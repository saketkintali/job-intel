import asyncio
import io
import json
import os
import re
import uuid
from typing import Optional

import httpx
import pdfplumber
import PyPDF2
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="Job Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store: profileId -> parsed resume data
profiles: dict = {}

CLAUDE_API_URL = os.environ.get("CLAUDE_API_URL", "http://127.0.0.1:18789/v1/responses")
GATEWAY_TOKEN = os.environ.get("GATEWAY_TOKEN", "")
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs/us/search/1"
THEMUSE_BASE = "https://www.themuse.com/api/public/jobs"
GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

# Top tech companies known to use Greenhouse (no auth required)
GREENHOUSE_COMPANIES = [
    "airbnb", "anthropic", "brex", "coinbase", "databricks",
    "discord", "figma", "instacart", "lyft", "stripe",
    "vercel", "benchling", "asana", "robinhood", "twitch",
    "dropbox", "zendesk", "hubspot", "intercom", "gusto",
]


async def fetch_greenhouse_jobs(role: str, location: str = "") -> list[dict]:
    """Fetch jobs from Greenhouse ATS (free, no auth). Filters by role keyword."""
    role_lower = role.lower().strip()
    # Use full phrase first; fall back to significant keywords (skip generic words)
    GENERIC = {"engineer", "developer", "manager", "lead", "senior", "junior", "staff", "principal"}
    keywords = [kw.lower() for kw in role.split() if len(kw) > 2 and kw.lower() not in GENERIC]
    city = location.split(",")[0].strip().lower() if location else ""
    results = []

    async with httpx.AsyncClient(timeout=15) as client:
        tasks = [
            client.get(GREENHOUSE_BASE.format(company=c))
            for c in GREENHOUSE_COMPANIES
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    for company, resp in zip(GREENHOUSE_COMPANIES, responses):
        if isinstance(resp, Exception) or resp.status_code != 200:
            continue
        try:
            jobs = resp.json().get("jobs", [])
        except Exception:
            continue

        for job in jobs:
            title = job.get("title", "").lower()
            # Filter by role: exact phrase match first, then keyword fallback
            if role_lower not in title and (not keywords or not any(kw in title for kw in keywords)):
                continue
            job_location = job.get("location", {}).get("name", "")
            # Filter by city: only include jobs where city matches
            # "Remote - USA" or "Remote, USA" passes only if no city specified
            display_location = job_location
            is_remote = False

            if city:
                loc_lower = job_location.lower()
                # Split multi-city strings like "San Francisco, CA | Seattle, WA"
                segments = [s.strip() for s in job_location.replace(";", "|").split("|")]
                city_segments = [s for s in segments if city in s.lower()]
                remote_segments = [s for s in segments if "remote" in s.lower()]

                city_match = len(city_segments) > 0
                remote_usa = len(remote_segments) > 0 and any(
                    x in " ".join(remote_segments).lower()
                    for x in ["usa", "united states", "america", "- us", "-us", ", us"]
                ) and not any(
                    x in " ".join(remote_segments).lower()
                    for x in ["brazil", "india", "canada", "uk", "europe", "latam", "latin", "australia", "austria"]
                )

                if not city_match and not remote_usa:
                    continue

                # Clean up display: if multi-city mess, just show the searched city cleanly
                OTHER_CITIES = ["san francisco", "new york", "los angeles", "chicago", "boston",
                                "austin", "denver", "miami", "atlanta", "portland", "phoenix"]
                if city_match:
                    candidate = city_segments[0] if len(city_segments) == 1 else " | ".join(city_segments)
                    # If the candidate still has other cities in it, just use the search location
                    has_other_city = any(oc in candidate.lower() for oc in OTHER_CITIES if oc != city)
                    if has_other_city or len(candidate) > 40 or "|" in candidate:
                        display_location = location.strip() if location else city.title()
                    else:
                        display_location = candidate
                elif remote_usa:
                    display_location = remote_segments[0]
                    is_remote = True
            else:
                is_remote = "remote" in job_location.lower()

            results.append({
                "id": str(job.get("id", uuid.uuid4())),
                "company": company.capitalize(),
                "title": job.get("title", ""),
                "location": display_location,
                "url": job.get("absolute_url", "#"),
                "remote": is_remote,
                "source": "Greenhouse",
            })

    return results




@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    contents = await file.read()

    # Try pdfplumber first (handles complex layouts, columns, ATS formats better)
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        pass

    # Fall back to PyPDF2
    if not text.strip():
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(contents))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            pass

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from PDF — try a different file or use the job title search instead")

    prompt = (
        "Extract job titles from this resume. Focus on what roles this person is APPLYING FOR based on their experience, "
        "not just what they held. Return JSON: { skills: string[], roles: string[], yearsExp: number }. "
        "For roles, return clean job titles without seniority (e.g. Software Engineer not Senior Software Engineer). "
        f"Resume: {text[:8000]}"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            CLAUDE_API_URL,
            json={
                "model": "openclaw:main",
                "input": [{"type": "message", "role": "user", "content": prompt}]
            },
            headers={"Authorization": f"Bearer {GATEWAY_TOKEN}"}
        )
        resp.raise_for_status()

    data = resp.json()
    raw = ""
    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                raw = c.get("text", "")
                break

    # Parse JSON from Claude response
    parsed = {"skills": [], "roles": [], "yearsExp": 0}
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError:
            pass

    profile_id = str(uuid.uuid4())
    profiles[profile_id] = parsed

    return {
        "profileId": profile_id,
        "skills": parsed.get("skills", []),
        "roles": parsed.get("roles", []),
        "yearsExp": parsed.get("yearsExp", 0),
    }


