"""
Database Migration & Ownership Formalization Module for CareerLens AI
Safely upgrades both Neon PostgreSQL and SQLite databases to support:
  - Strong salted user credentials (password_hash)
  - Token blocklist for immediate session revocation
  - Resource ownership columns (user_id) across:
    - match_results
    - roadmap_progress
    - security_audits
  - Preserves existing user records (including legacy demo_user) without reassignment.
  - Backfills ownership from resumes.user_id to child records.
"""

import os
import sys
import sqlite3
from typing import Dict, Any, Optional

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    get_db_connection,
    get_sqlite_connection,
    get_postgres_connection,
    IS_POSTGRES,
    PSYCOPG2_AVAILABLE,
    SQLITE_DB_PATH
)
from services.auth_service import hash_password


def run_postgres_migrations(conn) -> Dict[str, Any]:
    """Applies schema migrations to Neon PostgreSQL."""
    stats = {
        "engine": "neon_postgres",
        "columns_added": [],
        "tables_created": [],
        "backfilled": {}
    }
    with conn.cursor() as cur:
        # 1. Update users table columns
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(255);")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255);")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP WITH TIME ZONE;")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique ON users(LOWER(username)) WHERE username IS NOT NULL;")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(LOWER(email));")
        stats["columns_added"].extend(["users.username", "users.password_hash", "users.is_active", "users.last_login", "users.reset_token", "users.reset_token_expires_at"])

        # 2. Update child resource tables with user_id
        cur.execute("ALTER TABLE match_results ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);")
        cur.execute("ALTER TABLE roadmap_progress ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);")
        cur.execute("ALTER TABLE security_audits ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);")
        stats["columns_added"].extend(["match_results.user_id", "roadmap_progress.user_id", "security_audits.user_id"])

        # 3. Create token_blocklist table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS token_blocklist (
            jti VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        stats["tables_created"].append("token_blocklist")

        # 4. Create index on resource user_id columns for fast scoped queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_match_results_user_id ON match_results(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_roadmap_progress_user_id ON roadmap_progress(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_security_audits_user_id ON security_audits(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_token_blocklist_jti ON token_blocklist(jti);")

        # 5. Backfill user_id on child records from parent resumes table
        cur.execute("""
        UPDATE match_results m
        SET user_id = r.user_id
        FROM resumes r
        WHERE m.resume_id = r.id AND (m.user_id IS NULL OR m.user_id = '');
        """)
        stats["backfilled"]["match_results"] = cur.rowcount

        cur.execute("""
        UPDATE roadmap_progress rp
        SET user_id = r.user_id
        FROM resumes r
        WHERE rp.resume_id = r.id AND (rp.user_id IS NULL OR rp.user_id = '');
        """)
        stats["backfilled"]["roadmap_progress"] = cur.rowcount

        cur.execute("""
        UPDATE security_audits sa
        SET user_id = r.user_id
        FROM resumes r
        WHERE sa.resume_id = r.id AND (sa.user_id IS NULL OR sa.user_id = '');
        """)
        # 6. Ensure legacy demo_user has valid hashed credentials for controlled dev testing
        demo_pwd_hash = hash_password("DemoUser123!")
        cur.execute("""
        UPDATE users
        SET password_hash = %s, is_active = TRUE
        WHERE id = 'demo_user' AND (password_hash IS NULL OR password_hash = '');
        """, (demo_pwd_hash,))

        # 7. Create Stage 4 Interview Preparation Tables
        cur.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            resume_id VARCHAR(255),
            job_id VARCHAR(255),
            job_title VARCHAR(255) NOT NULL,
            candidate_name VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'in_progress',
            total_questions INT DEFAULT 0,
            completed_questions INT DEFAULT 0,
            average_score FLOAT DEFAULT 0.0,
            data_limitation_note TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS interview_questions (
            id VARCHAR(255) PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
            category VARCHAR(50) NOT NULL,
            question_text TEXT NOT NULL,
            related_requirement VARCHAR(255),
            difficulty_level VARCHAR(50) NOT NULL,
            difficulty_rationale TEXT,
            what_interviewer_is_evaluating TEXT,
            rubric_json JSONB NOT NULL,
            source_reference TEXT,
            is_generic_fallback BOOLEAN DEFAULT FALSE,
            order_index INT DEFAULT 0
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS interview_answers (
            id VARCHAR(255) PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
            question_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            answer_text TEXT NOT NULL,
            word_count INT NOT NULL,
            overall_score INT NOT NULL,
            criterion_feedback_json JSONB NOT NULL,
            strengths_json JSONB NOT NULL,
            improvements_json JSONB NOT NULL,
            missing_concepts_json JSONB NOT NULL,
            suggested_structure TEXT,
            sample_answer TEXT,
            disclaimer TEXT,
            is_fallback_eval BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (session_id, question_id)
        );
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_id ON interview_sessions(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_interview_questions_session_id ON interview_questions(session_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_interview_answers_session_id ON interview_answers(session_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_interview_answers_user_id ON interview_answers(user_id);")
        stats["tables_created"].extend(["interview_sessions", "interview_questions", "interview_answers"])

        # 8. Create fairness_audits table (Stage 5)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS fairness_audits (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            policy_version VARCHAR(50) NOT NULL,
            total_tests INT NOT NULL,
            passed_tests INT NOT NULL,
            discrepancy_count INT NOT NULL,
            discrepancy_rate REAL NOT NULL,
            max_absolute_delta INT NOT NULL,
            avg_absolute_delta REAL NOT NULL,
            metrics_json JSONB NOT NULL,
            findings_json JSONB NOT NULL,
            test_results_json JSONB NOT NULL,
            unassessed_dimensions_json JSONB NOT NULL,
            scoring_policy_summary_json JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fairness_audits_user_id ON fairness_audits(user_id);")
        stats["tables_created"].append("fairness_audits")

    conn.commit()
    return stats


def run_sqlite_migrations(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Applies schema migrations to SQLite."""
    stats = {
        "engine": "sqlite",
        "columns_added": [],
        "tables_created": [],
        "backfilled": {}
    }
    cur = conn.cursor()

    # Helper to check if column exists
    def column_exists(table: str, col: str) -> bool:
        cur.execute(f"PRAGMA table_info({table});")
        cols = [r[1] if isinstance(r, tuple) else r["name"] for r in cur.fetchall()]
        return col in cols

    # 1. Update users table columns
    if not column_exists("users", "username"):
        cur.execute("ALTER TABLE users ADD COLUMN username TEXT;")
        stats["columns_added"].append("users.username")

    if not column_exists("users", "password_hash"):
        cur.execute("ALTER TABLE users ADD COLUMN password_hash TEXT;")
        stats["columns_added"].append("users.password_hash")

    if not column_exists("users", "is_active"):
        cur.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1;")
        stats["columns_added"].append("users.is_active")

    if not column_exists("users", "last_login"):
        cur.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP;")
        stats["columns_added"].append("users.last_login")

    if not column_exists("users", "reset_token"):
        cur.execute("ALTER TABLE users ADD COLUMN reset_token TEXT;")
        stats["columns_added"].append("users.reset_token")

    if not column_exists("users", "reset_token_expires_at"):
        cur.execute("ALTER TABLE users ADD COLUMN reset_token_expires_at TIMESTAMP;")
        stats["columns_added"].append("users.reset_token_expires_at")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique ON users(LOWER(username)) WHERE username IS NOT NULL;")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(LOWER(email));")

    # 2. Update child resource tables
    if not column_exists("match_results", "user_id"):
        cur.execute("ALTER TABLE match_results ADD COLUMN user_id TEXT;")
        stats["columns_added"].append("match_results.user_id")

    if not column_exists("roadmap_progress", "user_id"):
        cur.execute("ALTER TABLE roadmap_progress ADD COLUMN user_id TEXT;")
        stats["columns_added"].append("roadmap_progress.user_id")

    if not column_exists("security_audits", "user_id"):
        cur.execute("ALTER TABLE security_audits ADD COLUMN user_id TEXT;")
        stats["columns_added"].append("security_audits.user_id")

    # 3. Create token_blocklist table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS token_blocklist (
        jti TEXT PRIMARY KEY,
        user_id TEXT,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    stats["tables_created"].append("token_blocklist")

    # 4. Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_match_results_user_id ON match_results(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_roadmap_progress_user_id ON roadmap_progress(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_security_audits_user_id ON security_audits(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_token_blocklist_jti ON token_blocklist(jti);")

    # 5. Backfill user_id in child tables
    cur.execute("""
    UPDATE match_results
    SET user_id = (SELECT user_id FROM resumes WHERE resumes.id = match_results.resume_id)
    WHERE user_id IS NULL OR user_id = '';
    """)
    stats["backfilled"]["match_results"] = cur.rowcount

    cur.execute("""
    UPDATE roadmap_progress
    SET user_id = (SELECT user_id FROM resumes WHERE resumes.id = roadmap_progress.resume_id)
    WHERE user_id IS NULL OR user_id = '';
    """)
    stats["backfilled"]["roadmap_progress"] = cur.rowcount

    cur.execute("""
    UPDATE security_audits
    SET user_id = (SELECT user_id FROM resumes WHERE resumes.id = security_audits.resume_id)
    WHERE user_id IS NULL OR user_id = '';
    """)
    stats["backfilled"]["security_audits"] = cur.rowcount

    # 6. Ensure demo_user has hashed password
    demo_pwd_hash = hash_password("DemoUser123!")
    cur.execute("""
    UPDATE users
    SET password_hash = ?, is_active = 1
    WHERE id = 'demo_user' AND (password_hash IS NULL OR password_hash = '');
    """, (demo_pwd_hash,))

    # 7. Create Stage 4 Interview Preparation Tables (SQLite)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS interview_sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        resume_id TEXT,
        job_id TEXT,
        job_title TEXT NOT NULL,
        candidate_name TEXT NOT NULL,
        status TEXT DEFAULT 'in_progress',
        total_questions INTEGER DEFAULT 0,
        completed_questions INTEGER DEFAULT 0,
        average_score REAL DEFAULT 0.0,
        data_limitation_note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS interview_questions (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
        category TEXT NOT NULL,
        question_text TEXT NOT NULL,
        related_requirement TEXT,
        difficulty_level TEXT NOT NULL,
        difficulty_rationale TEXT,
        what_interviewer_is_evaluating TEXT,
        rubric_json TEXT NOT NULL,
        source_reference TEXT,
        is_generic_fallback BOOLEAN DEFAULT 0,
        order_index INTEGER DEFAULT 0
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS interview_answers (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
        question_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        answer_text TEXT NOT NULL,
        word_count INTEGER NOT NULL,
        overall_score INTEGER NOT NULL,
        criterion_feedback_json TEXT NOT NULL,
        strengths_json TEXT NOT NULL,
        improvements_json TEXT NOT NULL,
        missing_concepts_json TEXT NOT NULL,
        suggested_structure TEXT,
        sample_answer TEXT,
        disclaimer TEXT,
        is_fallback_eval BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (session_id, question_id)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_id ON interview_sessions(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_interview_questions_session_id ON interview_questions(session_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_interview_answers_session_id ON interview_answers(session_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_interview_answers_user_id ON interview_answers(user_id);")
    stats["tables_created"].extend(["interview_sessions", "interview_questions", "interview_answers"])

    # 8. Create fairness_audits table (Stage 5)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fairness_audits (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        policy_version TEXT NOT NULL,
        total_tests INTEGER NOT NULL,
        passed_tests INTEGER NOT NULL,
        discrepancy_count INTEGER NOT NULL,
        discrepancy_rate REAL NOT NULL,
        max_absolute_delta INTEGER NOT NULL,
        avg_absolute_delta REAL NOT NULL,
        metrics_json TEXT NOT NULL,
        findings_json TEXT NOT NULL,
        test_results_json TEXT NOT NULL,
        unassessed_dimensions_json TEXT NOT NULL,
        scoring_policy_summary_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fairness_audits_user_id ON fairness_audits(user_id);")
    stats["tables_created"].append("fairness_audits")

    conn.commit()
    return stats


def apply_migrations(conn=None) -> Dict[str, Any]:
    """
    Entry point to run all necessary schema migrations on the active database.
    """
    close_when_done = False
    if conn is None:
        conn = get_db_connection()
        close_when_done = True

    try:
        is_pg = hasattr(conn, "cursor_factory") or not isinstance(conn, sqlite3.Connection)
        if is_pg:
            res = run_postgres_migrations(conn)
        else:
            res = run_sqlite_migrations(conn)
        return {"status": "success", "details": res}
    finally:
        if close_when_done:
            conn.close()


if __name__ == "__main__":
    print("[Migrations] Running Stage 3.1 Authentication & Data Isolation Migrations...")
    result = apply_migrations()
    print(f"[Migrations] Result: {result}")
