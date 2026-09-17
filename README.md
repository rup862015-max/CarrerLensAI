# CareerLens AI — Phase 1 Prototype
> **Explainable Career Intelligence & Job Matching System**

CareerLens AI provides transparent, evidence-backed candidate resume profiling, ATS optimization, and multi-layer job matching. Unlike black-box matching systems, CareerLens AI explains **why** a candidate matches a requirement with verified snippets from their projects and experience, highlights prioritized skill gaps, and forecasts career progression trajectories.

---

## 🏗️ Architecture & Vertical Slice (Phase 1)

```text
Upload Resume (PDF/DOCX)
        ↓
PyMuPDF / python-docx Text Extraction
        ↓
AI Profiling & Health Scoring (Content, Skills, Experience, Projects, ATS)
        ↓
Select Benchmark Job or Paste Custom Job Description
        ↓
Hybrid 3-Layer Matching Engine (Exact + Taxonomy + Semantic TF-IDF)
        ↓
Explainable Score Breakdown + Verified Evidence Snippets + Prioritized Skill Gaps
        ↓
Career Intelligence Trajectory Preview
```

---

## 🚀 Key Features

1. **Multi-Format Resume Ingestion**: Real extraction and parsing for `.pdf`, `.docx`, and `.txt` files with file size and integrity validation.
2. **Deterministic & Pluggable AI Service**: Pluggable LLM interface with a robust deterministic NLP engine (taxonomy graph, regex NER, TF-IDF vector cosine similarity) guaranteeing distinct, calculated scores without requiring paid API keys.
3. **Structured Candidate Profiling**: Extracts education, experience timeline, skills categorized by taxonomy, and projects distinguishing **Explicit Skills** from **Inferred Skills**.
4. **Hybrid 3-Layer Matching Engine**:
   - **Layer 1**: Exact requirement-to-skill matching.
   - **Layer 2**: Taxonomy hierarchy and synonym relationship matching.
   - **Layer 3**: Semantic cosine similarity via scikit-learn TF-IDF n-grams.
5. **Deep Explainability & Evidence Drawer**: Clicking any matched requirement displays verified context snippets, confidence ratings, and source locations (Projects, Experience, Skills).
6. **Market-Prioritized Skill Gaps**: Identifies high/medium/low priority missing skills with benchmark prevalence statistics.
7. **Side-by-Side Comparison**: Candidate skills checklist aligned with job requirements.
8. **Career Intelligence Preview**: Suggests strongest current path and high-leverage skill additions.
9. **Graceful Phase 2 Previews**: Polished modal previews for *Career Simulator*, *Skill Roadmap*, *Interview Simulator*, *Security Audit*, and *Fairness Audit*.

---

## 📦 Project Structure

```text
d:/MW III/
├── backend/
│   ├── main.py                  # FastAPI server with all endpoints and CORS
│   ├── database.py              # SQLite storage (resumes, profiles, jobs, match results)
│   ├── schemas.py               # Pydantic contract models
│   ├── test_phase1.py           # Backend automated test suite (7 comprehensive test cases)
│   ├── data/
│   │   ├── skills_taxonomy.json # 80+ categorized skills with aliases & relationships
│   │   └── demo_jobs.json       # 3 structured demo jobs (Backend, Frontend, Data Analyst)
│   └── services/
│       ├── resume_parser.py     # PDF (PyMuPDF) and DOCX (python-docx) extraction
│       ├── ai_service.py        # Pluggable AI service with deterministic NLP fallback
│       ├── skill_service.py     # Skill entity extraction & taxonomy lookups
│       ├── matching_service.py  # 3-layer hybrid matching engine & subscore calculation
│       └── explanation_service.py # Evidence extraction & confidence scoring
│
├── frontend/
│   ├── src/
│   │   ├── types/index.ts       # TypeScript interfaces
│   │   ├── services/api.ts      # Fetch API client communicating with backend
│   │   ├── components/          # Reusable UI components
│   │   │   ├── Navbar.tsx
│   │   │   ├── ResumeUpload.tsx
│   │   │   ├── ScoreRadial.tsx
│   │   │   ├── ExtractedProfileView.tsx
│   │   │   ├── MatchResultView.tsx
│   │   │   ├── SideBySideCompare.tsx
│   │   │   ├── CareerIntelligencePreview.tsx
│   │   │   └── Phase2Placeholder.tsx
│   │   └── pages/               # Functional route pages
│   │       ├── DashboardPage.tsx
│   │       ├── ResumeAnalysisPage.tsx
│   │       └── JobMatchingPage.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── .env.example
└── README.md
```

---

## 🛠️ Quick Start Instructions

### 1. Backend Setup & Run (FastAPI)

```bash
# Navigate to project root
cd "d:\MW III"

# Run all automated tests
python backend/test_phase1.py

# Start FastAPI backend server on port 8000
python backend/main.py
```
> The API will be live at `http://localhost:8000` with interactive Swagger docs at `http://localhost:8000/docs`.

### 2. Frontend Setup & Run (React + Vite)

```bash
# In a second terminal, navigate to frontend
cd "d:\MW III\frontend"

# Start Vite dev server on port 3000
npm run dev
```
> Open your browser at `http://localhost:3000`.

---

## 🧪 API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check & LLM provider status |
| `GET` | `/api/jobs/demo` | Retrieves 3 benchmark demo job descriptions |
| `POST` | `/api/resume/upload` | Ingests PDF/DOCX file, extracts entities, and stores analysis |
| `POST` | `/api/resume/analyze` | Ingests raw text or demo payload for instant parsing |
| `GET` | `/api/resume/latest` | Retrieves most recently analyzed resume from SQLite |
| `POST` | `/api/job/analyze` | Analyzes custom job description text into structured requirements |
| `POST` | `/api/match` | Executes 3-layer hybrid matching engine and returns explainability report |

---

## 🔮 Roadmap: Phase 2 Additions

- **Skill Knowledge Graph**: Multi-hop semantic skill relationships & industry ontology expansion.
- **Career What-If Simulator**: Real-time parameter tweaking to project trajectory changes.
- **Personalized Learning Roadmap**: Direct curriculum generation from missing skill gaps.
- **Interactive Interview Simulator**: Real-time speech & STAR-method response evaluation.
- **Resume Security & Prompt Injection Audit**: Defense against zero-width characters and prompt injections.
- **Algorithmic Fairness Audit**: Disparate impact and gender/ethnicity neutrality compliance scoring.