SENIORITY_PREFIXES = {"senior", "junior", "lead", "principal", "staff", "sr", "jr"}
STOP_WORDS = {"the", "for", "and", "with", "in", "of", "at", "to", "a", "an"}


def extract_keywords(role: str) -> list[str]:
    words = re.sub(r"[^a-z\s]", "", role.lower()).split()
    # Strip seniority prefixes
    words = [w for w in words if w not in SENIORITY_PREFIXES]
    # Keep meaningful words (>2 chars, not stop words)
    return [w for w in words if len(w) > 2 and w not in STOP_WORDS]


@app.post("/api/resume/debug")
async def debug_resume(file: UploadFile = File(...)):
    """Debug endpoint — returns raw extracted text + Claude's raw response."""
    contents = await file.read()
    text = ""
    method = "none"
    try:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            method = "pdfplumber"
    except Exception:
        pass
    if not text.strip():
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(contents))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if text.strip():
                method = "pypdf2"
        except Exception:
            pass

    if not text.strip():
        return {"extracted_text": "", "method": "none", "claude_raw": "", "parsed": {}}

    prompt = (
        "Extract job titles from this resume. Return JSON: { skills: string[], roles: string[], yearsExp: number }. "
        f"Resume: {text[:4000]}"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(CLAUDE_API_URL,
            json={"model": "openclaw:main", "input": [{"type": "message", "role": "user", "content": prompt}]},
            headers={"Authorization": f"Bearer {GATEWAY_TOKEN}"})
    raw = ""
    for item in resp.json().get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                raw = c.get("text", "")

    return {
        "extracted_text_preview": text[:1000],
        "extracted_length": len(text),
        "method": method,
        "claude_raw": raw,
    }


@app.get("/api/companies")
async def get_companies(profileId: str, role: Optional[str] = None, location: Optional[str] = "Seattle, WA", salary_min: Optional[int] = None, radius: Optional[int] = 25):
    if profileId != "manual" and profileId not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    if profileId == "manual":
        search_role = role or "software engineer"
    else:
        profile = profiles[profileId]
        search_role = role or (profile.get("roles") or ["software engineer"])[0]

    # ── Adzuna + Greenhouse (run in parallel) ────────────────────────────
    adzuna_jobs = []
    greenhouse_task = asyncio.create_task(
        fetch_greenhouse_jobs(search_role, location or "Seattle")
    )

    if ADZUNA_APP_ID and ADZUNA_APP_ID not in ("REPLACE_WITH_APP_ID", ""):
        async with httpx.AsyncClient(timeout=30) as client:
            adzuna_params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "results_per_page": 15,
                "what": search_role,
                "where": location or "Seattle",
                "sort_by": "relevance",
                "distance": radius or 25,
            }
            if salary_min:
                adzuna_params["salary_min"] = salary_min
            resp = await client.get(ADZUNA_BASE, params=adzuna_params)
        if resp.status_code == 200:
            for job in resp.json().get("results", []):
                adzuna_jobs.append({
                    "id": str(job.get("id", uuid.uuid4())),
                    "company": job.get("company", {}).get("display_name", "Unknown"),
                    "title": job.get("title", ""),
                    "location": job.get("location", {}).get("display_name", ""),
                    "url": job.get("redirect_url", "#"),
                    "remote": False,
                    "source": "Adzuna",
                })

    greenhouse_jobs = await greenhouse_task

    # ── Merge + deduplicate by (company, title) ───────────────────────────
    seen: set = set()
    merged: list = []
    for job in adzuna_jobs + greenhouse_jobs:
        key = (job["company"].lower().strip(), job["title"].lower().strip())
        if key in seen:
            continue
        seen.add(key)
        merged.append(job)

    if merged:
        return merged

    # ── The Muse fallback ─────────────────────────────────────────────────
    keywords = extract_keywords(search_role)
    if not keywords:
        keywords = [search_role.lower().strip()]

    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [
            client.get(THEMUSE_BASE, params={"descending": "true", "page": p})
            for p in [1, 2]
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    all_results = []
    for resp in responses:
        if isinstance(resp, Exception):
            continue
        try:
            resp.raise_for_status()
            all_results.extend(resp.json().get("results", []))
        except Exception:
            continue

    matched = [
        j for j in all_results
        if any(kw in j.get("name", "").lower() for kw in keywords)
    ]

    city = location.split(",")[0].strip().lower() if location else ""

    def is_city_match(job) -> bool:
        return any(city in loc.get("name", "").lower() for loc in job.get("locations", []))

    def is_remote(job) -> bool:
        return any("remote" in loc.get("name", "").lower() or "flexible" in loc.get("name", "").lower() for loc in job.get("locations", []))

    city_jobs = [j for j in matched if is_city_match(j)] if city else []
    remote_jobs = [j for j in matched if is_remote(j)]

    # Use city-specific jobs if available, otherwise fall back to remote
    display_jobs = city_jobs if city_jobs else remote_jobs if remote_jobs else matched

    # Deduplicate: one card per company name
    seen_companies: set = set()
    deduped = []
    for job in display_jobs:
        company_name = job.get("company", {}).get("name", "Unknown")
        if company_name not in seen_companies:
            seen_companies.add(company_name)
            deduped.append(job)

    companies = []
    for job in deduped[:12]:
        job_is_remote = is_remote(job)
        companies.append({
            "id": str(job.get("id", uuid.uuid4())),
            "company": job.get("company", {}).get("name", "Unknown"),
            "title": job.get("name", ""),
            "location": job.get("locations", [{}])[0].get("name", "Remote"),
            "url": job.get("refs", {}).get("landing_page", "#"),
            "remote": job_is_remote,
        })

    return companies


LEETCODE_TAGS_BY_ROLE = {
    "data": ["Database", "Hash Table", "Math", "Statistics"],
    "ml": ["Math", "Dynamic Programming", "Matrix"],
    "frontend": ["String", "Array", "Hash Table", "Tree"],
    "backend": ["Array", "Hash Table", "Tree", "Graph", "Dynamic Programming"],
    "default": ["Array", "Hash Table", "Tree", "Linked List", "Dynamic Programming", "Graph"],
}

async def fetch_leetcode_problems(tags: list[str], limit: int = 5) -> list[dict]:
    """Fetch real LeetCode problems filtered by topic tags."""
    query = """
    query problemsetQuestionList($categorySlug: String, $limit: Int, $filters: QuestionListFilterInput) {
      questionList(categorySlug: $categorySlug limit: $limit filters: $filters) {
        data {
          title
          difficulty
          topicTags { name }
          titleSlug
        }
      }
    }
    """
    problems = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://leetcode.com/graphql",
                json={"query": query, "variables": {
                    "categorySlug": "",
                    "limit": limit * 2,
                    "filters": {"tags": tags}
                }},
                headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"},
            )
        items = resp.json().get("data", {}).get("questionList", {}).get("data", [])
        for item in items[:limit]:
            problems.append({
                "question": item["title"],
                "type": "coding",
                "difficulty": item["difficulty"],
                "frequency": "very often" if item["difficulty"] == "Easy" else "often" if item["difficulty"] == "Medium" else "sometimes",
                "source": "LeetCode",
                "url": f"https://leetcode.com/problems/{item['titleSlug']}/",
                "tags": [t["name"] for t in item["topicTags"][:3]],
            })
    except Exception:
        pass
    return problems


