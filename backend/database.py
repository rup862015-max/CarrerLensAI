"""
SQLite Database Layer for CareerLens AI Phase 1
Stores uploaded resumes, parsed candidate profiles, job descriptions, and match results.
"""

import sqlite3
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "careerlens.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the database schema if not already present."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Resumes Table
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

    # 3. Resume Analyses Table
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

    # 4. Job Descriptions Table
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

    # 5. Match Results Table
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

    # Insert default demo user
    cursor.execute("""
    INSERT OR IGNORE INTO users (id, email, name)
    VALUES ('demo_user', 'candidate@careerlens.ai', 'Alex Mercer');
    """)

    conn.commit()
    conn.close()


def save_resume(resume_id: str, filename: str, file_type: str, file_size: int, raw_text: str, user_id: str = "demo_user"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO resumes (id, user_id, filename, file_type, file_size, raw_text, uploaded_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (resume_id, user_id, filename, file_type, file_size, raw_text, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def save_resume_analysis(analysis_id: str, resume_id: str, health_scores: Dict[str, int], extracted_profile: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO resume_analyses 
    (id, resume_id, overall_health_score, content_quality_score, skills_coverage_score, 
     experience_clarity_score, project_strength_score, ats_readability_score, extracted_profile, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        analysis_id,
        resume_id,
        health_scores.get("overall", 82),
        health_scores.get("content_quality", 86),
        health_scores.get("skills_coverage", 91),
        health_scores.get("experience_clarity", 78),
        health_scores.get("project_strength", 84),
        health_scores.get("ats_readability", 80),
        json.dumps(extracted_profile),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()


def get_latest_resume() -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT r.id as resume_id, r.filename, r.file_type, r.file_size, r.raw_text, r.uploaded_at,
           a.id as analysis_id, a.overall_health_score, a.content_quality_score, a.skills_coverage_score,
           a.experience_clarity_score, a.project_strength_score, a.ats_readability_score, a.extracted_profile
    FROM resumes r
    LEFT JOIN resume_analyses a ON r.id = a.resume_id
    ORDER BY r.uploaded_at DESC
    LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None

    data = dict(row)
    if data.get("extracted_profile"):
        data["extracted_profile"] = json.loads(data["extracted_profile"])
    return data


def save_match_result(match_id: str, resume_id: str, job_id: Optional[str], job_title: str, match_data: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO match_results
    (id, resume_id, job_id, job_title, overall_score, skill_match, experience_match, 
     education_match, project_relevance, semantic_fit, matched_requirements, missing_requirements, 
     skill_gaps, career_preview, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        match_id,
        resume_id,
        job_id,
        job_title,
        match_data.get("overall_score", 0),
        match_data.get("skill_match", 0),
        match_data.get("experience_match", 0),
        match_data.get("education_match", 0),
        match_data.get("project_relevance", 0),
        match_data.get("semantic_fit", 0),
        json.dumps(match_data.get("matched_requirements", [])),
        json.dumps(match_data.get("missing_requirements", [])),
        json.dumps(match_data.get("skill_gaps", [])),
        json.dumps(match_data.get("career_preview", {})),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()
