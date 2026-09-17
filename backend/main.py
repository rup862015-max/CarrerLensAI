"""
FastAPI Application Entry Point for CareerLens AI Phase 1
Exposes REST endpoints for resume uploading, parsing, AI profiling, and explainable job matching.
"""

import os
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import init_db, save_resume, save_resume_analysis, get_latest_resume, save_match_result
from schemas import (
    ResumeAnalysisResponse,
    ResumeAnalyzeRequest,
    JobAnalyzeRequest,
    DemoJob,
    MatchRequest,
    MatchResponse,
    ExtractedProfile
)
from services.resume_parser import extract_text_from_file, ResumeParserError
from services.ai_service import ai_service
from services.matching_service import matching_service

# Initialize SQLite tables on startup
init_db()

app = FastAPI(
    title="CareerLens AI API",
    description="Explainable Career Intelligence & Job Matching Engine",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DEMO_JOBS_PATH = os.path.join(DATA_DIR, "demo_jobs.json")


def load_demo_jobs() -> List[Dict[str, Any]]:
    if os.path.exists(DEMO_JOBS_PATH):
        with open(DEMO_JOBS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.get("/api/health")
async def health_check():
    """Service health and LLM provider status check."""
    return {
        "status": "healthy",
        "service": "CareerLens AI Phase 1",
        "llm_active": ai_service.is_llm_active(),
        "llm_provider": ai_service.provider
    }


@app.get("/api/jobs/demo", response_model=List[DemoJob])
async def get_demo_jobs():
    """Returns the 3 structured demo job descriptions."""
    jobs = load_demo_jobs()
    if not jobs:
        raise HTTPException(status_code=404, detail="Demo jobs not found.")
    return jobs


@app.post("/api/resume/upload", response_model=ResumeAnalysisResponse)
async def upload_resume(file: UploadFile = File(...)):
    """
    Accepts PDF, DOCX, or TXT resume file, extracts text,
    builds structured candidate profile, computes health scores, and persists to DB.
    """
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        raw_text, file_type = extract_text_from_file(file.filename, file_bytes)
        
        # Analyze resume using AI service
        analysis_data = ai_service.analyze_resume(raw_text, filename=file.filename)
        resume_id = analysis_data["resume_id"]

        # Persist to SQLite
        save_resume(
            resume_id=resume_id,
            filename=file.filename,
            file_type=file_type,
            file_size=len(file_bytes),
            raw_text=raw_text
        )
        save_resume_analysis(
            analysis_id=f"ana_{resume_id}",
            resume_id=resume_id,
            health_scores=analysis_data["health_scores"],
            extracted_profile=analysis_data["extracted_profile"]
        )

        return analysis_data

    except ResumeParserError as pe:
        raise HTTPException(status_code=400, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal analysis failure: {str(e)}")


@app.post("/api/resume/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume_text(request: ResumeAnalyzeRequest):
    """
    Analyzes raw pasted resume text and returns structured candidate profile.
    """
    if len(request.resume_text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Resume text is too short to analyze.")

    analysis_data = ai_service.analyze_resume(request.resume_text, filename=request.filename or "Pasted_Resume.txt")
    resume_id = analysis_data["resume_id"]

    # Persist to SQLite
    save_resume(
        resume_id=resume_id,
        filename=request.filename or "Pasted_Resume.txt",
        file_type="txt",
        file_size=len(request.resume_text.encode("utf-8")),
        raw_text=request.resume_text
    )
    save_resume_analysis(
        analysis_id=f"ana_{resume_id}",
        resume_id=resume_id,
        health_scores=analysis_data["health_scores"],
        extracted_profile=analysis_data["extracted_profile"]
    )

    return analysis_data


@app.get("/api/resume/latest")
async def get_latest_analyzed_resume():
    """
    Retrieves the most recent analyzed resume from SQLite storage.
    """
    latest = get_latest_resume()
    if not latest:
        raise HTTPException(status_code=404, detail="No analyzed resumes found in storage.")
    return latest


@app.post("/api/job/analyze")
async def analyze_job_description(request: JobAnalyzeRequest):
    """
    Parses an arbitrary job description text into structured requirements and responsibilities.
    """
    if len(request.job_text.strip()) < 15:
        raise HTTPException(status_code=400, detail="Job description text is too short.")

    return ai_service.analyze_job_description(request.job_text, title=request.title or "Custom Job Opening")


@app.post("/api/match", response_model=MatchResponse)
async def run_match_engine(request: MatchRequest):
    """
    Runs the 3-layer hybrid matching engine against a candidate profile and target job description.
    Returns scores, explainable evidence snippets, skill gaps, and career previews.
    """
    # 1. Resolve Resume Profile
    resume_profile = None
    raw_resume_text = ""

    if request.resume_profile:
        resume_profile = request.resume_profile.model_dump()
        raw_resume_text = request.resume_text or json.dumps(resume_profile)
    elif request.resume_id:
        latest = get_latest_resume()
        if latest and latest.get("resume_id") == request.resume_id:
            resume_profile = latest.get("extracted_profile")
            raw_resume_text = latest.get("raw_text", "")

    if not resume_profile:
        # Fallback to latest resume in database
        latest = get_latest_resume()
        if latest and latest.get("extracted_profile"):
            resume_profile = latest["extracted_profile"]
            raw_resume_text = latest.get("raw_text", "")
        else:
            # Fallback to demo software engineer profile
            demo_analysis = ai_service.analyze_resume(DEMO_RESUME_TEXT, "Demo_Software_Engineer_Resume.pdf")
            resume_profile = demo_analysis["extracted_profile"]
            raw_resume_text = demo_analysis["raw_text"]

    # 2. Resolve Job Data
    job_data = None
    if request.job_id:
        demo_jobs = load_demo_jobs()
        for j in demo_jobs:
            if j.get("id") == request.job_id:
                job_data = j
                break

    if not job_data and request.job_description:
        job_data = ai_service.analyze_job_description(request.job_description, title=request.job_title or "Target Role")

    if not job_data:
        # Default to first demo job (Junior Backend Developer)
        demo_jobs = load_demo_jobs()
        job_data = demo_jobs[0] if demo_jobs else {
            "title": "Backend Developer",
            "requirements": [{"name": "Python", "importance": "critical"}],
            "description": "Backend engineering role"
        }

    # 3. Execute Matching Engine
    match_result = matching_service.match_resume_to_job(
        resume_profile=resume_profile,
        raw_resume_text=raw_resume_text,
        job_data=job_data
    )

    # 4. Save to SQLite
    resume_id = request.resume_id or "demo_resume"
    save_match_result(
        match_id=match_result["match_id"],
        resume_id=resume_id,
        job_id=request.job_id,
        job_title=job_data.get("title", "Position"),
        match_data=match_result
    )

    return match_result


# Realistic Software Engineer demo resume content
DEMO_RESUME_TEXT = """Alex Mercer
San Francisco, CA | alex.mercer@email.com | (555) 019-2834 | linkedin.com/in/alexmercer | github.com/alexmercer

PROFESSIONAL SUMMARY
Results-oriented Software Engineer with 2+ years of hands-on experience designing, developing, and deploying scalable web services, RESTful APIs, and responsive frontends. Proven ability to build robust microservices and collaborate with engineering teams.

EDUCATION
B.Tech Information Technology | University of California, Berkeley (2019 - 2023)
GPA: 3.8/4.0 | Dean's Honor List

TECHNICAL SKILLS
Languages: Python, JavaScript, TypeScript, Java, SQL, HTML, CSS
Frameworks & Libraries: React, Node.js, Express, FastAPI, Tailwind CSS, Redux
Databases: PostgreSQL, MySQL, MongoDB, SQLite, Redis
Tools & DevOps: Git, GitHub, Docker, Linux, CI/CD pipelines, REST APIs, Microservices

WORK EXPERIENCE
Software Developer Intern | Apex Tech Solutions (2022 - 2023)
• Developed and deployed 12+ RESTful API microservices using Node.js, FastAPI, and PostgreSQL, serving 50,000+ daily requests with 99.9% uptime.
• Optimized database queries and created indexing strategies in MongoDB, reducing average API response times by 38%.
• Collaborated in an Agile Scrum squad of 6 engineers, participating in bi-weekly sprints and peer code reviews.
• Integrated automated CI/CD testing pipelines with GitHub Actions, improving release deployment speed by 45%.

PROJECTS
Food Delivery Platform (React, Node.js, MongoDB)
• Architected a full-stack food delivery web application using React, Express, and MongoDB.
• Implemented secure JWT-based candidate authentication and Stripe payment integration.
• Designed real-time order tracking with WebSockets and optimized state management with Redux Toolkit.

AI Resume & Job Matcher (Python, FastAPI, SQL, Git)
• Engineered an NLP matching pipeline using Python, Scikit-Learn, and FastAPI to score resume-job alignment.
• Built SQLite schema migrations and designed intuitive REST endpoints for candidate profile extraction.
• Managed version control using Git with automated unit tests and linting workflows.
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