@app.get("/api/interviews")
async def get_interviews(company: str, role: str):
    role_lower = role.lower()
    is_data = any(kw in role_lower for kw in ["data", "analyst", "scientist", "ml", "machine learning"])
    is_frontend = any(kw in role_lower for kw in ["frontend", "front-end", "react", "ui"])
    is_pm = any(kw in role_lower for kw in ["product", "manager", "pm"])
    is_design = any(kw in role_lower for kw in ["design", "ux"])

    # Fetch real coding problems from LeetCode
    if is_data:
        lc_tags = LEETCODE_TAGS_BY_ROLE["data"]
    elif is_frontend:
        lc_tags = LEETCODE_TAGS_BY_ROLE["frontend"]
    else:
        lc_tags = LEETCODE_TAGS_BY_ROLE["default"]

    coding_questions = []
    if not is_pm and not is_design:
        coding_questions = await fetch_leetcode_problems(lc_tags, limit=5)

    # Generate system design + behavioral with Claude (company-specific)
    if is_pm:
        sd_behavioral = [
            {"question": f"How would you prioritize features for {company}'s next product release?", "type": "behavioral", "frequency": "very often", "source": "Common"},
            {"question": "A key metric dropped 20% overnight. Walk me through your investigation.", "type": "behavioral", "frequency": "often", "source": "Common"},
            {"question": "Tell me about a product you significantly improved. What was your process?", "type": "behavioral", "frequency": "very often", "source": "Common"},
            {"question": f"Design the metrics framework for a new {company} feature.", "type": "system design", "frequency": "often", "source": "Common"},
            {"question": "How do you balance user needs against business constraints?", "type": "behavioral", "frequency": "often", "source": "Common"},
        ]
    elif is_design:
        sd_behavioral = [
            {"question": "Walk me through your design process from discovery to delivery.", "type": "behavioral", "frequency": "very often", "source": "Common"},
            {"question": f"Redesign {company}'s onboarding experience. What would you change?", "type": "system design", "frequency": "often", "source": "Common"},
            {"question": "Tell me about a design that failed and what you learned.", "type": "behavioral", "frequency": "often", "source": "Common"},
            {"question": "How do you measure the success of a design change?", "type": "behavioral", "frequency": "sometimes", "source": "Common"},
        ]
    else:
        sd_behavioral = [
            {"question": f"Design a URL shortener service at {company}'s scale.", "type": "system design", "frequency": "very often", "source": "Common"},
            {"question": f"Design a notification system for {company}.", "type": "system design", "frequency": "often", "source": "Common"},
            {"question": "Tell me about a time you resolved a conflict within your team.", "type": "behavioral", "frequency": "often", "source": "Common"},
            {"question": "Describe a situation where you had to make a critical decision under pressure.", "type": "behavioral", "frequency": "sometimes", "source": "Common"},
        ]

    return coding_questions + sd_behavioral


