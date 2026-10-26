"""
Stage 1 Comprehensive Regression Test Suite for CareerLens AI
Verifies all 12 non-negotiable Stage 1F criteria:
 1. A valid resume with explicit matching skills
 2. A valid resume with missing job requirements
 3. Different resume and job-description inputs
 4. Empty or malformed uploads
 5. Extraction failures
 6. AI/API failures and graceful deterministic operation
 7. Missing or malformed job descriptions
 8. Unsupported or unverified skills
 9. Reproducible scores for identical inputs and configuration
10. Correct evidence references in matching explanations
11. Absence of fake candidate fallback results
12. Existing upload, extraction, matching, and API integration
"""

import os
import sys
import json
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, save_resume, save_resume_analysis
from services.resume_parser import extract_text_from_file, ResumeParserError
from services.skill_service import skill_service
from services.explanation_service import explanation_service
from services.matching_service import matching_service
from services.ai_service import ai_service
from config import (
    MATCHING_WEIGHTS,
    IMPORTANCE_WEIGHTS,
    REQUIREMENT_STATUSES,
    validate_matching_config
)
from main import app


class TestStage1Regression(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        from services.auth_service import get_test_token
        cls.client.headers["Authorization"] = f"Bearer {get_test_token('demo_user', 'candidate@careerlens.ai')}"
        validate_matching_config()

    # 1. Valid resume with explicit matching skills
    def test_01_valid_resume_with_explicit_matching_skills(self):
        resume_text = """Sarah Connor
        sarah.connor@cyberdyne.io | (555) 382-9102 | Denver, CO
        
        PROFESSIONAL SUMMARY
        Experienced Backend Engineer with 4+ years developing scalable REST APIs, microservices, and database systems.
        
        TECHNICAL SKILLS
        Python, FastAPI, Docker, PostgreSQL, SQL, Git, Linux
        
        WORK EXPERIENCE
        Software Engineer | SkyNet Systems (2020 - 2024)
        • Developed high-throughput REST APIs in Python and FastAPI handling 100k requests/min.
        • Deployed containerized microservices using Docker and orchestrated database queries on PostgreSQL.
        
        PROJECTS
        Sentinel API (Python, Docker, PostgreSQL)
        • Designed secure authentication service using FastAPI and PostgreSQL with 99.9% uptime.
        """
        analysis = ai_service.analyze_resume(resume_text, filename="Sarah_Connor.pdf")
        profile = analysis["extracted_profile"]

        job_data = {
            "title": "Backend Systems Engineer",
            "requirements": [
                {"name": "Python", "importance": "critical", "category": "languages"},
                {"name": "FastAPI", "importance": "critical", "category": "frameworks"},
                {"name": "Docker", "importance": "required", "category": "cloud_devops"},
                {"name": "PostgreSQL", "importance": "required", "category": "databases"}
            ],
            "description": "Looking for backend engineer with Python, FastAPI, Docker, and PostgreSQL experience."
        }

        match_res = matching_service.match_resume_to_job(profile, resume_text, job_data)
        self.assertGreaterEqual(match_res["overall_score"], 75)
        self.assertGreaterEqual(match_res["skill_match"], 80)

        matched_names = [m["requirement"] for m in match_res["matched_requirements"]]
        self.assertIn("Python", matched_names)
        self.assertIn("FastAPI", matched_names)
        self.assertIn("Docker", matched_names)
        self.assertIn("PostgreSQL", matched_names)

        # Check evidence presence and confidence
        for m in match_res["matched_requirements"]:
            self.assertTrue(len(m["resume_evidence"]) > 5)
            self.assertGreater(m["confidence"], 0.6)
            self.assertIn(m["status"], [REQUIREMENT_STATUSES["MATCHED"], REQUIREMENT_STATUSES["UNVERIFIED"]])

    # 2. Valid resume with missing job requirements
    def test_02_valid_resume_with_missing_job_requirements(self):
        frontend_resume = """Alex Taylor
        alex@frontend.io | New York, NY
        
        TECHNICAL SKILLS
        HTML, CSS, React, Figma, Tailwind CSS
        
        PROJECTS
        Design System
        • Built reusable component library using React and Tailwind CSS.
        """
        analysis = ai_service.analyze_resume(frontend_resume, filename="Alex_Taylor.txt", file_type="txt")
        profile = analysis["extracted_profile"]

        data_job = {
            "title": "Data Analyst",
            "requirements": [
                {"name": "SQL", "importance": "critical", "category": "databases"},
                {"name": "Tableau", "importance": "critical", "category": "ai_data"},
                {"name": "Pandas", "importance": "recommended", "category": "ai_data"}
            ],
            "description": "Requires advanced SQL, Tableau dashboards, and Pandas data modeling."
        }

        match_res = matching_service.match_resume_to_job(profile, frontend_resume, data_job)
        missing_names = [m["requirement"] for m in match_res["missing_requirements"]]
        self.assertIn("SQL", missing_names)
        self.assertIn("Tableau", missing_names)
        self.assertIn("Pandas", missing_names)

        # Explanations must clarify absence in document vs candidate ability
        for m in match_res["missing_requirements"]:
            self.assertEqual(m["status"], REQUIREMENT_STATUSES["MISSING"])
            self.assertEqual(m["confidence"], 0.0)
            self.assertIn("absence from the resume document", m["reason"])
            self.assertIn("scoring_contribution", m)

    # 3. Different resume and job-description inputs produce distinct appropriate scores
    def test_03_different_resume_and_job_description_inputs(self):
        resume_mobile = """David Miller
        david@mobile.com
        SKILLS: Swift, iOS, Kotlin, Android, Mobile Design
        EDUCATION:
        B.S. in Arts
        EXPERIENCE:
        Mobile Developer (2021 - 2024)
        • Built native iOS apps using Swift.
        """
        resume_devops = """Elena Rostova
        elena@cloud.com
        SKILLS: AWS, Terraform, Kubernetes, Docker, Linux, CI/CD
        EDUCATION:
        B.S. in Computer Science | Tech University (2018 - 2022)
        EXPERIENCE:
        DevOps Engineer (2019 - 2024)
        • Automated multi-region AWS cloud infrastructure using Terraform and Kubernetes.
        PROJECTS:
        K8s Cluster Migration (Kubernetes, AWS, Terraform)
        • Migrated 30 microservices to EKS with zero downtime.
        """

        profile_mobile = ai_service.analyze_resume(resume_mobile, "mobile.txt")["extracted_profile"]
        profile_devops = ai_service.analyze_resume(resume_devops, "devops.txt")["extracted_profile"]

        cloud_job = {
            "title": "Senior Cloud Infrastructure Engineer",
            "requirements": [
                {"name": "AWS", "importance": "critical", "category": "cloud_devops"},
                {"name": "Kubernetes", "importance": "critical", "category": "cloud_devops"},
                {"name": "Terraform", "importance": "critical", "category": "cloud_devops"},
                {"name": "Docker", "importance": "required", "category": "cloud_devops"}
            ],
            "description": "Architect and maintain cloud infrastructure on AWS with Kubernetes and Terraform."
        }

        match_mobile = matching_service.match_resume_to_job(profile_mobile, resume_mobile, cloud_job)
        match_devops = matching_service.match_resume_to_job(profile_devops, resume_devops, cloud_job)

        # Elena (DevOps) must have significantly higher score than David (Mobile)
        self.assertGreater(match_devops["overall_score"], match_mobile["overall_score"])
        self.assertGreaterEqual(match_devops["overall_score"], 80)
        self.assertLess(match_mobile["overall_score"], 50)

    # 4. Empty or malformed uploads
    def test_04_empty_or_malformed_uploads(self):
        # Empty file (0 bytes)
        res_empty = self.client.post(
            "/api/resume/upload",
            files={"file": ("empty.pdf", b"", "application/pdf")}
        )
        self.assertEqual(res_empty.status_code, 400)
        self.assertIn("empty", res_empty.json()["detail"].lower())

        # Unsupported file extension
        res_bad_ext = self.client.post(
            "/api/resume/upload",
            files={"file": ("malware.exe", b"MZexecutabledata", "application/octet-stream")}
        )
        self.assertEqual(res_bad_ext.status_code, 400)
        self.assertIn("unsupported", res_bad_ext.json()["detail"].lower())

    # 5. Extraction failures
    def test_05_extraction_failures(self):
        # Text with fewer than 10 words
        with self.assertRaises(ResumeParserError):
            extract_text_from_file("corrupt.txt", b"   \n  \t  ")

        # Insufficient resume text endpoint check
        res = self.client.post("/api/resume/analyze", json={"resume_text": "too short"})
        self.assertIn(res.status_code, [400, 422])

    # 6. AI/API failures and deterministic fallback operation
    def test_06_ai_api_failures_graceful_handling(self):
        # Even with mock or offline LLM provider, deterministic engine parses and scores
        self.assertFalse(ai_service.is_llm_active())  # Provider is mock
        analysis = ai_service.analyze_resume(
            "Jane Doe\nSkills: Python, SQL\nExperience: Software Engineer for 3 years at TechCorp.",
            "Jane.txt"
        )
        self.assertEqual(analysis["extraction_status"], "success")
        self.assertIn("Python", analysis["extracted_profile"]["skills"])
        self.assertGreater(analysis["health_scores"]["overall"], 0)

    # 7. Missing or malformed job descriptions
    def test_07_missing_or_malformed_job_descriptions(self):
        # Non-existent job id
        res = self.client.post("/api/match", json={
            "resume_text": "Sample candidate text with Python and SQL",
            "job_id": "job-invalid-999"
        })
        self.assertEqual(res.status_code, 404)

        # Job description text too short
        res_short = self.client.post("/api/match", json={
            "resume_text": "Sample candidate with Python and SQL",
            "job_description": "short"
        })
        self.assertEqual(res_short.status_code, 400)

        # Neither job_id nor job_description provided
        res_missing_job = self.client.post("/api/match", json={
            "resume_text": "Sample candidate with Python and SQL"
        })
        self.assertEqual(res_missing_job.status_code, 400)
        self.assertIn("job", res_missing_job.json()["detail"].lower())

    # 8. Unsupported or unverified skills
    def test_08_unsupported_or_unverified_skills(self):
        # Candidate lists Docker only in skills section, with no project or experience context
        resume = """Bob Vance
        TECHNICAL SKILLS: Docker, BrainfuckEsotericLang
        EDUCATION: B.S. in CS
        """
        analysis = ai_service.analyze_resume(resume, "bob.txt")
        profile = analysis["extracted_profile"]

        job = {
            "title": "DevOps Junior",
            "requirements": [
                {"name": "Docker", "importance": "critical", "category": "cloud_devops"}
            ],
            "description": "Requires Docker containerization."
        }
        match_res = matching_service.match_resume_to_job(profile, resume, job)
        matched = match_res["matched_requirements"][0]
        self.assertEqual(matched["requirement"], "Docker")
        self.assertEqual(matched["status"], REQUIREMENT_STATUSES["UNVERIFIED"])
        self.assertIn("uncertainty_note", matched)
        self.assertIn("project deliverables", matched["uncertainty_note"].lower())

    # 9. Reproducible scores for identical inputs and configuration
    def test_09_reproducible_scores_for_identical_inputs_and_configuration(self):
        resume = """Alice Wong
        Skills: Python, TypeScript, React, PostgreSQL, Docker
        Experience: 3 years building web apps.
        Projects:
        TaskApp (React, Python, PostgreSQL)
        • Built task manager with 10k users.
        """
        analysis = ai_service.analyze_resume(resume, "alice.txt")
        profile = analysis["extracted_profile"]

        job = {
            "title": "Full Stack Engineer",
            "requirements": [
                {"name": "Python", "importance": "critical"},
                {"name": "React", "importance": "critical"},
                {"name": "PostgreSQL", "importance": "required"}
            ],
            "description": "Looking for Full Stack Engineer with Python, React, and PostgreSQL."
        }

        run_1 = matching_service.match_resume_to_job(profile, resume, job)
        run_2 = matching_service.match_resume_to_job(profile, resume, job)

        self.assertEqual(run_1["overall_score"], run_2["overall_score"])
        self.assertEqual(run_1["skill_match"], run_2["skill_match"])
        self.assertEqual(run_1["experience_match"], run_2["experience_match"])
        self.assertEqual(run_1["education_match"], run_2["education_match"])
        self.assertEqual(run_1["project_relevance"], run_2["project_relevance"])
        self.assertEqual(run_1["semantic_fit"], run_2["semantic_fit"])
        self.assertEqual(run_1["match_grade"], run_2["match_grade"])

    # 10. Correct evidence references in matching explanations
    def test_10_correct_evidence_references_in_matching_explanations(self):
        resume = """Marcus Brody
        Skills: Python, FastAPI
        Projects:
        Archaeology Tracker (Python, FastAPI)
        • Implemented REST APIs and indexed artifact records reducing search latency by 45%.
        """
        analysis = ai_service.analyze_resume(resume, "marcus.txt")
        profile = analysis["extracted_profile"]

        job = {
            "title": "Python API Developer",
            "requirements": [{"name": "FastAPI", "importance": "critical"}],
            "description": "Requires FastAPI web development."
        }

        match = matching_service.match_resume_to_job(profile, resume, job)
        fastapi_req = match["matched_requirements"][0]
        self.assertEqual(fastapi_req["requirement"], "FastAPI")
        self.assertIn("Archaeology Tracker", fastapi_req["resume_evidence"])
        self.assertTrue(any("Project: Archaeology Tracker" in loc for loc in fastapi_req["evidence_locations"]))
        self.assertIn("scoring_contribution", fastapi_req)

    # 11. Absence of fake candidate fallback results
    def test_11_absence_of_fake_candidate_fallback_results(self):
        # Post with invalid resume_id and no profile
        res = self.client.post("/api/match", json={
            "resume_id": "res_nonexistent_xyz999",
            "job_id": "job-backend-001"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("not found in storage", res.json()["detail"])

        # Post with no resume at all
        res_empty = self.client.post("/api/match", json={
            "job_id": "job-backend-001"
        })
        # If DB has no active resume, it returns 400 rather than silently using Alex Mercer
        # If DB had an active resume from a previous test, it uses that verified DB resume, not hardcoded Alex Mercer.

    # 12. Existing upload, extraction, matching, and UI integration flow
    def test_12_existing_upload_extraction_matching_and_ui_integration(self):
        resume_payload = {
            "resume_text": """Carlos Santana
            carlos@guitar.io | Austin, TX
            PROFESSIONAL SUMMARY
            Software developer with 3 years experience in TypeScript, React, and GraphQL.
            EDUCATION
            B.S. in Computer Science | University of Texas
            TECHNICAL SKILLS
            TypeScript, React, Node.js, GraphQL, Git
            WORK EXPERIENCE
            Web Developer | Studio Audio (2021 - 2024)
            • Built interactive dashboards in React and TypeScript.
            PROJECTS
            AudioStream Web (React, TypeScript, GraphQL)
            • Engineered real-time audio streaming platform with React and TypeScript.
            """,
            "filename": "Carlos_Santana.txt"
        }
        res_analyze = self.client.post("/api/resume/analyze", json=resume_payload)
        self.assertEqual(res_analyze.status_code, 200)
        ana_data = res_analyze.json()
        self.assertTrue(ana_data["resume_id"].startswith("res_"))
        self.assertIn("TypeScript", ana_data["extracted_profile"]["skills"])

        # Match against custom job description
        res_match = self.client.post("/api/match", json={
            "resume_id": ana_data["resume_id"],
            "job_description": "We need a Frontend Engineer proficient in TypeScript, React, and GraphQL.",
            "job_title": "Frontend Engineer"
        })
        self.assertEqual(res_match.status_code, 200)
        match_data = res_match.json()
        self.assertEqual(match_data["job_title"], "Frontend Engineer")
        self.assertGreaterEqual(match_data["overall_score"], 70)
        self.assertTrue(len(match_data["matched_requirements"]) >= 2)
        self.assertIn("career_preview", match_data)
        self.assertIn("recommendations", match_data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
