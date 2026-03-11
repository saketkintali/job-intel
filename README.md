# Job Intelligence Platform

Upload your resume (or search by job title) to get matched with real job listings, then instantly pull up interview questions, salary ranges, a study plan, and a breakdown of interview rounds — all in one dashboard.

---

## What It Does

- **Resume upload** → Claude AI extracts your skills and target roles
- **Job title search** → skip the resume, search directly
- **Company grid** → real listings from Adzuna, filtered by location (25-mile radius) and optional salary floor
- **Per-company dashboard** with 4 tiles:
  - 🎯 **Interview Questions** — real LeetCode problems (coding) + company-specific system design & behavioral
  - 💰 **Salary Ranges** — min / median / max with location breakdown
  - 📚 **Study Plan** — mapped to actual interview rounds with curated resources
  - 🔁 **Interview Rounds** — number of rounds, type, and duration
- **Apply Now** button → links directly to the job listing

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, uvicorn |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| AI | Claude via OpenClaw local API |
| Jobs API | Adzuna (primary), The Muse (fallback) |
| Interview data | LeetCode GraphQL (public, no auth) |
| PDF parsing | pdfplumber (primary), PyPDF2 (fallback) |

---

## Prerequisites

- Python 3.12+
- Node.js 18+
- An [Adzuna API account](https://developer.adzuna.com/) (free)
- OpenClaw running locally (for Claude API access)

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
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

Open `backend/main.py` and update these constants near the top:

```python
# Claude / OpenClaw
CLAUDE_API_URL = "http://127.0.0.1:18789/v1/responses"
GATEWAY_TOKEN  = "your-openclaw-gateway-token"

# Adzuna — get from https://developer.adzuna.com/
ADZUNA_APP_ID  = "your-app-id"
ADZUNA_APP_KEY = "your-app-key"
```

> **Coming soon:** `.env` file support so you never touch `main.py` for secrets.

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
| `/api/companies` | GET | Job listings from Adzuna. Params: `profileId`, `role`, `location`, `salary_min` |
| `/api/interviews` | GET | Interview questions. Params: `company`, `role` |
| `/api/salary` | GET | Salary ranges. Params: `companyId`, `role`, `location` |
| `/api/study` | GET | Study plan. Params: `profileId`, `companyId`, `role` |
| `/api/rounds` | GET | Interview rounds. Params: `companyId`, `role` |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Project Structure

```
job-intel/
├── backend/
│   ├── main.py              # FastAPI app — all endpoints
│   ├── requirements.txt
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

> Note: Docker compose requires the Adzuna and OpenClaw API keys to be set as environment variables or in a `.env` file at the root.

---

## Known Limitations

- **Profiles are in-memory** — re-uploading your resume after a backend restart is required (SQLite persistence is planned)
- **LeetCode coding questions** are filtered by topic tag, not company-specific (company tagging requires LeetCode Premium)
- **Salary and round data** are estimated based on role type — not sourced from a live API
- **Resume parsing** works best with text-based PDFs; scanned/image PDFs may not extract correctly

---

## Roadmap

- [ ] SQLite persistence for resume profiles
- [ ] `.env` file support for secrets
- [ ] Adzuna pagination (currently page 1 only)
- [ ] More interview question sources
- [ ] Save/bookmark companies
- [ ] Export study plan to PDF