@app.get("/api/salary")
async def get_salary(company: str, role: str):
    role_lower = role.lower()

    if any(kw in role_lower for kw in ["senior", "sr", "staff", "principal", "lead"]):
        base_min, base_median, base_max = 150000, 185000, 240000
    elif any(kw in role_lower for kw in ["junior", "jr", "entry", "associate", "intern"]):
        base_min, base_median, base_max = 70000, 90000, 120000
    elif any(kw in role_lower for kw in ["manager", "director", "vp", "head"]):
        base_min, base_median, base_max = 160000, 210000, 280000
    elif any(kw in role_lower for kw in ["data scientist", "ml engineer", "machine learning"]):
        base_min, base_median, base_max = 120000, 155000, 200000
    else:
        base_min, base_median, base_max = 100000, 130000, 175000

    # Adjust for well-known high-paying companies
    big_tech = ["google", "meta", "apple", "microsoft", "amazon", "netflix", "uber", "airbnb", "stripe", "openai"]
    if any(b in company.lower() for b in big_tech):
        base_min = int(base_min * 1.25)
        base_median = int(base_median * 1.3)
        base_max = int(base_max * 1.35)

    return {
        "min": base_min,
        "median": base_median,
        "max": base_max,
        "currency": "USD",
        "note": f"Estimated total compensation for {role} at {company}. Includes base salary; equity and bonus vary by level.",
    }


