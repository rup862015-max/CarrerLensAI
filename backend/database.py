"""
PostgreSQL (Neon) & SQLite Unified Database Layer for CareerLens AI
Supports Neon PostgreSQL with connection pooling / SSL, and seamless SQLite fallback.
"""

import os
import sys
import json
import sqlite3
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from backend or root .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Database connection settings
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("NEON_DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or ""
).strip()

SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "careerlens.db")

# Detect PostgreSQL / Neon
IS_POSTGRES = bool(DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")))

if IS_POSTGRES:
    # Fix postgres:// legacy prefix if needed
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Ensure SSL is enabled for Neon DB connections
    if "sslmode=" not in DATABASE_URL and "?" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"
    elif "sslmode=" not in DATABASE_URL and "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


def get_db_type() -> str:
    """Returns 'neon_postgres' if connected to Neon/PostgreSQL, otherwise 'sqlite'."""
    return "neon_postgres" if (IS_POSTGRES and PSYCOPG2_AVAILABLE) else "sqlite"


def get_db_info() -> Dict[str, Any]:
    """Returns diagnostic database connection metadata (masks credentials)."""
    db_type = get_db_type()
    if db_type == "neon_postgres":
        # Mask password in URL for display
        masked_url = DATABASE_URL
        if "@" in masked_url:
            prefix, rest = masked_url.split("@", 1)
            if ":" in prefix:
                proto_user = prefix.rsplit(":", 1)[0]
                masked_url = f"{proto_user}:****@{rest}"
        return {
            "type": "PostgreSQL (Neon)",
            "driver": "psycopg2",
            "connection": masked_url,
            "connected": True
        }
    else:
        return {
            "type": "SQLite (Local Fallback)",
            "driver": "sqlite3",
            "connection": f"{os.path.basename(SQLITE_DB_PATH)} (local_storage)",
            "connected": True
        }


def get_postgres_connection():
    """Establishes connection to Neon PostgreSQL."""
    if not PSYCOPG2_AVAILABLE:
        raise RuntimeError("psycopg2-binary is not installed. Please run `pip install psycopg2-binary`.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_sqlite_connection() -> sqlite3.Connection:
    """Establishes connection to local SQLite."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_db_connection():
    """Returns an active database connection depending on configuration."""
    if IS_POSTGRES and PSYCOPG2_AVAILABLE:
        try:
            return get_postgres_connection()
        except Exception as e:
            print(f"[Database Warning] Failed to connect to Neon PostgreSQL ({e}). Falling back to SQLite.")
            return get_sqlite_connection()
    return get_sqlite_connection()


def init_db():
    """Initializes tables for Neon PostgreSQL or SQLite and applies migrations."""
    if IS_POSTGRES and PSYCOPG2_AVAILABLE:
        try:
            _init_postgres_db()
            from migrations import apply_migrations
            apply_migrations()
            print("[Database] Successfully connected to Neon PostgreSQL and initialized schema.")
            return
        except Exception as e:
            print(f"[Database Error] Neon PostgreSQL init failed: {e}. Falling back to SQLite.")
    
    _init_sqlite_db()
    from migrations import apply_migrations
    apply_migrations()
    print("[Database] Initialized local SQLite schema.")


def _init_postgres_db():
    """PostgreSQL DDL schema setup."""
    conn = get_postgres_connection()
    with conn.cursor() as cursor:
        # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(255) PRIMARY KEY,
            username VARCHAR(255) UNIQUE,
            email VARCHAR(255) UNIQUE,
            name VARCHAR(255),
            password_hash VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            last_login TIMESTAMP WITH TIME ZONE,
            reset_token VARCHAR(255),
            reset_token_expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Resumes Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) DEFAULT 'demo_user',
            filename VARCHAR(500) NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            file_size BIGINT,
            raw_text TEXT NOT NULL,
            uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 3. Resume Analyses Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_analyses (
            id VARCHAR(255) PRIMARY KEY,
            resume_id VARCHAR(255) NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
            overall_health_score INT NOT NULL,
            content_quality_score INT NOT NULL,
            skills_coverage_score INT NOT NULL,
            experience_clarity_score INT NOT NULL,
            project_strength_score INT NOT NULL,
            ats_readability_score INT NOT NULL,
            extracted_profile JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 4. Job Descriptions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_descriptions (
            id VARCHAR(255) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            department VARCHAR(255),
            raw_text TEXT NOT NULL,
            requirements JSONB NOT NULL,
            is_demo BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 5. Match Results Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_results (
            id VARCHAR(255) PRIMARY KEY,
            resume_id VARCHAR(255) NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
            job_id VARCHAR(255),
            job_title VARCHAR(255) NOT NULL,
            overall_score INT NOT NULL,
            skill_match INT NOT NULL,
            experience_match INT NOT NULL,
            education_match INT NOT NULL,
            project_relevance INT NOT NULL,
            semantic_fit INT NOT NULL,
            matched_requirements JSONB NOT NULL,
            missing_requirements JSONB NOT NULL,
            skill_gaps JSONB NOT NULL,
            career_preview JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 6. Roadmap Progress Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roadmap_progress (
            id VARCHAR(255) PRIMARY KEY,
            resume_id VARCHAR(255) NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
            job_id VARCHAR(255) NOT NULL,
            skill_name VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'not_started',
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (resume_id, job_id, skill_name)
        );
        """)

        # 7. Security Audits Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_audits (
            id VARCHAR(255) PRIMARY KEY,
            resume_id VARCHAR(255),
            status VARCHAR(50) NOT NULL,
            action_taken VARCHAR(50) NOT NULL,
            risk_score INT NOT NULL,
            findings_count JSONB NOT NULL,
            findings JSONB NOT NULL,
            audit_data JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Insert default demo user if not exists
        cursor.execute("""
        INSERT INTO users (id, email, name)
        VALUES ('demo_user', 'candidate@careerlens.ai', 'Alex Mercer')
        ON CONFLICT (id) DO NOTHING;
        """)

    conn.commit()
    conn.close()


def _init_sqlite_db():
    """SQLite DDL schema setup."""
    conn = get_sqlite_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        name TEXT,
        password_hash TEXT,
        is_active BOOLEAN DEFAULT 1,
        last_login TIMESTAMP,
        reset_token TEXT,
        reset_token_expires_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resumes (
        id TEXT PRIMARY KEY,
        user_id TEXT DEFAULT 'demo_user',
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER,
        raw_text TEXT NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resume_analyses (
        id TEXT PRIMARY KEY,
        resume_id TEXT NOT NULL,
        overall_health_score INTEGER NOT NULL,
        content_quality_score INTEGER NOT NULL,
        skills_coverage_score INTEGER NOT NULL,
        experience_clarity_score INTEGER NOT NULL,
        project_strength_score INTEGER NOT NULL,
        ats_readability_score INTEGER NOT NULL,
        extracted_profile JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resume_id) REFERENCES resumes (id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_descriptions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        department TEXT,
        raw_text TEXT NOT NULL,
        requirements JSON NOT NULL,
        is_demo BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_results (
        id TEXT PRIMARY KEY,
        resume_id TEXT NOT NULL,
        job_id TEXT,
        job_title TEXT NOT NULL,
        overall_score INTEGER NOT NULL,
        skill_match INTEGER NOT NULL,
        experience_match INTEGER NOT NULL,
        education_match INTEGER NOT NULL,
        project_relevance INTEGER NOT NULL,
        semantic_fit INTEGER NOT NULL,
        matched_requirements JSON NOT NULL,
        missing_requirements JSON NOT NULL,
        skill_gaps JSON NOT NULL,
        career_preview JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resume_id) REFERENCES resumes (id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roadmap_progress (
        id TEXT PRIMARY KEY,
        resume_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'not_started',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (resume_id, job_id, skill_name),
        FOREIGN KEY (resume_id) REFERENCES resumes (id)
    );
    """)

    # 7. Security Audits Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS security_audits (
        id TEXT PRIMARY KEY,
        resume_id TEXT,
        status TEXT NOT NULL,
        action_taken TEXT NOT NULL,
        risk_score INTEGER NOT NULL,
        findings_count JSON NOT NULL,
        findings JSON NOT NULL,
        audit_data JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO users (id, email, name)
    VALUES ('demo_user', 'candidate@careerlens.ai', 'Alex Mercer');
    """)

    conn.commit()
    conn.close()


def save_resume(resume_id: str, filename: str, file_type: str, file_size: int, raw_text: str, user_id: str = "demo_user"):
    """Saves or updates uploaded resume text and metadata."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)

    try:
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()

        if is_pg:
            cursor.execute("""
            INSERT INTO resumes (id, user_id, filename, file_type, file_size, raw_text, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                filename = EXCLUDED.filename,
                file_type = EXCLUDED.file_type,
                file_size = EXCLUDED.file_size,
                raw_text = EXCLUDED.raw_text,
                uploaded_at = EXCLUDED.uploaded_at;
            """, (resume_id, user_id, filename, file_type, file_size, raw_text, now_iso))
        else:
            cursor.execute("""
            INSERT OR REPLACE INTO resumes (id, user_id, filename, file_type, file_size, raw_text, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (resume_id, user_id, filename, file_type, file_size, raw_text, now_iso))

        conn.commit()
    finally:
        conn.close()


def save_resume_analysis(analysis_id: str, resume_id: str, health_scores: Dict[str, int], extracted_profile: Dict[str, Any]):
    """Saves or updates parsed resume analysis and health scores."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)

    try:
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        
        overall = health_scores.get("overall", 82)
        content_quality = health_scores.get("content_quality", 86)
        skills_coverage = health_scores.get("skills_coverage", 91)
        experience_clarity = health_scores.get("experience_clarity", 78)
        project_strength = health_scores.get("project_strength", 84)
        ats_readability = health_scores.get("ats_readability", 80)

        if is_pg:
            cursor.execute("""
            INSERT INTO resume_analyses 
            (id, resume_id, overall_health_score, content_quality_score, skills_coverage_score, 
             experience_clarity_score, project_strength_score, ats_readability_score, extracted_profile, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                overall_health_score = EXCLUDED.overall_health_score,
                content_quality_score = EXCLUDED.content_quality_score,
                skills_coverage_score = EXCLUDED.skills_coverage_score,
                experience_clarity_score = EXCLUDED.experience_clarity_score,
                project_strength_score = EXCLUDED.project_strength_score,
                ats_readability_score = EXCLUDED.ats_readability_score,
                extracted_profile = EXCLUDED.extracted_profile,
                created_at = EXCLUDED.created_at;
            """, (
                analysis_id,
                resume_id,
                overall,
                content_quality,
                skills_coverage,
                experience_clarity,
                project_strength,
                ats_readability,
                json.dumps(extracted_profile),
                now_iso
            ))
        else:
            cursor.execute("""
            INSERT OR REPLACE INTO resume_analyses 
            (id, resume_id, overall_health_score, content_quality_score, skills_coverage_score, 
             experience_clarity_score, project_strength_score, ats_readability_score, extracted_profile, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_id,
                resume_id,
                overall,
                content_quality,
                skills_coverage,
                experience_clarity,
                project_strength,
                ats_readability,
                json.dumps(extracted_profile),
                now_iso
            ))

        conn.commit()
    finally:
        conn.close()


def get_latest_resume(user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the most recently uploaded/analyzed resume, scoped to user_id when provided."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    try:
        cursor = conn.cursor()
        where_clause = f"WHERE r.user_id = {'%s' if is_pg else '?'}" if user_id else ""
        query = f"""
        SELECT r.id as resume_id, r.user_id, r.filename, r.file_type, r.file_size, r.raw_text, r.uploaded_at,
               a.id as analysis_id, a.overall_health_score, a.content_quality_score, a.skills_coverage_score,
               a.experience_clarity_score, a.project_strength_score, a.ats_readability_score, a.extracted_profile
        FROM resumes r
        LEFT JOIN resume_analyses a ON r.id = a.resume_id
        {where_clause}
        ORDER BY r.uploaded_at DESC
        LIMIT 1
        """
        if user_id:
            cursor.execute(query, (user_id,))
        else:
            cursor.execute(query)
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        if data.get("extracted_profile"):
            if isinstance(data["extracted_profile"], str):
                data["extracted_profile"] = json.loads(data["extracted_profile"])
        return data
    finally:
        conn.close()


def get_resume_by_id(resume_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a specific resume and analysis by its resume_id, strictly enforcing user_id ownership when provided."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    try:
        cursor = conn.cursor()
        if user_id:
            query = f"""
            SELECT r.id as resume_id, r.user_id, r.filename, r.file_type, r.file_size, r.raw_text, r.uploaded_at,
                   a.id as analysis_id, a.overall_health_score, a.content_quality_score, a.skills_coverage_score,
                   a.experience_clarity_score, a.project_strength_score, a.ats_readability_score, a.extracted_profile
            FROM resumes r
            LEFT JOIN resume_analyses a ON r.id = a.resume_id
            WHERE r.id = {'%s' if is_pg else '?'} AND r.user_id = {'%s' if is_pg else '?'}
            LIMIT 1
            """
            cursor.execute(query, (resume_id, user_id))
        else:
            query = f"""
            SELECT r.id as resume_id, r.user_id, r.filename, r.file_type, r.file_size, r.raw_text, r.uploaded_at,
                   a.id as analysis_id, a.overall_health_score, a.content_quality_score, a.skills_coverage_score,
                   a.experience_clarity_score, a.project_strength_score, a.ats_readability_score, a.extracted_profile
            FROM resumes r
            LEFT JOIN resume_analyses a ON r.id = a.resume_id
            WHERE r.id = {'%s' if is_pg else '?'}
            LIMIT 1
            """
            cursor.execute(query, (resume_id,))
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        if data.get("extracted_profile"):
            if isinstance(data["extracted_profile"], str):
                data["extracted_profile"] = json.loads(data["extracted_profile"])
        return data
    finally:
        conn.close()



def save_match_result(match_id: str, resume_id: str, job_id: Optional[str], job_title: str, match_data: Dict[str, Any], user_id: Optional[str] = None):
    """Saves or updates job match evaluation and breakdown, persisting user_id ownership."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)

    try:
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()

        # Resolve user_id from parent resume if not passed explicitly
        resolved_user_id = user_id
        if not resolved_user_id and resume_id:
            check_q = f"SELECT user_id FROM resumes WHERE id = {'%s' if is_pg else '?'}"
            cursor.execute(check_q, (resume_id,))
            r_row = cursor.fetchone()
            if r_row:
                resolved_user_id = r_row["user_id"] if isinstance(r_row, dict) else r_row[0]

        overall_score = match_data.get("overall_score", 0)
        skill_match = match_data.get("skill_match", 0)
        experience_match = match_data.get("experience_match", 0)
        education_match = match_data.get("education_match", 0)
        project_relevance = match_data.get("project_relevance", 0)
        semantic_fit = match_data.get("semantic_fit", 0)
        matched_reqs = json.dumps(match_data.get("matched_requirements", []))
        missing_reqs = json.dumps(match_data.get("missing_requirements", []))
        skill_gaps = json.dumps(match_data.get("skill_gaps", []))
        career_preview = json.dumps(match_data.get("career_preview", {}))

        if is_pg:
            cursor.execute("""
            INSERT INTO match_results
            (id, resume_id, user_id, job_id, job_title, overall_score, skill_match, experience_match, 
             education_match, project_relevance, semantic_fit, matched_requirements, missing_requirements, 
             skill_gaps, career_preview, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                job_id = EXCLUDED.job_id,
                user_id = EXCLUDED.user_id,
                job_title = EXCLUDED.job_title,
                overall_score = EXCLUDED.overall_score,
                skill_match = EXCLUDED.skill_match,
                experience_match = EXCLUDED.experience_match,
                education_match = EXCLUDED.education_match,
                project_relevance = EXCLUDED.project_relevance,
                semantic_fit = EXCLUDED.semantic_fit,
                matched_requirements = EXCLUDED.matched_requirements,
                missing_requirements = EXCLUDED.missing_requirements,
                skill_gaps = EXCLUDED.skill_gaps,
                career_preview = EXCLUDED.career_preview,
                created_at = EXCLUDED.created_at;
            """, (
                match_id,
                resume_id,
                resolved_user_id,
                job_id,
                job_title,
                overall_score,
                skill_match,
                experience_match,
                education_match,
                project_relevance,
                semantic_fit,
                matched_reqs,
                missing_reqs,
                skill_gaps,
                career_preview,
                now_iso
            ))
        else:
            cursor.execute("""
            INSERT OR REPLACE INTO match_results
            (id, resume_id, user_id, job_id, job_title, overall_score, skill_match, experience_match, 
             education_match, project_relevance, semantic_fit, matched_requirements, missing_requirements, 
             skill_gaps, career_preview, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_id,
                resume_id,
                resolved_user_id,
                job_id,
                job_title,
                overall_score,
                skill_match,
                experience_match,
                education_match,
                project_relevance,
                semantic_fit,
                matched_reqs,
                missing_reqs,
                skill_gaps,
                career_preview,
                now_iso
            ))

        conn.commit()
    finally:
        conn.close()


def migrate_sqlite_to_postgres() -> Dict[str, Any]:
    """
    Utility function to migrate all records from SQLite to Neon PostgreSQL.
    """
    if not (IS_POSTGRES and PSYCOPG2_AVAILABLE):
        return {"status": "error", "message": "PostgreSQL DATABASE_URL not configured."}

    _init_postgres_db()

    sqlite_conn = get_sqlite_connection()
    pg_conn = get_postgres_connection()

    counts = {"resumes": 0, "resume_analyses": 0, "match_results": 0}

    try:
        s_cursor = sqlite_conn.cursor()
        p_cursor = pg_conn.cursor()

        # Migrate Resumes
        s_cursor.execute("SELECT * FROM resumes")
        resumes = s_cursor.fetchall()
        for r in resumes:
            p_cursor.execute("""
            INSERT INTO resumes (id, user_id, filename, file_type, file_size, raw_text, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
            """, (r["id"], r["user_id"], r["filename"], r["file_type"], r["file_size"], r["raw_text"], r["uploaded_at"]))
            counts["resumes"] += 1

        # Migrate Resume Analyses
        s_cursor.execute("SELECT * FROM resume_analyses")
        analyses = s_cursor.fetchall()
        for a in analyses:
            p_cursor.execute("""
            INSERT INTO resume_analyses 
            (id, resume_id, overall_health_score, content_quality_score, skills_coverage_score, 
             experience_clarity_score, project_strength_score, ats_readability_score, extracted_profile, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
            """, (
                a["id"], a["resume_id"], a["overall_health_score"], a["content_quality_score"],
                a["skills_coverage_score"], a["experience_clarity_score"], a["project_strength_score"],
                a["ats_readability_score"], a["extracted_profile"], a["created_at"]
            ))
            counts["resume_analyses"] += 1

        # Migrate Match Results
        s_cursor.execute("SELECT * FROM match_results")
        matches = s_cursor.fetchall()
        for m in matches:
            p_cursor.execute("""
            INSERT INTO match_results
            (id, resume_id, job_id, job_title, overall_score, skill_match, experience_match, 
             education_match, project_relevance, semantic_fit, matched_requirements, missing_requirements, 
             skill_gaps, career_preview, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
            """, (
                m["id"], m["resume_id"], m["job_id"], m["job_title"], m["overall_score"],
                m["skill_match"], m["experience_match"], m["education_match"], m["project_relevance"],
                m["semantic_fit"], m["matched_requirements"], m["missing_requirements"],
                m["skill_gaps"], m["career_preview"], m["created_at"]
            ))
            counts["match_results"] += 1

        pg_conn.commit()
        return {"status": "success", "migrated": counts}
    except Exception as e:
        pg_conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        sqlite_conn.close()
        pg_conn.close()


def save_roadmap_progress(resume_id: str, job_id: str, skill_name: str, status: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Saves or updates progress for a roadmap skill item, verifying ownership if user_id is provided."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    now_iso = datetime.utcnow().isoformat()
    record_id = f"prog_{uuid.uuid4().hex[:10]}"
    clean_skill = skill_name.strip()

    try:
        cursor = conn.cursor()
        resolved_user_id = user_id
        if not resolved_user_id and resume_id:
            check_q = f"SELECT user_id FROM resumes WHERE id = {'%s' if is_pg else '?'}"
            cursor.execute(check_q, (resume_id,))
            r_row = cursor.fetchone()
            if r_row:
                resolved_user_id = r_row["user_id"] if isinstance(r_row, dict) else r_row[0]

        if is_pg:
            cursor.execute("""
            INSERT INTO roadmap_progress (id, resume_id, user_id, job_id, skill_name, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (resume_id, job_id, skill_name)
            DO UPDATE SET status = EXCLUDED.status, user_id = EXCLUDED.user_id, updated_at = EXCLUDED.updated_at
            """, (record_id, resume_id, resolved_user_id, job_id, clean_skill, status, now_iso))
        else:
            cursor.execute("""
            INSERT INTO roadmap_progress (id, resume_id, user_id, job_id, skill_name, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (resume_id, job_id, skill_name)
            DO UPDATE SET status = excluded.status, user_id = excluded.user_id, updated_at = excluded.updated_at
            """, (record_id, resume_id, resolved_user_id, job_id, clean_skill, status, now_iso))

        conn.commit()
        return {
            "resume_id": resume_id,
            "job_id": job_id,
            "skill_name": clean_skill,
            "status": status,
            "updated_at": now_iso
        }
    finally:
        conn.close()


def get_roadmap_progress(resume_id: str, job_id: str, user_id: Optional[str] = None) -> Dict[str, str]:
    """Retrieves all tracked roadmap item statuses for a given resume and job, strictly enforcing ownership when user_id is provided."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    try:
        cursor = conn.cursor()
        # Verify ownership if user_id is provided
        if user_id:
            check_q = f"SELECT user_id FROM resumes WHERE id = {'%s' if is_pg else '?'}"
            cursor.execute(check_q, (resume_id,))
            r_row = cursor.fetchone()
            if not r_row:
                return {}
            owner = r_row["user_id"] if isinstance(r_row, dict) else r_row[0]
            if owner != user_id:
                return {}

        query = f"""
        SELECT skill_name, status FROM roadmap_progress
        WHERE resume_id = {'%s' if is_pg else '?'} AND job_id = {'%s' if is_pg else '?'}
        """
        cursor.execute(query, (resume_id, job_id))
        rows = cursor.fetchall()
        progress_map = {}
        for r in rows:
            if isinstance(r, dict) or hasattr(r, "keys"):
                progress_map[r["skill_name"].lower().strip()] = r["status"]
            else:
                progress_map[r[0].lower().strip()] = r[1]
        return progress_map
    finally:
        conn.close()


def save_security_audit(
    audit_id: str,
    resume_id: Optional[str],
    status: str,
    action_taken: str,
    risk_score: int,
    findings_count: Dict[str, Any],
    findings: List[Dict[str, Any]],
    audit_data: Dict[str, Any],
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Saves a security audit report to database with user_id association."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    now_iso = datetime.utcnow().isoformat()

    try:
        cursor = conn.cursor()
        resolved_user_id = user_id
        if not resolved_user_id and resume_id:
            check_q = f"SELECT user_id FROM resumes WHERE id = {'%s' if is_pg else '?'}"
            cursor.execute(check_q, (resume_id,))
            r_row = cursor.fetchone()
            if r_row:
                resolved_user_id = r_row["user_id"] if isinstance(r_row, dict) else r_row[0]

        fc_json = Json(findings_count) if is_pg and PSYCOPG2_AVAILABLE else json.dumps(findings_count)
        f_json = Json(findings) if is_pg and PSYCOPG2_AVAILABLE else json.dumps(findings)
        ad_json = Json(audit_data) if is_pg and PSYCOPG2_AVAILABLE else json.dumps(audit_data)

        if is_pg:
            cursor.execute("""
            INSERT INTO security_audits
            (id, resume_id, user_id, status, action_taken, risk_score, findings_count, findings, audit_data, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                resume_id = EXCLUDED.resume_id,
                user_id = EXCLUDED.user_id,
                status = EXCLUDED.status,
                action_taken = EXCLUDED.action_taken,
                risk_score = EXCLUDED.risk_score,
                findings_count = EXCLUDED.findings_count,
                findings = EXCLUDED.findings,
                audit_data = EXCLUDED.audit_data
            """, (audit_id, resume_id, resolved_user_id, status, action_taken, risk_score, fc_json, f_json, ad_json, now_iso))
        else:
            cursor.execute("""
            INSERT OR REPLACE INTO security_audits
            (id, resume_id, user_id, status, action_taken, risk_score, findings_count, findings, audit_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (audit_id, resume_id, resolved_user_id, status, action_taken, risk_score, fc_json, f_json, ad_json, now_iso))

        conn.commit()
        return audit_data
    finally:
        conn.close()


def get_security_audit_by_resume_id(resume_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the latest security audit for a given resume_id, enforcing user_id ownership when provided."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    try:
        cursor = conn.cursor()
        if user_id:
            check_q = f"SELECT user_id FROM resumes WHERE id = {'%s' if is_pg else '?'}"
            cursor.execute(check_q, (resume_id,))
            r_row = cursor.fetchone()
            if not r_row:
                return None
            owner = r_row["user_id"] if isinstance(r_row, dict) else r_row[0]
            if owner != user_id:
                return None

        query = f"""
        SELECT audit_data FROM security_audits
        WHERE resume_id = {'%s' if is_pg else '?'}
        ORDER BY created_at DESC
        LIMIT 1
        """
        cursor.execute(query, (resume_id,))
        row = cursor.fetchone()
        if not row:
            return None
        data = row["audit_data"] if (isinstance(row, dict) or hasattr(row, "keys")) else row[0]
        if isinstance(data, str):
            return json.loads(data)
        return data
    finally:
        conn.close()


def get_latest_security_audit(user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the most recent security audit, scoped to user_id when provided."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    try:
        cursor = conn.cursor()
        if user_id:
            query = f"""
            SELECT audit_data FROM security_audits
            WHERE user_id = {'%s' if is_pg else '?'}
            ORDER BY created_at DESC
            LIMIT 1
            """
            cursor.execute(query, (user_id,))
        else:
            query = """
            SELECT audit_data FROM security_audits
            ORDER BY created_at DESC
            LIMIT 1
            """
            cursor.execute(query)
        row = cursor.fetchone()
        if not row:
            return None
        data = row["audit_data"] if (isinstance(row, dict) or hasattr(row, "keys")) else row[0]
        if isinstance(data, str):
            return json.loads(data)
        return data
    finally:
        conn.close()


# ─── User Management & Authentication Persistence (Stage 3.1) ───

def create_user(
    user_id: str,
    email: str,
    name: Optional[str],
    password_hash: str,
    username: Optional[str] = None
) -> Dict[str, Any]:
    """Creates a new user account with securely hashed credentials and unique username."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    now_iso = datetime.utcnow().isoformat()
    clean_email = email.strip().lower()
    clean_username = username.strip().lower() if username else None

    try:
        cursor = conn.cursor()
        if is_pg:
            cursor.execute("""
            INSERT INTO users (id, email, username, name, password_hash, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, clean_email, clean_username, name or "Candidate", password_hash, True, now_iso))
        else:
            cursor.execute("""
            INSERT INTO users (id, email, username, name, password_hash, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, clean_email, clean_username, name or "Candidate", password_hash, 1, now_iso))

        conn.commit()
        return {
            "id": user_id,
            "email": clean_email,
            "username": clean_username,
            "name": name or "Candidate",
            "created_at": now_iso
        }
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves user profile and credentials by ID."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    try:
        cursor = conn.cursor()
        query = f"SELECT id, username, email, name, password_hash, is_active, reset_token, reset_token_expires_at, created_at FROM users WHERE id = {'%s' if is_pg else '?'}"
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves user profile by case-insensitive email."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    clean_email = email.strip().lower()
    try:
        cursor = conn.cursor()
        query = f"SELECT id, username, email, name, password_hash, is_active, reset_token, reset_token_expires_at, created_at FROM users WHERE LOWER(email) = {'%s' if is_pg else '?'}"
        cursor.execute(query, (clean_email,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Retrieves user profile by case-insensitive username."""
    if not username:
        return None
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    clean_username = username.strip().lower()
    try:
        cursor = conn.cursor()
        query = f"SELECT id, username, email, name, password_hash, is_active, reset_token, reset_token_expires_at, created_at FROM users WHERE LOWER(username) = {'%s' if is_pg else '?'}"
        cursor.execute(query, (clean_username,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    """Retrieves user profile by either email or username."""
    if not identifier:
        return None
    clean = identifier.strip().lower()
    user = get_user_by_email(clean)
    if user:
        return user
    return get_user_by_username(clean)


def set_user_reset_token(identifier: str, reset_token: str, expires_at: datetime) -> Optional[Dict[str, Any]]:
    """Sets a password reset token for a user."""
    user = get_user_by_identifier(identifier)
    if not user:
        return None
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    exp_iso = expires_at.isoformat()
    try:
        cursor = conn.cursor()
        query = f"UPDATE users SET reset_token = {'%s' if is_pg else '?'}, reset_token_expires_at = {'%s' if is_pg else '?'} WHERE id = {'%s' if is_pg else '?'}"
        cursor.execute(query, (reset_token, exp_iso, user["id"]))
        conn.commit()
        return user
    finally:
        conn.close()


def update_user_password(user_id: str, new_password_hash: str) -> bool:
    """Updates user's hashed password and invalidates active reset tokens."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    try:
        cursor = conn.cursor()
        query = f"UPDATE users SET password_hash = {'%s' if is_pg else '?'}, reset_token = NULL, reset_token_expires_at = NULL WHERE id = {'%s' if is_pg else '?'}"
        cursor.execute(query, (new_password_hash, user_id))
        conn.commit()
        return True
    finally:
        conn.close()


def update_user_last_login(user_id: str):
    """Updates user last login timestamp."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    now_iso = datetime.utcnow().isoformat()
    try:
        cursor = conn.cursor()
        query = f"UPDATE users SET last_login = {'%s' if is_pg else '?'} WHERE id = {'%s' if is_pg else '?'}"
        cursor.execute(query, (now_iso, user_id))
        conn.commit()
    finally:
        conn.close()


def add_token_to_blocklist(jti: str, user_id: str, expires_at: datetime):
    """Persists a revoked token JTI to the token blocklist."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    exp_iso = expires_at.isoformat()
    now_iso = datetime.utcnow().isoformat()
    try:
        cursor = conn.cursor()
        if is_pg:
            cursor.execute("""
            INSERT INTO token_blocklist (jti, user_id, expires_at, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (jti) DO NOTHING;
            """, (jti, user_id, exp_iso, now_iso))
        else:
            cursor.execute("""
            INSERT OR IGNORE INTO token_blocklist (jti, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?);
            """, (jti, user_id, exp_iso, now_iso))
        conn.commit()
    finally:
        conn.close()


def is_token_in_blocklist(jti: str) -> bool:
    """Checks whether a token JTI has been revoked in database storage."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    try:
        cursor = conn.cursor()
        query = f"SELECT 1 FROM token_blocklist WHERE jti = {'%s' if is_pg else '?'}"
        cursor.execute(query, (jti,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def get_resumes_by_user(user_id: str) -> List[Dict[str, Any]]:
    """Retrieves all resumes belonging to an authenticated user."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    try:
        cursor = conn.cursor()
        query = f"""
        SELECT r.id as resume_id, r.user_id, r.filename, r.file_type, r.file_size, r.uploaded_at,
               a.id as analysis_id, a.overall_health_score, a.content_quality_score, a.skills_coverage_score,
               a.experience_clarity_score, a.project_strength_score, a.ats_readability_score
        FROM resumes r
        LEFT JOIN resume_analyses a ON r.id = a.resume_id
        WHERE r.user_id = {'%s' if is_pg else '?'}
        ORDER BY r.uploaded_at DESC
        """
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─── Stage 4: Interview Preparation Persistence ───

def save_interview_session(
    session_data: Dict[str, Any],
    questions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Persists an interview session and its dynamically generated questions.
    Scoped strictly to user_id.
    """
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    ph = "%s" if is_pg else "?"

    try:
        cursor = conn.cursor()

        # 1. Insert session
        sess_query = f"""
        INSERT INTO interview_sessions (
            id, user_id, resume_id, job_id, job_title, candidate_name,
            status, total_questions, completed_questions, average_score,
            data_limitation_note, created_at, updated_at
        ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        cursor.execute(sess_query, (
            session_data["id"],
            session_data["user_id"],
            session_data.get("resume_id"),
            session_data.get("job_id"),
            session_data["job_title"],
            session_data["candidate_name"],
            session_data.get("status", "in_progress"),
            len(questions),
            session_data.get("completed_questions", 0),
            session_data.get("average_score", 0.0),
            session_data.get("data_limitation_note")
        ))

        # 2. Insert questions
        for idx, q in enumerate(questions):
            rubric_val = json.dumps(q.get("rubric", [])) if not is_pg else Json(q.get("rubric", []))
            q_query = f"""
            INSERT INTO interview_questions (
                id, session_id, category, question_text, related_requirement,
                difficulty_level, difficulty_rationale, what_interviewer_is_evaluating,
                rubric_json, source_reference, is_generic_fallback, order_index
            ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """
            cursor.execute(q_query, (
                q["id"],
                session_data["id"],
                q["category"],
                q["question_text"],
                q.get("related_requirement"),
                q["difficulty_level"],
                q.get("difficulty_rationale", ""),
                q.get("what_interviewer_is_evaluating", ""),
                rubric_val,
                q.get("source_reference", ""),
                q.get("is_generic_fallback", False),
                idx
            ))

        conn.commit()
        return session_data
    finally:
        conn.close()


def get_interview_session(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves an interview session along with its questions and completed answers.
    Enforces user_id ownership; returns None if not found or belongs to another user.
    """
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    ph = "%s" if is_pg else "?"

    try:
        cursor = conn.cursor()

        # 1. Fetch session record
        sess_query = f"""
        SELECT id, user_id, resume_id, job_id, job_title, candidate_name,
               status, total_questions, completed_questions, average_score,
               data_limitation_note, created_at, updated_at
        FROM interview_sessions
        WHERE id = {ph} AND user_id = {ph}
        """
        cursor.execute(sess_query, (session_id, user_id))
        sess_row = cursor.fetchone()
        if not sess_row:
            return None

        sess = dict(sess_row)

        # 2. Fetch questions
        q_query = f"""
        SELECT id, session_id, category, question_text, related_requirement,
               difficulty_level, difficulty_rationale, what_interviewer_is_evaluating,
               rubric_json, source_reference, is_generic_fallback, order_index
        FROM interview_questions
        WHERE session_id = {ph}
        ORDER BY order_index ASC
        """
        cursor.execute(q_query, (session_id,))
        q_rows = cursor.fetchall()

        # 3. Fetch any existing answers
        ans_query = f"""
        SELECT question_id, answer_text, word_count, overall_score,
               criterion_feedback_json, strengths_json, improvements_json,
               missing_concepts_json, suggested_structure, sample_answer,
               disclaimer, is_fallback_eval, created_at
        FROM interview_answers
        WHERE session_id = {ph} AND user_id = {ph}
        """
        cursor.execute(ans_query, (session_id, user_id))
        ans_rows = cursor.fetchall()
        answers_by_qid = {}
        for a in ans_rows:
            ad = dict(a)
            # Parse json fields if SQLite
            if isinstance(ad.get("criterion_feedback_json"), str):
                ad["criterion_feedback"] = json.loads(ad["criterion_feedback_json"])
            else:
                ad["criterion_feedback"] = ad.get("criterion_feedback_json", [])

            if isinstance(ad.get("strengths_json"), str):
                ad["strengths"] = json.loads(ad["strengths_json"])
            else:
                ad["strengths"] = ad.get("strengths_json", [])

            if isinstance(ad.get("improvements_json"), str):
                ad["improvement_areas"] = json.loads(ad["improvements_json"])
            else:
                ad["improvement_areas"] = ad.get("improvements_json", [])

            if isinstance(ad.get("missing_concepts_json"), str):
                ad["missing_concepts"] = json.loads(ad["missing_concepts_json"])
            else:
                ad["missing_concepts"] = ad.get("missing_concepts_json", [])

            answers_by_qid[ad["question_id"]] = ad

        # Merge questions with answer & rubric
        questions_list = []
        for r in q_rows:
            qd = dict(r)
            if isinstance(qd.get("rubric_json"), str):
                qd["rubric"] = json.loads(qd["rubric_json"])
            else:
                qd["rubric"] = qd.get("rubric_json", [])

            qid = qd["id"]
            if qid in answers_by_qid:
                ans_data = answers_by_qid[qid]
                qd["answer"] = ans_data["answer_text"]
                qd["evaluation"] = ans_data
            else:
                qd["answer"] = None
                qd["evaluation"] = None
            questions_list.append(qd)

        sess["questions"] = questions_list
        sess["session_id"] = sess["id"]
        if sess.get("created_at"):
            sess["created_at"] = str(sess["created_at"])
        return sess
    finally:
        conn.close()


def list_interview_sessions(user_id: str) -> List[Dict[str, Any]]:
    """Lists all interview sessions belonging to the user."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    ph = "%s" if is_pg else "?"

    try:
        cursor = conn.cursor()
        query = f"""
        SELECT id, user_id, resume_id, job_id, job_title, candidate_name,
               status, total_questions, completed_questions, average_score,
               data_limitation_note, created_at, updated_at
        FROM interview_sessions
        WHERE user_id = {ph}
        ORDER BY created_at DESC
        """
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            result.append(d)
        return result
    finally:
        conn.close()


def delete_interview_session(session_id: str, user_id: str) -> bool:
    """Deletes an interview session belonging to the user."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    ph = "%s" if is_pg else "?"

    try:
        cursor = conn.cursor()
        query = f"DELETE FROM interview_sessions WHERE id = {ph} AND user_id = {ph}"
        cursor.execute(query, (session_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def save_interview_answer(answer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persists a candidate's answer and evaluation.
    Updates the parent session's completed_questions and average_score.
    """
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    ph = "%s" if is_pg else "?"

    try:
        cursor = conn.cursor()
        session_id = answer_data["session_id"]
        question_id = answer_data["question_id"]
        user_id = answer_data["user_id"]

        crit_val = json.dumps(answer_data.get("criterion_feedback", [])) if not is_pg else Json(answer_data.get("criterion_feedback", []))
        str_val = json.dumps(answer_data.get("strengths", [])) if not is_pg else Json(answer_data.get("strengths", []))
        imp_val = json.dumps(answer_data.get("improvement_areas", [])) if not is_pg else Json(answer_data.get("improvement_areas", []))
        mis_val = json.dumps(answer_data.get("missing_concepts", [])) if not is_pg else Json(answer_data.get("missing_concepts", []))

        # Check if already answered to do clean update or insert
        check_q = f"SELECT id FROM interview_answers WHERE session_id = {ph} AND question_id = {ph}"
        cursor.execute(check_q, (session_id, question_id))
        existing = cursor.fetchone()

        if existing:
            update_q = f"""
            UPDATE interview_answers
            SET answer_text = {ph}, word_count = {ph}, overall_score = {ph},
                criterion_feedback_json = {ph}, strengths_json = {ph},
                improvements_json = {ph}, missing_concepts_json = {ph},
                suggested_structure = {ph}, sample_answer = {ph}, disclaimer = {ph},
                is_fallback_eval = {ph}, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = {ph} AND question_id = {ph}
            """
            cursor.execute(update_q, (
                answer_data["answer_text"],
                answer_data["word_count"],
                answer_data["overall_score"],
                crit_val,
                str_val,
                imp_val,
                mis_val,
                answer_data.get("suggested_structure", ""),
                answer_data.get("sample_answer", ""),
                answer_data.get("disclaimer", ""),
                answer_data.get("is_fallback_eval", False),
                session_id,
                question_id
            ))
        else:
            ans_id = answer_data.get("answer_id") or f"ans_{uuid.uuid4().hex[:8]}"
            answer_data["answer_id"] = ans_id
            insert_q = f"""
            INSERT INTO interview_answers (
                id, session_id, question_id, user_id, answer_text, word_count,
                overall_score, criterion_feedback_json, strengths_json,
                improvements_json, missing_concepts_json, suggested_structure,
                sample_answer, disclaimer, is_fallback_eval, created_at, updated_at
            ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.execute(insert_q, (
                ans_id,
                session_id,
                question_id,
                user_id,
                answer_data["answer_text"],
                answer_data["word_count"],
                answer_data["overall_score"],
                crit_val,
                str_val,
                imp_val,
                mis_val,
                answer_data.get("suggested_structure", ""),
                answer_data.get("sample_answer", ""),
                answer_data.get("disclaimer", ""),
                answer_data.get("is_fallback_eval", False)
            ))

        # Recompute session stats
        stats_q = f"""
        SELECT COUNT(*) as count, AVG(overall_score) as avg_score
        FROM interview_answers
        WHERE session_id = {ph}
        """
        cursor.execute(stats_q, (session_id,))
        stat_row = cursor.fetchone()
        comp_count = stat_row[0] if isinstance(stat_row, tuple) else stat_row["count"]
        avg_score = float(stat_row[1] or 0.0) if isinstance(stat_row, tuple) else float(stat_row["avg_score"] or 0.0)

        # Update session
        update_sess_q = f"""
        UPDATE interview_sessions
        SET completed_questions = {ph}, average_score = {ph},
            status = CASE WHEN {ph} >= total_questions THEN 'completed' ELSE 'in_progress' END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = {ph}
        """
        cursor.execute(update_sess_q, (comp_count, round(avg_score, 1), comp_count, session_id))

        conn.commit()
        return answer_data
    finally:
        conn.close()


def get_interview_answer(session_id: str, question_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an answer evaluation for a specific question."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    ph = "%s" if is_pg else "?"

    try:
        cursor = conn.cursor()
        query = f"""
        SELECT id, session_id, question_id, user_id, answer_text, word_count,
               overall_score, criterion_feedback_json, strengths_json,
               improvements_json, missing_concepts_json, suggested_structure,
               sample_answer, disclaimer, is_fallback_eval, created_at, updated_at
        FROM interview_answers
        WHERE session_id = {ph} AND question_id = {ph} AND user_id = {ph}
        """
        cursor.execute(query, (session_id, question_id, user_id))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        if isinstance(d.get("criterion_feedback_json"), str):
            d["criterion_feedback"] = json.loads(d["criterion_feedback_json"])
        else:
            d["criterion_feedback"] = d.get("criterion_feedback_json", [])

        if isinstance(d.get("strengths_json"), str):
            d["strengths"] = json.loads(d["strengths_json"])
        else:
            d["strengths"] = d.get("strengths_json", [])

        if isinstance(d.get("improvements_json"), str):
            d["improvement_areas"] = json.loads(d["improvements_json"])
        else:
            d["improvement_areas"] = d.get("improvements_json", [])

        if isinstance(d.get("missing_concepts_json"), str):
            d["missing_concepts"] = json.loads(d["missing_concepts_json"])
        else:
            d["missing_concepts"] = d.get("missing_concepts_json", [])

        if d.get("created_at"):
            d["created_at"] = str(d["created_at"])
        return d
    finally:
        conn.close()


# ─── Stage 5: Fairness Audit Persistence ───

def save_fairness_audit(audit_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persists a completed fairness audit report."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    ph = "%s" if is_pg else "?"

    audit_id = audit_data.get("audit_id") or f"audit_{uuid.uuid4().hex[:12]}"
    user_id = audit_data["user_id"]
    policy_version = audit_data.get("policy_version", "v1.2.0")
    total_tests = audit_data.get("total_tests", 0)
    passed_tests = audit_data.get("passed_tests", 0)
    discrepancy_count = audit_data.get("discrepancy_count", 0)
    discrepancy_rate = audit_data.get("discrepancy_rate", 0.0)
    max_absolute_delta = audit_data.get("max_absolute_delta", 0)
    avg_absolute_delta = audit_data.get("avg_absolute_delta", 0.0)

    metrics_json = json.dumps(audit_data.get("metrics", []))
    findings_json = json.dumps(audit_data.get("findings", []))
    test_results_json = json.dumps(audit_data.get("test_results", []))
    unassessed_dimensions_json = json.dumps(audit_data.get("unassessed_dimensions", []))
    scoring_policy_summary_json = json.dumps(audit_data.get("scoring_policy_summary", {}))

    try:
        cursor = conn.cursor()
        query = f"""
        INSERT INTO fairness_audits (
            id, user_id, policy_version, total_tests, passed_tests,
            discrepancy_count, discrepancy_rate, max_absolute_delta, avg_absolute_delta,
            metrics_json, findings_json, test_results_json,
            unassessed_dimensions_json, scoring_policy_summary_json, created_at
        ) VALUES (
            {ph}, {ph}, {ph}, {ph}, {ph},
            {ph}, {ph}, {ph}, {ph},
            {ph}, {ph}, {ph},
            {ph}, {ph}, CURRENT_TIMESTAMP
        )
        """
        cursor.execute(query, (
            audit_id, user_id, policy_version, total_tests, passed_tests,
            discrepancy_count, discrepancy_rate, max_absolute_delta, avg_absolute_delta,
            metrics_json, findings_json, test_results_json,
            unassessed_dimensions_json, scoring_policy_summary_json
        ))
        conn.commit()
        audit_data["audit_id"] = audit_id
        return audit_data
    finally:
        conn.close()


def get_fairness_audit(audit_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single fairness audit report owned by user_id."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    ph = "%s" if is_pg else "?"

    try:
        cursor = conn.cursor()
        query = f"""
        SELECT id, user_id, policy_version, total_tests, passed_tests,
               discrepancy_count, discrepancy_rate, max_absolute_delta, avg_absolute_delta,
               metrics_json, findings_json, test_results_json,
               unassessed_dimensions_json, scoring_policy_summary_json, created_at
        FROM fairness_audits
        WHERE id = {ph} AND user_id = {ph}
        """
        cursor.execute(query, (audit_id, user_id))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        for field in ["metrics", "findings", "test_results", "unassessed_dimensions", "scoring_policy_summary"]:
            json_key = f"{field}_json"
            if isinstance(d.get(json_key), str):
                d[field] = json.loads(d[json_key])
            else:
                d[field] = d.get(json_key, [] if field != "scoring_policy_summary" else {})

        d["audit_id"] = d.pop("id")
        d["timestamp"] = str(d.get("created_at", ""))
        return d
    finally:
        conn.close()


def list_fairness_audits(user_id: str) -> List[Dict[str, Any]]:
    """Lists summary of all fairness audits performed by user_id."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    ph = "%s" if is_pg else "?"

    try:
        cursor = conn.cursor()
        query = f"""
        SELECT id, user_id, policy_version, total_tests, passed_tests,
               discrepancy_rate, max_absolute_delta, avg_absolute_delta, created_at
        FROM fairness_audits
        WHERE user_id = {ph}
        ORDER BY created_at DESC
        """
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            results.append(d)
        return results
    finally:
        conn.close()


def delete_fairness_audit(audit_id: str, user_id: str) -> bool:
    """Deletes a fairness audit owned by user_id."""
    conn = get_db_connection()
    is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
    ph = "%s" if is_pg else "?"

    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM fairness_audits WHERE id = {ph} AND user_id = {ph}", (audit_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()



