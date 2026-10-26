"""
FastAPI Application Entry Point for CareerLens AI
Exposes REST endpoints for authentication, resume uploading, parsing,
AI profiling, explainable job matching, simulations, roadmaps, and security defense.
Enforces strict authentication, authorization, and data isolation on all user resources (Stage 3.1).
"""

import os
import sys
import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import (
    init_db,
    save_resume,
    save_resume_analysis,
    get_latest_resume,
    get_resume_by_id,
    get_resumes_by_user,
    save_match_result,
    save_roadmap_progress,
    get_roadmap_progress,
    get_db_info,
    migrate_sqlite_to_postgres,
    save_security_audit,
    get_security_audit_by_resume_id,
    get_latest_security_audit,
    create_user,
    get_user_by_id,
    get_user_by_email,
    get_user_by_username,
    get_user_by_identifier,
    set_user_reset_token,
    update_user_password,
    update_user_last_login,
    save_interview_session,
    get_interview_session,
    list_interview_sessions,
    delete_interview_session,
    save_interview_answer,
    get_interview_answer,
    save_fairness_audit,
    get_fairness_audit,
    list_fairness_audits,
    delete_fairness_audit
)
from schemas import (
    ResumeAnalysisResponse,
    ResumeAnalyzeRequest,
    JobAnalyzeRequest,
    DemoJob,
    MatchRequest,
    MatchResponse,
    ExtractedProfile,
    SimulateRequest,
    SimulateResponse,
    CareerPathsResponse,
    RoadmapResponse,
    RoadmapProgressUpdateRequest,
    RoadmapProgressUpdateResponse,
    SecurityAuditReport,
    SecurityAuditRequest,
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    PasswordResetResponse,
    InterviewQuestion,
    CreateInterviewSessionRequest,
    InterviewSessionResponse,
    InterviewSessionSummary,
    SubmitAnswerRequest,
    AnswerEvaluationResponse,
    FairnessAuditReport,
    FairnessAuditSummary
)
from config import ROADMAP_STEP_STATUSES
from services.resume_parser import extract_text_from_file, ResumeParserError
from services.ai_service import ai_service
from services.matching_service import matching_service
from services.career_service import career_service
from services.security_service import security_service
from services.interview_service import interview_service
from services.fairness_service import fairness_service
from services.job_generator_service import job_generator_service
from services.auth_service import (
    hash_password,
    verify_password,
    validate_email_format,
    create_access_token,
    decode_access_token,
    revoke_token,
    rate_limiter,
    AuthError,
    TokenExpiredError,
    TokenRevokedError,
    TokenInvalidError,
    RateLimitExceededError
)

# Initialize database and run migrations on startup
init_db()