@app.get("/api/study")
async def get_study_plan(profileId: str, company: str, role: str):
    """Study plan derived directly from interview rounds — each item maps to a round."""

    ROUND_RESOURCES = {
        "coding": {
            "label": "Coding / DSA",
            "priority": "high",
            "resources": [
                {"title": "NeetCode 150 — structured DSA practice", "url": "https://neetcode.io/practice"},
                {"title": "LeetCode Top Interview 150", "url": "https://leetcode.com/studyplan/top-interview-150/"},
                {"title": "Blind 75 — must-know problems", "url": "https://leetcode.com/discuss/general-discussion/460599/blind-75-leetcode-questions"},
            ],
            "tips": "Focus on arrays, hashmaps, trees, graphs, and dynamic programming. Practice talking through your solution before coding.",
        },
        "system design": {
            "label": "System Design",
            "priority": "high",
            "resources": [
                {"title": "System Design Primer (GitHub)", "url": "https://github.com/donnemartin/system-design-primer"},
                {"title": "ByteByteGo — visual system design guides", "url": "https://bytebytego.com"},
                {"title": "Designing Data-Intensive Applications (book)", "url": "https://dataintensive.net"},
            ],
            "tips": "Always start with requirements. Cover scale, storage, APIs, and failure modes. Use the RESHADED framework.",
        },
        "behavioral": {
            "label": "Behavioral / Leadership",
            "priority": "medium",
            "resources": [
                {"title": "STAR Method — structuring your answers", "url": "https://www.themuse.com/advice/star-interview-method"},
                {"title": "Grokking the Behavioral Interview", "url": "https://www.educative.io/courses/grokking-the-behavioral-interview"},
                {"title": f"{company} Leadership Principles — research these specifically", "url": f"https://www.google.com/search?q={company.replace(' ', '+')}+leadership+principles+interview"},
            ],
            "tips": "Prepare 5–6 STAR stories covering: conflict, failure, ownership, impact, and cross-team collaboration.",
        },
        "recruiter screen": {
            "label": "Recruiter / Intro Screen",
            "priority": "low",
            "resources": [
                {"title": "How to ace a recruiter screen", "url": "https://www.themuse.com/advice/how-to-ace-a-phone-screen-interview"},
            ],
            "tips": "Know your resume cold. Have a 2-minute 'tell me about yourself' ready. Research the company's recent news.",
        },
        "hiring manager": {
            "label": "Hiring Manager Interview",
            "priority": "medium",
            "resources": [
                {"title": "Questions to ask your hiring manager", "url": "https://www.themuse.com/advice/51-interview-questions-you-should-be-asking"},
            ],
            "tips": "Show genuine interest in the team's mission. Ask about current challenges and how success is measured.",
        },
        "take-home": {
            "label": "Take-Home / Case Study",
            "priority": "high",
            "resources": [
                {"title": "How to ace take-home coding challenges", "url": "https://www.freecodecamp.org/news/the-essential-guide-to-take-home-coding-challenges-a0e746220dd7/"},
            ],
            "tips": "Prioritize clarity and clean code over completeness. Add a short README explaining your decisions.",
        },
        "bar raiser": {
            "label": "Bar Raiser / Culture Fit",
            "priority": "medium",
            "resources": [
                {"title": "Amazon Bar Raiser — what to expect", "url": "https://www.levels.fyi/blog/amazon-bar-raiser.html"},
            ],
            "tips": "Be authentic. Show intellectual curiosity, ownership mindset, and how you've raised the bar in past roles.",
        },
    }

    DATA_RESOURCES = {
        "label": "Data / ML Skills",
        "priority": "high",
        "resources": [
            {"title": "Kaggle Learn — hands-on ML courses", "url": "https://www.kaggle.com/learn"},
            {"title": "StatQuest — statistics & ML explained visually", "url": "https://www.youtube.com/@statquest"},
            {"title": "Mode SQL Tutorial", "url": "https://mode.com/sql-tutorial/"},
        ],
        "tips": "Practice SQL window functions and pandas data manipulation. Be ready to explain model evaluation metrics.",
    }

    # Get rounds for this role
    rounds_resp = await get_rounds(company=company, role=role)
    rounds = rounds_resp.get("rounds", [])

    plan = []
    seen_types: set = set()

    for round_item in rounds:
        rtype = round_item.get("type", "").lower()
        round_num = round_item.get("number", 0)

        # Match round type to a resource block
        matched_key = None
        for key in ROUND_RESOURCES:
            if key in rtype:
                matched_key = key
                break

        if not matched_key or matched_key in seen_types:
            continue

        seen_types.add(matched_key)
        block = ROUND_RESOURCES[matched_key]

        plan.append({
            "round": round_num,
            "roundType": round_item.get("type"),
            "skill": block["label"],
            "priority": block["priority"],
            "tips": block["tips"],
            "resources": block["resources"],
        })

    # Add data-specific resources if relevant role
    role_lower = role.lower()
    if any(kw in role_lower for kw in ["data", "ml", "machine learning", "scientist", "analyst"]):
        plan.insert(0, {
            "round": 0,
            "roundType": "Technical",
            "skill": DATA_RESOURCES["label"],
            "priority": DATA_RESOURCES["priority"],
            "tips": DATA_RESOURCES["tips"],
            "resources": DATA_RESOURCES["resources"],
        })

    return {"plan": plan}


