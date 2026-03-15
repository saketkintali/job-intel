# Job Intelligence Platform

Upload your resume (or search by job title) to get matched with real job listings, then instantly pull up interview questions, salary ranges, a study plan, and a breakdown of interview rounds — all in one dashboard.

---

## What It Does

- **Resume upload** → Claude AI extracts your skills and target roles
- **Job title search** → skip the resume, search directly
- **Company grid** → real listings from Adzuna and Greenhouse (20 top tech companies), filtered by location, radius, salary floor, and remote/onsite preference
- **Per-company dashboard** with 4 tiles:
  - **Interview Questions** — real LeetCode problems (coding) + company-specific system design & behavioral
  - **Salary Ranges** — min / median / max estimated by role and company tier
  - **Study Plan** — mapped to actual interview rounds with curated resources
  - **Interview Rounds** — number of rounds, type, and duration
- **Apply Now** button → links directly to the job listing

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, uvicorn |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| AI | Claude via OpenClaw local gateway |
| Jobs API | Adzuna (optional) + Greenhouse ATS (no auth), The Muse (fallback) |
| Interview data | LeetCode GraphQL (public, no auth) |
| PDF parsing | pdfplumber (primary), PyPDF2 (fallback) |

---

## Prerequisites

- Python 3.12+
- Node.js 18+
- OpenClaw running locally (for resume parsing via Claude)
- An [Adzuna API account](https://developer.adzuna.com/) *(optional — Greenhouse jobs load without it)*

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/saketkintali/job-intel.git
cd job-intel
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure API keys

```bash
cd backend
cp .env.example .env   # Windows: copy .env.example .env
```

Open `backend/.env` and fill in your values:

```env
# Claude / OpenClaw local gateway
CLAUDE_API_URL=http://127.0.0.1:18789/v1/responses
GATEWAY_TOKEN=your-openclaw-gateway-token

# Adzuna Jobs API — free account at https://developer.adzuna.com/
# Leave blank to rely on Greenhouse + The Muse only
ADZUNA_APP_ID=your-adzuna-app-id
ADZUNA_APP_KEY=your-adzuna-app-key
```

> The `.env` file is listed in `.gitignore` and will never be committed.

### 4. Frontend

```bash
cd ../frontend
npm install
```

---

## Running Locally

You need two terminals.

**Terminal 1 — Backend:**

```bash
cd backend
.venv\Scripts\activate        # Windows
# or: source .venv/bin/activate  (macOS/Linux)

python -m uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/resume/upload` | POST | Upload PDF → returns `profileId`, extracted skills/roles |
| `/api/resume/debug` | POST | Debug endpoint — returns raw extracted text + Claude output |
| `/api/companies` | GET | Job listings. Params: `profileId`, `role`, `location`, `salary_min`, `radius` (miles, default 25) |
| `/api/interviews` | GET | Interview questions. Params: `company`, `role` |
| `/api/salary` | GET | Salary ranges. Params: `company`, `role` |
| `/api/study` | GET | Study plan. Params: `profileId`, `company`, `role` |
| `/api/rounds` | GET | Interview rounds. Params: `company`, `role` |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Job Sources

| Source | Auth required | Notes |
|---|---|---|
| Adzuna | Yes (free account) | Keyword + location search, salary filter, radius |
| Greenhouse ATS | None | 20 hardcoded top tech companies (Airbnb, Anthropic, Stripe, etc.) |
| The Muse | None | Fallback — used only if Adzuna and Greenhouse return nothing |

Results from Adzuna and Greenhouse are fetched in parallel and deduplicated by `(company, title)`.

---

## Project Structure

```
job-intel/
├── backend/
│   ├── main.py              # FastAPI app — all endpoints
│   ├── requirements.txt
│   ├── .env.example         # Copy to .env and fill in keys
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   └── pages/
│   │       ├── UploadPage.tsx      # Entry — resume or title search
│   │       ├── CompaniesPage.tsx   # Job grid with filters
│   │       └── DashboardPage.tsx   # 4-tile company dashboard
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Docker (optional)

```bash
docker compose up --build
```

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend: [http://localhost:8000](http://localhost:8000)

> Set `GATEWAY_TOKEN`, `ADZUNA_APP_ID`, and `ADZUNA_APP_KEY` as environment variables or in a `.env` file at the repo root before running Docker.

---

## Known Limitations

- **Profiles are in-memory** — re-uploading your resume after a backend restart is required (SQLite persistence is planned)
- **LeetCode coding questions** are filtered by topic tag, not company-specific (company tagging requires LeetCode Premium)
- **Salary and round data** are estimated based on role type — not sourced from a live API
- **Resume parsing** works best with text-based PDFs; scanned/image PDFs may not extract correctly

---

## Roadmap

- [ ] SQLite persistence for resume profiles
- [x] `.env` file support for secrets
- [x] Greenhouse ATS as a no-auth job source
- [x] Fix seniority filtering for Greenhouse results
- [ ] Adzuna pagination (currently page 1 only)
- [ ] More interview question sources
- [ ] Save/bookmark companies
- [ ] Export study plan to PDF