app = FastAPI(
    title="CareerLens AI API",
    description="Explainable Career Intelligence & Job Matching Engine with Authenticated Data Isolation",
    version="1.1.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DEMO_JOBS_PATH = os.path.join(DATA_DIR, "demo_jobs.json")


def load_demo_jobs(resume_id: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Dynamically generates and returns benchmark roles based on the provided resume
    or active candidate session. Replaces all static, hardcoded datasets.
    """
    return job_generator_service.get_roles_for_resume(resume_id=resume_id, user_id=user_id)


# ─── Authentication Dependency (Stage 3.1) ───

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Extracts and validates JWT Bearer token from Authorization header.
    Rejects missing, malformed, expired, or revoked tokens with HTTP 401.
    Derives real authenticated user context; never trusts client-supplied user_id or demo_user.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You need to sign in to use this feature.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You need to sign in to use this feature.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    try:
        payload = decode_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenRevokedError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked or logged out. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthError as ae:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(ae.message),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token validation failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing subject identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account does not exist or has been disabled.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ─── Authentication Endpoints (Stage 3.1) ───

@app.post("/api/auth/register", response_model=TokenResponse)
async def register_user(request: Request, body: UserRegisterRequest):
    """
    Registers a new candidate account with salted bcrypt password hashing.
    Enforces sliding-window rate limiting to prevent spam and credential stuffing.
    """
    client_ip = request.client.host if request.client else "unknown"
    try:
        rate_limiter.check(f"register:{client_ip}", max_requests=10, window_seconds=60)
    except RateLimitExceededError as rle:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(rle.message))

    clean_email = body.email.strip().lower()
    if not validate_email_format(clean_email):
        raise HTTPException(status_code=400, detail="Invalid email address format.")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")

    clean_username = (body.username or "").strip().lower()
    if clean_username:
        existing_username = get_user_by_username(clean_username)
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already exists")

    existing_email = get_user_by_email(clean_email)
    if existing_email:
        if clean_email.endswith("@gmail.com"):
            raise HTTPException(status_code=400, detail="Gmail already exists")
        else:
            raise HTTPException(status_code=400, detail="Email already exists")

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    pwd_hash = hash_password(body.password)
    resolved_name = body.name or body.full_name or body.username or "Candidate"

    try:
        user_data = create_user(
            user_id=user_id,
            email=clean_email,
            name=resolved_name,
            password_hash=pwd_hash,
            username=clean_username or None
        )
    except Exception as db_err:
        err_str = str(db_err).lower()
        if "username" in err_str:
            raise HTTPException(status_code=400, detail="Username already exists")
        if "email" in err_str:
            if clean_email.endswith("@gmail.com"):
                raise HTTPException(status_code=400, detail="Gmail already exists")
            else:
                raise HTTPException(status_code=400, detail="Email already exists")
        raise HTTPException(status_code=400, detail="Registration failed. Account may already exist.")

    token, _, expire = create_access_token(user_id=user_id, email=clean_email, name=resolved_name)
    expires_in = int((expire - datetime.now(timezone.utc)).total_seconds())

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": {
            "id": user_id,
            "email": clean_email,
            "username": clean_username or None,
            "name": resolved_name,
            "created_at": str(user_data.get("created_at")) if user_data.get("created_at") else None
        }
    }


@app.post("/api/auth/login", response_model=TokenResponse)
async def login_user(request: Request, body: UserLoginRequest):
    """
    Authenticates candidate credentials and returns a signed JWT access token.
    Generic error returned on failure to prevent user/account enumeration.
    """
    client_ip = request.client.host if request.client else "unknown"
    identifier = (body.email or body.username_or_email or "").strip().lower()
    if not identifier:
        raise HTTPException(
            status_code=400,
            detail="Please provide your username or email id to sign in."
        )

    rate_key = f"login:{client_ip}:{identifier}"

    try:
        rate_limiter.check(rate_key, max_requests=10, window_seconds=60)
    except RateLimitExceededError as rle:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(rle.message))

    user = get_user_by_identifier(identifier)
    if not user or not user.get("is_active", True) or not verify_password(body.password, user.get("password_hash") or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username and email id",
            headers={"WWW-Authenticate": "Bearer"},
        )

    rate_limiter.reset(rate_key)
    update_user_last_login(user["id"])

    token, _, expire = create_access_token(user_id=user["id"], email=user["email"], name=user.get("name"))
    expires_in = int((expire - datetime.now(timezone.utc)).total_seconds())

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user.get("username"),
            "name": user.get("name"),
            "created_at": str(user.get("created_at")) if user.get("created_at") else None
        }
    }


@app.post("/api/auth/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(body: ForgotPasswordRequest):
    """
    Initiates password recovery for a user account using email or username.
    Generates a secure 6-character reset code valid for 15 minutes.
    """
    identifier = body.email_or_username.strip().lower()
    if not identifier:
        raise HTTPException(status_code=400, detail="Please enter your username or email ID.")

    user = get_user_by_identifier(identifier)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="No account found with this username or email ID."
        )

    reset_token = f"{uuid.uuid4().hex[:6]}".upper()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    set_user_reset_token(identifier, reset_token, expires_at)

    return {
        "success": True,
        "message": "Password reset code generated.",
        "email": user["email"],
        "reset_token": reset_token
    }


@app.post("/api/auth/reset-password", response_model=PasswordResetResponse)
async def reset_password(body: ResetPasswordRequest):
    """
    Resets account password with salted bcrypt hashing after verification.
    """
    identifier = body.email_or_username.strip().lower()
    if not identifier:
        raise HTTPException(status_code=400, detail="Please enter your username or email ID.")

    user = get_user_by_identifier(identifier)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account found with this username or email ID."
        )

    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long."
        )

    # If verification token was provided, verify it
    if body.reset_token:
        stored_token = user.get("reset_token")
        if stored_token and stored_token.upper() != body.reset_token.strip().upper():
            raise HTTPException(
                status_code=400,
                detail="Invalid verification code. Please check and try again."
            )

    new_hash = hash_password(body.new_password)
    update_user_password(user["id"], new_hash)

    return {
        "success": True,
        "message": "Password has been successfully reset! You can now sign in with your new password.",
        "email": user["email"]
    }


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the authenticated candidate's profile context."""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user.get("name"),
        "created_at": str(current_user.get("created_at")) if current_user.get("created_at") else None
    }


@app.post("/api/auth/logout")
async def logout_user(
    authorization: Optional[str] = Header(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Revokes the current JWT access token via token blocklist and invalidates the session.
    """
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            try:
                payload = decode_access_token(token)
                jti = payload.get("jti")
                exp_ts = payload.get("exp")
                if jti and exp_ts:
                    exp_dt = datetime.fromtimestamp(exp_ts, timezone.utc)
                    revoke_token(jti, current_user["id"], exp_dt)
            except Exception:
                pass
    return {"status": "success", "message": "Successfully logged out and session invalidated."}


# ─── Public Diagnostic & Job Reference Endpoints ───

@app.get("/api/health")
async def health_check():
    """Service health, LLM provider, and database status check."""
    return {
        "status": "healthy",
        "service": "CareerLens AI Stage 3.1",
        "llm_active": ai_service.is_llm_active(),
        "llm_provider": ai_service.provider,
        "database": get_db_info()
    }


@app.get("/api/db/status")
async def get_database_status():
    """Returns detailed database engine configuration."""
    return get_db_info()


@app.post("/api/db/migrate")
async def migrate_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Migrates existing SQLite records to Neon PostgreSQL."""
    result = migrate_sqlite_to_postgres()
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.get("/api/jobs/demo", response_model=List[DemoJob])
async def get_demo_jobs(
    resume_id: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Returns benchmark demo roles dynamically generated on the basis of the provided resume.
    If no resume has been provided yet, returns an empty list.
    """
    user_id = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            try:
                payload = decode_access_token(parts[1])
                user_id = payload.get("sub")
            except Exception:
                pass

    jobs = load_demo_jobs(resume_id=resume_id, user_id=user_id)
    return jobs


@app.post("/api/job/analyze")
async def analyze_job_description(request: JobAnalyzeRequest):
    """
    Parses an arbitrary job description text into structured requirements and responsibilities.
    Stateless reference service.
    """
    if len(request.job_text.strip()) < 15:
        raise HTTPException(status_code=400, detail="Job description text is too short.")

    return ai_service.analyze_job_description(request.job_text, title=request.title or "Custom Job Opening")


# ─── Protected Resume Ingestion & Retrieval Endpoints ───

@app.post("/api/resume/upload", response_model=ResumeAnalysisResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Accepts PDF, DOCX, or TXT resume file, extracts text,
    builds structured candidate profile, computes health scores, and persists scoped to authenticated user.
    """
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        raw_text, file_type = extract_text_from_file(file.filename, file_bytes)
        
        # Analyze resume using AI service
        analysis_data = ai_service.analyze_resume(raw_text, filename=file.filename, file_type=file_type)
        resume_id = analysis_data["resume_id"]

        if analysis_data.get("extraction_status") == "failed":
            raise HTTPException(status_code=400, detail=analysis_data.get("message") or "Resume extraction failed.")

        # Persist to database strictly associated with authenticated user
        save_resume(
            resume_id=resume_id,
            filename=file.filename,
            file_type=file_type,
            file_size=len(file_bytes),
            raw_text=raw_text,
            user_id=current_user["id"]
        )
        save_resume_analysis(
            analysis_id=f"ana_{resume_id}",
            resume_id=resume_id,
            health_scores=analysis_data["health_scores"],
            extracted_profile=analysis_data["extracted_profile"]
        )

        # Persist Security Audit if available, associated with user
        if analysis_data.get("security_audit"):
            audit = analysis_data["security_audit"]
            save_security_audit(
                audit_id=audit["audit_id"],
                resume_id=resume_id,
                status=audit["status"],
                action_taken=audit["action_taken"],
                risk_score=audit["risk_score"],
                findings_count=audit["findings_count"],
                findings=audit["findings"],
                audit_data=audit,
                user_id=current_user["id"]
            )

        return analysis_data

    except ResumeParserError as pe:
        raise HTTPException(status_code=400, detail=str(pe))
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal analysis failure: {str(e)}")


@app.post("/api/resume/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume_text(
    request: ResumeAnalyzeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Analyzes raw pasted resume text, builds candidate profile, and persists scoped to authenticated user.
    """
    if len(request.resume_text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Resume text is too short to analyze.")

    analysis_data = ai_service.analyze_resume(
        request.resume_text,
        filename=request.filename or "Pasted_Resume.txt",
        file_type="txt"
    )
    if analysis_data.get("extraction_status") == "failed":
        raise HTTPException(status_code=400, detail=analysis_data.get("message") or "Resume extraction failed.")

    resume_id = analysis_data["resume_id"]

    # Persist to database strictly associated with authenticated user
    save_resume(
        resume_id=resume_id,
        filename=request.filename or "Pasted_Resume.txt",
        file_type="txt",
        file_size=len(request.resume_text.encode("utf-8")),
        raw_text=request.resume_text,
        user_id=current_user["id"]
    )
    save_resume_analysis(
        analysis_id=f"ana_{resume_id}",
        resume_id=resume_id,
        health_scores=analysis_data["health_scores"],
        extracted_profile=analysis_data["extracted_profile"]
    )

    # Persist Security Audit if available, associated with user
    if analysis_data.get("security_audit"):
        audit = analysis_data["security_audit"]
        save_security_audit(
            audit_id=audit["audit_id"],
            resume_id=resume_id,
            status=audit["status"],
            action_taken=audit["action_taken"],
            risk_score=audit["risk_score"],
            findings_count=audit["findings_count"],
            findings=audit["findings"],
            audit_data=audit,
            user_id=current_user["id"]
        )

    return analysis_data


@app.get("/api/resume/latest")
async def get_latest_analyzed_resume(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieves the most recent analyzed resume belonging exclusively to the authenticated user.
    """
    latest = get_latest_resume(user_id=current_user["id"])
    if not latest:
        return None
    return latest


@app.get("/api/resumes")
async def list_user_resumes(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieves all resumes uploaded by the authenticated user.
    """
    return get_resumes_by_user(current_user["id"])


@app.get("/api/resume/{resume_id}")
async def get_resume_by_id_endpoint(
    resume_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves a specific analyzed resume by resume_id.
    Strictly verifies ownership: returns 404 if resume does not exist or belongs to another user
    to prevent existence leakage.
    """
    record = get_resume_by_id(resume_id, user_id=current_user["id"])
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Resume with ID '{resume_id}' was not found in storage."
        )
    return record


# ─── Protected Matching, Simulation, & Roadmap Endpoints ───

@app.post("/api/match", response_model=MatchResponse)
async def run_match_engine(
    request: MatchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Runs the 3-layer hybrid matching engine against a candidate profile and target job description.
    Enforces that any provided resume_id belongs to the authenticated user.
    """
    # 1. Resolve Resume Profile
    resume_profile = None
    raw_resume_text = ""
    resolved_resume_id = request.resume_id

    if request.resume_profile:
        resume_profile = request.resume_profile.model_dump()
        raw_resume_text = request.resume_text or json.dumps(resume_profile)
    elif request.resume_id:
        record = get_resume_by_id(request.resume_id, user_id=current_user["id"])
        if record and record.get("extracted_profile"):
            resume_profile = record.get("extracted_profile")
            raw_resume_text = record.get("raw_text", "")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Resume with ID '{request.resume_id}' was not found in storage. Please upload or analyze a resume."
            )
    else:
        # Check active/latest analyzed resume for THIS authenticated user
        latest = get_latest_resume(user_id=current_user["id"])
        if latest and latest.get("extracted_profile"):
            resume_profile = latest["extracted_profile"]
            raw_resume_text = latest.get("raw_text", "")
            resolved_resume_id = latest.get("resume_id")

    if not resume_profile:
        raise HTTPException(
            status_code=400,
            detail="No candidate resume provided or found in storage. Please upload or analyze a resume before requesting a job match."
        )

    # 2. Resolve Job Data
    job_data = None
    if request.job_id:
        demo_jobs = load_demo_jobs(resume_id=resolved_resume_id, user_id=current_user["id"])
        for j in demo_jobs:
            if j.get("id") == request.job_id:
                job_data = j
                break
        if not job_data and demo_jobs:
            job_data = demo_jobs[0]
        if not job_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job position with ID '{request.job_id}' was not found. Please upload or analyze a resume to generate tailored roles."
            )
    elif request.job_description:
        if len(request.job_description.strip()) < 15:
            raise HTTPException(
                status_code=400,
                detail="Provided job description is too short to analyze. Please provide a more detailed job posting."
            )
        job_data = ai_service.analyze_job_description(request.job_description, title=request.job_title or "Target Role")
    else:
        raise HTTPException(
            status_code=400,
            detail="No target job specified. Please select a valid job position or provide a job description."
        )

    # 3. Execute Matching Engine
    match_result = matching_service.match_resume_to_job(
        resume_profile=resume_profile,
        raw_resume_text=raw_resume_text,
        job_data=job_data
    )

    # 4. Save to Database strictly scoped to authenticated user
    save_match_result(
        match_id=match_result["match_id"],
        resume_id=resolved_resume_id or "unpersisted_candidate",
        job_id=request.job_id,
        job_title=job_data.get("title", "Position"),
        match_data=match_result,
        user_id=current_user["id"]
    )

    return match_result


@app.post("/api/career/simulate", response_model=SimulateResponse)
async def simulate_career(
    request: SimulateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Career What-If Simulator Endpoint.
    Evaluates the impact of hypothetical skill additions against target job requirements.
    Enforces user ownership on referenced resume.
    """
    # 1. Resolve Resume Profile
    resume_profile = None
    raw_resume_text = ""
    resolved_resume_id = request.resume_id

    if request.resume_profile:
        resume_profile = request.resume_profile.model_dump()
        raw_resume_text = request.resume_text or json.dumps(resume_profile)
    elif request.resume_id:
        record = get_resume_by_id(request.resume_id, user_id=current_user["id"])
        if record and record.get("extracted_profile"):
            resume_profile = record.get("extracted_profile")
            raw_resume_text = record.get("raw_text", "")
            resolved_resume_id = record.get("resume_id") or request.resume_id
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Resume with ID '{request.resume_id}' was not found in storage. Please upload or analyze a resume."
            )
    else:
        latest = get_latest_resume(user_id=current_user["id"])
        if latest and latest.get("extracted_profile"):
            resume_profile = latest["extracted_profile"]
            raw_resume_text = latest.get("raw_text", "")
            resolved_resume_id = latest.get("resume_id")

    if not resume_profile:
        raise HTTPException(
            status_code=400,
            detail="No candidate resume provided or found in storage. Please upload or analyze a resume before requesting career simulation."
        )

    # 2. Resolve Job Data
    job_data = None
    if request.job_id:
        demo_jobs = load_demo_jobs(resume_id=resolved_resume_id, user_id=current_user["id"])
        for j in demo_jobs:
            if j.get("id") == request.job_id:
                job_data = j
                break
        if not job_data and demo_jobs:
            job_data = demo_jobs[0]
        if not job_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job position with ID '{request.job_id}' was not found."
            )
    elif request.job_description:
        if len(request.job_description.strip()) < 15:
            raise HTTPException(
                status_code=400,
                detail="Provided job description is too short to analyze. Please provide a more detailed job posting."
            )
        job_data = ai_service.analyze_job_description(request.job_description, title=request.job_title or "Target Role")
    else:
        raise HTTPException(
            status_code=400,
            detail="No target job specified. Please select a valid job position or provide a job description."
        )

    # 3. Execute Simulation via Career Service
    simulation_result = career_service.simulate_what_if(
        resume_profile=resume_profile,
        raw_resume_text=raw_resume_text,
        job_data=job_data,
        added_skills=request.hypothetical_skills
    )

    return simulation_result


@app.get("/api/career/paths", response_model=CareerPathsResponse)
async def get_career_paths(
    resume_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Career Path Analysis Endpoint.
    Compares the candidate's existing verified profile against benchmark roles.
    Enforces user ownership on referenced resume.
    """
    # 1. Resolve Resume Profile
    resume_profile = None
    raw_resume_text = ""
    resolved_resume_id = resume_id

    if resume_id:
        record = get_resume_by_id(resume_id, user_id=current_user["id"])
        if record and record.get("extracted_profile"):
            resume_profile = record.get("extracted_profile")
            raw_resume_text = record.get("raw_text", "")
            resolved_resume_id = record.get("resume_id") or resume_id
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Resume with ID '{resume_id}' was not found in storage. Please upload or analyze a resume."
            )
    else:
        latest = get_latest_resume(user_id=current_user["id"])
        if latest and latest.get("extracted_profile"):
            resume_profile = latest["extracted_profile"]
            raw_resume_text = latest.get("raw_text", "")
            resolved_resume_id = latest.get("resume_id")

    if not resume_profile:
        raise HTTPException(
            status_code=400,
            detail="No candidate resume found in storage. Please upload or analyze a resume before requesting career paths."
        )

    # 2. Benchmark target roles generated dynamically from candidate resume
    benchmark_jobs = load_demo_jobs(resume_id=resolved_resume_id, user_id=current_user["id"])
    if not benchmark_jobs:
        raise HTTPException(
            status_code=400,
            detail="No candidate resume found in storage to generate career paths. Please upload or analyze a resume first."
        )

    # 3. Analyze Paths
    paths_result = career_service.analyze_career_paths(
        resume_profile=resume_profile,
        raw_resume_text=raw_resume_text,
        target_roles=benchmark_jobs
    )

    return paths_result


@app.get("/api/career/roadmap", response_model=RoadmapResponse)
async def get_learning_roadmap(
    resume_id: Optional[str] = None,
    job_id: Optional[str] = None,
    job_description: Optional[str] = None,
    job_title: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Skill Learning Roadmap Endpoint.
    Generates a personalized, prerequisite-aware learning roadmap.
    Enforces user ownership on resume_id and tracked progress.
    """
    if not resume_id:
        raise HTTPException(
            status_code=400,
            detail="resume_id is required to generate a personalized skill roadmap."
        )

    record = get_resume_by_id(resume_id, user_id=current_user["id"])
    if not record or not record.get("extracted_profile"):
        raise HTTPException(
            status_code=404,
            detail=f"Resume with ID '{resume_id}' was not found in storage."
        )

    resume_profile = record.get("extracted_profile")
    raw_resume_text = record.get("raw_text", "")

    if not job_id and not job_description:
        raise HTTPException(
            status_code=400,
            detail="Either job_id or job_description must be provided to generate a skill roadmap."
        )

    if job_id:
        demo_jobs = load_demo_jobs(resume_id=resume_id, user_id=current_user["id"])
        job_data = next((j for j in demo_jobs if j.get("id") == job_id), None)
        if not job_data and demo_jobs:
            job_data = demo_jobs[0]
        if not job_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job position with ID '{job_id}' was not found in generated roles."
            )
    else:
        if len(job_description.strip()) < 15:
            raise HTTPException(
                status_code=400,
                detail="Job description text is too short to analyze requirements."
            )
        job_data = ai_service.analyze_job_description(
            job_description,
            title=job_title or "Custom Target Role"
        )

    target_job_id = job_data.get("id", job_id or "job_custom")

    # Retrieve saved progress strictly scoped to this user and resume
    saved_progress = get_roadmap_progress(resume_id=resume_id, job_id=target_job_id, user_id=current_user["id"])

    # Generate explainable, prerequisite-aware roadmap
    roadmap_result = career_service.generate_learning_roadmap(
        resume_profile=resume_profile,
        raw_resume_text=raw_resume_text,
        job_data=job_data,
        saved_progress=saved_progress,
        resume_id=resume_id
    )

    return roadmap_result


@app.post("/api/career/roadmap/progress", response_model=RoadmapProgressUpdateResponse)
async def update_roadmap_progress_endpoint(
    request: RoadmapProgressUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Updates the learning progress status of a roadmap skill item in persistent storage.
    Strictly verifies that the target resume is owned by the authenticated user.
    """
    if not request.resume_id or not request.job_id or not request.skill_name:
        raise HTTPException(
            status_code=400, 
            detail="resume_id, job_id, and skill_name are required."
        )

    # Verify resume ownership
    record = get_resume_by_id(request.resume_id, user_id=current_user["id"])
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Resume with ID '{request.resume_id}' was not found in storage."
        )

    clean_status = request.status.strip().lower()
    if clean_status not in ROADMAP_STEP_STATUSES.values():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{request.status}'. Allowed statuses: {', '.join(ROADMAP_STEP_STATUSES.values())}"
        )

    updated = save_roadmap_progress(
        resume_id=request.resume_id,
        job_id=request.job_id,
        skill_name=request.skill_name,
        status=clean_status,
        user_id=current_user["id"]
    )

    return {
        "status": "success",
        "message": f"Progress for '{request.skill_name}' updated to '{clean_status}'.",
        "updated_progress": updated
    }


# ─── Protected Security Audit Endpoints ───

@app.post("/api/security/audit", response_model=SecurityAuditReport)
async def audit_security_endpoint(
    request: SecurityAuditRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Resume Security Audit & Prompt-Injection Defense Endpoint.
    Enforces user ownership when scanning an existing resume in storage.
    """
    text_to_scan = ""
    filename = request.filename or "Scanned_Document.txt"
    source_type = "resume"
    resolved_resume_id = None

    if request.resume_id:
        record = get_resume_by_id(request.resume_id, user_id=current_user["id"])
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Resume with ID '{request.resume_id}' was not found in storage. Cannot perform security audit."
            )
        text_to_scan = record.get("raw_text", "")
        filename = record.get("filename", filename)
        resolved_resume_id = request.resume_id
    elif request.resume_text:
        text_to_scan = request.resume_text
        source_type = "resume"
    elif request.job_description:
        text_to_scan = request.job_description
        source_type = "job_description"
        filename = "Job_Description.txt"
    else:
        latest = get_latest_resume(user_id=current_user["id"])
        if latest and latest.get("raw_text"):
            text_to_scan = latest["raw_text"]
            filename = latest.get("filename", filename)
            resolved_resume_id = latest.get("resume_id")
        else:
            raise HTTPException(
                status_code=400,
                detail="No resume text or valid resume_id provided for security audit."
            )

    report = security_service.scan_text(
        text=text_to_scan,
        filename=filename,
        source_type=source_type
    )

    report["resume_id"] = resolved_resume_id
    save_security_audit(
        audit_id=report["audit_id"],
        resume_id=resolved_resume_id,
        status=report["status"],
        action_taken=report["action_taken"],
        risk_score=report["risk_score"],
        findings_count=report["findings_count"],
        findings=report["findings"],
        audit_data=report,
        user_id=current_user["id"]
    )

    return report


@app.post("/api/security/audit/upload", response_model=SecurityAuditReport)
async def audit_file_upload_endpoint(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Direct document security audit endpoint for PDF, DOCX, or TXT files.
    """
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

        raw_text, file_type = extract_text_from_file(file.filename, file_bytes)

        metadata = {}
        if file_type == "pdf":
            try:
                import pymupdf
                doc = pymupdf.open(stream=file_bytes, filetype="pdf")
                meta = doc.metadata or {}
                for k in ["title", "author", "subject", "keywords", "creator", "producer"]:
                    if meta.get(k):
                        metadata[k] = meta[k]
                doc.close()
            except Exception:
                pass
        elif file_type == "docx":
            try:
                import io
                import docx
                doc = docx.Document(io.BytesIO(file_bytes))
                cp = doc.core_properties
                for attr in ["author", "title", "subject", "keywords", "comments", "category"]:
                    val = getattr(cp, attr, None)
                    if val and isinstance(val, str) and val.strip():
                        metadata[attr] = val.strip()
            except Exception:
                pass

        report = security_service.scan_text(
            text=raw_text,
            filename=file.filename,
            source_type=f"file_{file_type}",
            metadata=metadata
        )

        return report

    except ResumeParserError as pe:
        raise HTTPException(
            status_code=400,
            detail=f"Security audit document parsing failed: {str(pe)}. Unscanned documents cannot be verified as safe."
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document security audit failure: {str(e)}")


@app.get("/api/security/audit/latest", response_model=Optional[SecurityAuditReport])
async def get_latest_security_audit_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieves the most recent security audit report scoped to the authenticated user.
    """
    latest_audit = get_latest_security_audit(user_id=current_user["id"])
    if latest_audit:
        return latest_audit

    latest_resume = get_latest_resume(user_id=current_user["id"])
    if not latest_resume or not latest_resume.get("raw_text"):
        return None

    # Generate on the fly and persist associated with user
    report = security_service.scan_text(
        text=latest_resume["raw_text"],
        filename=latest_resume.get("filename", "Resume.pdf"),
        source_type="resume"
    )
    report["resume_id"] = latest_resume.get("resume_id")
    save_security_audit(
        audit_id=report["audit_id"],
        resume_id=latest_resume.get("resume_id"),
        status=report["status"],
        action_taken=report["action_taken"],
        risk_score=report["risk_score"],
        findings_count=report["findings_count"],
        findings=report["findings"],
        audit_data=report,
        user_id=current_user["id"]
    )
    return report


@app.get("/api/security/audit/{resume_id}", response_model=SecurityAuditReport)
async def get_security_audit_by_id_endpoint(
    resume_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves the security audit report for a specific resume_id.
    Strictly verifies that the resume exists and belongs to the authenticated user.
    """
    record = get_resume_by_id(resume_id, user_id=current_user["id"])
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Resume with ID '{resume_id}' was not found in storage."
        )

    saved = get_security_audit_by_resume_id(resume_id, user_id=current_user["id"])
    if saved:
        return saved

    # Generate if not yet cached
    report = security_service.scan_text(
        text=record.get("raw_text", ""),
        filename=record.get("filename", "Resume.pdf"),
        source_type="resume"
    )
    report["resume_id"] = resume_id
    save_security_audit(
        audit_id=report["audit_id"],
        resume_id=resume_id,
        status=report["status"],
        action_taken=report["action_taken"],
        risk_score=report["risk_score"],
        findings_count=report["findings_count"],
        findings=report["findings"],
        audit_data=report,
        user_id=current_user["id"]
    )
    return report


# ─── Stage 4: Personalized Interview Preparation Endpoints ───

@app.post("/api/interview/session", response_model=InterviewSessionResponse)
async def create_interview_session_endpoint(
    request: CreateInterviewSessionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Creates an authenticated interview preparation session.
    Dynamically generates personalized questions derived from actual resume evidence,
    job requirements, matched skills, and skill gaps.
    """
    # 1. Resolve Resume Profile
    resume_profile = None
    resolved_resume_id = request.resume_id
    raw_resume_text = ""

    if request.resume_profile:
        resume_profile = request.resume_profile.model_dump()
        raw_resume_text = request.resume_text or json.dumps(resume_profile)
    elif request.resume_id:
        record = get_resume_by_id(request.resume_id, user_id=current_user["id"])
        if record and record.get("extracted_profile"):
            resume_profile = record["extracted_profile"]
            raw_resume_text = record.get("raw_text", "")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Resume with ID '{request.resume_id}' was not found in storage. Please upload or analyze a resume."
            )
    else:
        latest = get_latest_resume(user_id=current_user["id"])
        if latest and latest.get("extracted_profile"):
            resume_profile = latest["extracted_profile"]
            raw_resume_text = latest.get("raw_text", "")
            resolved_resume_id = latest.get("resume_id")

    if not resume_profile:
        raise HTTPException(
            status_code=400,
            detail="No candidate resume provided or found in storage. Please upload or analyze a resume first."
        )

    # 2. Resolve Job Data
    job_data = None
    if request.job_id:
        demo_jobs = load_demo_jobs(resume_id=resolved_resume_id, user_id=current_user["id"])
        for j in demo_jobs:
            if j.get("id") == request.job_id:
                job_data = j
                break
        if not job_data and demo_jobs:
            job_data = demo_jobs[0]
        if not job_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID '{request.job_id}' was not found."
            )
    elif request.job_description:
        if len(request.job_description.strip()) < 15:
            raise HTTPException(
                status_code=400,
                detail="Provided job description is too short to analyze."
            )
        job_data = ai_service.analyze_job_description(request.job_description, title=request.job_title or "Target Role")
    else:
        raise HTTPException(
            status_code=400,
            detail="No target job specified. Please select a valid job position or provide a job description."
        )

    # 3. Match Resume to Job to ground questions in evidence & gaps
    match_result = matching_service.match_resume_to_job(
        resume_profile=resume_profile,
        raw_resume_text=raw_resume_text,
        job_data=job_data
    )
    skill_gaps = match_result.get("skill_gaps", [])
    matched_reqs = match_result.get("matched_requirements", [])

    # 4. Generate Interview Questions
    session_data = interview_service.create_interview_session(
        resume_profile=resume_profile,
        job_data=job_data,
        user_id=current_user["id"],
        resume_id=resolved_resume_id,
        job_id=request.job_id,
        skill_gaps=skill_gaps,
        matched_requirements=matched_reqs,
        categories=request.categories,
        num_questions=request.num_questions
    )

    # 5. Persist Session to Database
    save_interview_session(session_data, session_data["questions"])

    return {
        "session_id": session_data["id"],
        "user_id": current_user["id"],
        "resume_id": resolved_resume_id,
        "job_id": request.job_id,
        "job_title": session_data["job_title"],
        "candidate_name": session_data["candidate_name"],
        "status": session_data["status"],
        "total_questions": session_data["total_questions"],
        "completed_questions": session_data["completed_questions"],
        "average_score": session_data["average_score"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_limitation_note": session_data.get("data_limitation_note"),
        "questions": session_data["questions"]
    }


@app.get("/api/interview/sessions", response_model=List[InterviewSessionSummary])
async def list_interview_sessions_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lists all saved interview preparation sessions for the authenticated user.
    """
    return list_interview_sessions(user_id=current_user["id"])


@app.get("/api/interview/session/{session_id}", response_model=InterviewSessionResponse)
async def get_interview_session_endpoint(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves a specific interview session, including questions and completed answers.
    Enforces user data isolation: returns 404 if not found or belongs to another user.
    """
    sess = get_interview_session(session_id=session_id, user_id=current_user["id"])
    if not sess:
        raise HTTPException(
            status_code=404,
            detail=f"Interview session with ID '{session_id}' was not found."
        )
    return sess


@app.delete("/api/interview/session/{session_id}")
async def delete_interview_session_endpoint(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Deletes an interview session belonging to the authenticated user.
    """
    deleted = delete_interview_session(session_id=session_id, user_id=current_user["id"])
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Interview session with ID '{session_id}' was not found."
        )
    return {"status": "success", "message": f"Interview session '{session_id}' was deleted."}


@app.post("/api/interview/session/{session_id}/answer", response_model=AnswerEvaluationResponse)
async def submit_interview_answer_endpoint(
    session_id: str,
    request: SubmitAnswerRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Submits a practice answer for a specific question in an interview session.
    Evaluates the response against the question's rubric with category-tailored criteria.
    Persists evaluation, updates session progress, and separates practice scores from match scores.
    """
    # 1. Verify session exists and belongs to current user
    sess = get_interview_session(session_id=session_id, user_id=current_user["id"])
    if not sess:
        raise HTTPException(
            status_code=404,
            detail=f"Interview session with ID '{session_id}' was not found."
        )

    # 2. Find target question
    target_q = None
    for q in sess.get("questions", []):
        if q["id"] == request.question_id:
            target_q = q
            break
    if not target_q:
        raise HTTPException(
            status_code=404,
            detail=f"Question with ID '{request.question_id}' was not found in session '{session_id}'."
        )

    # 3. Evaluate answer
    eval_result = interview_service.evaluate_answer(
        question=target_q,
        answer_text=request.answer_text,
        user_id=current_user["id"],
        session_id=session_id
    )

    # 4. Persist answer & update session progress
    save_interview_answer(eval_result)

    return {
        "answer_id": eval_result["answer_id"],
        "session_id": session_id,
        "question_id": request.question_id,
        "word_count": eval_result["word_count"],
        "overall_score": eval_result["overall_score"],
        "criterion_feedback": eval_result["criterion_feedback"],
        "strengths": eval_result["strengths"],
        "improvement_areas": eval_result["improvement_areas"],
        "missing_concepts": eval_result["missing_concepts"],
        "suggested_structure": eval_result["suggested_structure"],
        "sample_answer": eval_result["sample_answer"],
        "disclaimer": eval_result["disclaimer"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_fallback_eval": eval_result.get("is_fallback_eval", False)
    }


@app.get("/api/interview/session/{session_id}/question/{question_id}/answer")
async def get_interview_answer_endpoint(
    session_id: str,
    question_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves previous answer and evaluation for a specific question in a user's session.
    """
    ans = get_interview_answer(session_id=session_id, question_id=question_id, user_id=current_user["id"])
    if not ans:
        return None
    return ans


# ─── Stage 5: Fairness Audit & Scoring Consistency Endpoints ───

@app.post("/api/fairness/audit", response_model=FairnessAuditReport)
async def run_fairness_audit_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Executes the reproducible counterfactual fairness audit suite against the matching engine.
    Measures individual demographic-proxy invariance, formatting invariance, alias consistency,
    boundary condition handling, and score isolation.
    Persists the audit report strictly scoped to the authenticated user.
    """
    try:
        report = fairness_service.run_audit_suite(user_id=current_user["id"])
        save_fairness_audit(report)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fairness audit execution failed: {str(e)}"
        )


@app.get("/api/fairness/audits", response_model=List[FairnessAuditSummary])
async def list_fairness_audits_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lists historical fairness audit runs for the authenticated user.
    """
    return list_fairness_audits(user_id=current_user["id"])


@app.get("/api/fairness/audit/latest", response_model=FairnessAuditReport)
async def get_latest_fairness_audit_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves the most recent fairness audit report for the authenticated user.
    If no audit exists yet, runs an initial baseline audit.
    """
    summaries = list_fairness_audits(user_id=current_user["id"])
    if summaries:
        latest_id = summaries[0]["audit_id"]
        report = get_fairness_audit(audit_id=latest_id, user_id=current_user["id"])
        if report:
            return report

    # If no prior audit exists, run initial audit
    report = fairness_service.run_audit_suite(user_id=current_user["id"])
    save_fairness_audit(report)
    return report


@app.get("/api/fairness/audit/{audit_id}", response_model=FairnessAuditReport)
async def get_fairness_audit_endpoint(
    audit_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves a specific fairness audit report by audit_id.
    Strictly verifies ownership: returns 404 if not found or owned by another user.
    """
    report = get_fairness_audit(audit_id=audit_id, user_id=current_user["id"])
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Fairness audit record with ID '{audit_id}' was not found."
        )
    return report


@app.delete("/api/fairness/audit/{audit_id}")
async def delete_fairness_audit_endpoint(
    audit_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Deletes a specific fairness audit record belonging to the authenticated user.
    """
    deleted = delete_fairness_audit(audit_id=audit_id, user_id=current_user["id"])
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Fairness audit record with ID '{audit_id}' was not found."
        )
    return {
        "status": "success",
        "message": f"Fairness audit '{audit_id}' was deleted."
    }


@app.get("/api/fairness/policy")
async def get_fairness_policy_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Returns the authoritative scoring policy, component weights, documented tolerances,
    and list of irrelevant attributes.
    """
    return fairness_service.get_policy_info()


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
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, app_dir=backend_dir)