@app.get("/api/rounds")
async def get_rounds(company: str, role: str):
    role_lower = role.lower()

    is_senior = any(kw in role_lower for kw in ["senior", "sr", "staff", "principal", "lead", "manager", "director"])
    is_pm = any(kw in role_lower for kw in ["product manager", "pm"])
    is_data = any(kw in role_lower for kw in ["data scientist", "ml engineer", "machine learning"])

    if is_pm:
        rounds = [
            {"number": 1, "type": "Recruiter Screen", "duration": "30 min", "tips": "Review your resume and know your key achievements. Research the company's products."},
            {"number": 2, "type": "Hiring Manager Interview", "duration": "45 min", "tips": "Discuss your product thinking and past PM experience. Use the STAR method."},
            {"number": 3, "type": "Product Sense", "duration": "60 min", "tips": "Practice designing products and defining metrics. Use a structured framework: goals → users → solutions → tradeoffs."},
            {"number": 4, "type": "Analytical/Metrics", "duration": "45 min", "tips": "Be comfortable with A/B testing, funnel analysis, and defining success metrics."},
            {"number": 5, "type": "Cross-functional / Leadership", "duration": "45 min", "tips": "Show how you work with engineering, design, and stakeholders. Demonstrate influence without authority."},
        ]
    elif is_data:
        rounds = [
            {"number": 1, "type": "Recruiter Screen", "duration": "30 min", "tips": "Talk through your experience and motivation. Expect questions about your tooling (Python, SQL, etc.)."},
            {"number": 2, "type": "Technical Screen", "duration": "60 min", "tips": "SQL and Python coding problems. Practice window functions and data manipulation with pandas."},
            {"number": 3, "type": "Machine Learning Deep Dive", "duration": "60 min", "tips": "Be ready to explain model choice, training, evaluation, and deployment. Expect case studies."},
            {"number": 4, "type": "Take-Home or Case Study", "duration": "1–2 days", "tips": "Analyze a provided dataset and present findings. Focus on storytelling and business impact."},
            {"number": 5, "type": "Behavioral / Culture Fit", "duration": "45 min", "tips": "Prepare STAR stories around data-driven decisions, collaboration, and ambiguity."},
        ]
    elif is_senior:
        rounds = [
            {"number": 1, "type": "Recruiter Screen", "duration": "30 min", "tips": "Align on compensation, timeline, and role fit. Research the team's mission."},
            {"number": 2, "type": "Technical Phone Screen", "duration": "60 min", "tips": "Medium/hard LeetCode-style problem. Communicate your thought process clearly."},
            {"number": 3, "type": "System Design", "duration": "60 min", "tips": "Focus on scale, reliability, and trade-offs. Ask clarifying questions and drive the design."},
            {"number": 4, "type": "Coding Interview", "duration": "60 min", "tips": "Two coding problems—aim for optimal time/space complexity and clean code."},
            {"number": 5, "type": "Leadership & Behavioral", "duration": "45 min", "tips": "Highlight examples of technical leadership, mentoring, and navigating ambiguity."},
            {"number": 6, "type": "Bar Raiser / Culture Fit", "duration": "45 min", "tips": "Expect questions on ownership, influence, and past failures. Be honest and reflective."},
        ]
    else:
        rounds = [
            {"number": 1, "type": "Recruiter Screen", "duration": "30 min", "tips": "Review your resume. Prepare your background story and why you're interested in the role."},
            {"number": 2, "type": "Technical Phone Screen", "duration": "45–60 min", "tips": "One or two coding problems. Practice easy/medium problems on LeetCode under time pressure."},
            {"number": 3, "type": "System Design", "duration": "45 min", "tips": "Understand the basics: load balancing, caching, databases, and scaling. Use the RESHADED framework."},
            {"number": 4, "type": "Coding Interview (Onsite)", "duration": "60 min", "tips": "Two coding problems. Think out loud and explain your approach before coding."},
            {"number": 5, "type": "Behavioral Interview", "duration": "45 min", "tips": "Prepare 5–6 STAR stories covering: teamwork, conflict, failure, success, and leadership."},
        ]

    return {"totalRounds": len(rounds), "rounds": rounds}
