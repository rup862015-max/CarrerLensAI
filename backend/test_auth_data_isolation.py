"""
Stage 3.1: Adversarial & Authentication Data Isolation Test Suite
Validates:
  1. User A can upload and retrieve their own resume.
  2. User B cannot retrieve User A's resume by guessing or copying its ID (404 Not Found).
  3. User B cannot retrieve User A's match, simulation, roadmap, progress, or security audit.
  4. User B cannot modify User A's roadmap progress or records.
  5. Changing client-supplied user ID cannot spoof authenticated identity.
  6. Unauthenticated requests are rejected across all protected endpoints (401 Unauthorized).
  7. Invalid, expired, and malformed tokens and credentials are rejected.
  8. Logout invalidates tokens via persistent revocation blocklist.
  9. Legacy demo_user records remain protected and cannot be accessed by other users.
  10. Full authenticated single-user lifecycle workflow works seamlessly.
"""

import os
import sys
import uuid
import unittest
from datetime import timedelta

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from database import init_db, get_db_connection, get_resume_by_id
from services.auth_service import create_access_token

RESUME_TEXT_USER_A = """Alice Smith
San Francisco, CA | alice.smith@example.com | (555) 111-2222 | linkedin.com/in/alicesmith

PROFESSIONAL SUMMARY
Senior Cloud & Backend Engineer with 5+ years of experience designing scalable microservices in Python, FastAPI, and PostgreSQL.

TECHNICAL SKILLS
Languages: Python, SQL, JavaScript
Frameworks: FastAPI, React, Docker
Databases: PostgreSQL, Redis

WORK EXPERIENCE
Senior Backend Engineer | CloudScale Inc. (2021 - 2024)
• Built REST microservices handling 100k daily requests.
• Optimized PostgreSQL query performance by 40%.

EDUCATION
B.S. in Computer Science | UC Berkeley (2017 - 2021)
"""

RESUME_TEXT_USER_B = """Bob Jones
New York, NY | bob.jones@example.com | (555) 333-4444

PROFESSIONAL SUMMARY
Frontend Specialist with 3+ years experience building user interfaces with React and TypeScript.

TECHNICAL SKILLS
Languages: JavaScript, TypeScript, HTML, CSS
Frameworks: React, Next.js

WORK EXPERIENCE
Frontend Developer | WebCorp (2022 - 2024)
• Designed responsive dashboards and client applications in React.

EDUCATION
B.A. in Graphic Design | NYU (2018 - 2022)
"""


class TestAuthDataIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

        # Generate unique user emails for this test run
        cls.uid_a = uuid.uuid4().hex[:8]
        cls.uid_b = uuid.uuid4().hex[:8]
        cls.email_a = f"alice_{cls.uid_a}@securitytest.com"
        cls.email_b = f"bob_{cls.uid_b}@securitytest.com"
        cls.password_a = "StrongPasswordA123!"
        cls.password_b = "StrongPasswordB456!"

        # Register User A
        res_a = cls.client.post("/api/auth/register", json={
            "email": cls.email_a,
            "password": cls.password_a,
            "name": "Alice Smith"
        })
        assert res_a.status_code == 200, f"Register A failed: {res_a.text}"
        data_a = res_a.json()
        cls.token_a = data_a["access_token"]
        cls.user_a_id = data_a["user"]["id"]

        # Register User B
        res_b = cls.client.post("/api/auth/register", json={
            "email": cls.email_b,
            "password": cls.password_b,
            "name": "Bob Jones"
        })
        assert res_b.status_code == 200, f"Register B failed: {res_b.text}"
        data_b = res_b.json()
        cls.token_b = data_b["access_token"]
        cls.user_b_id = data_b["user"]["id"]

    def auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    # ─────────────────────────────────────────────────────────────────
    # 1. User A can upload and retrieve their own resume
    # ─────────────────────────────────────────────────────────────────
    def test_01_user_a_can_upload_and_retrieve_own_resume(self):
        headers_a = self.auth_headers(self.token_a)
        res = self.client.post("/api/resume/analyze", json={
            "resume_text": RESUME_TEXT_USER_A,
            "filename": "Alice_Smith_CV.txt"
        }, headers=headers_a)
        self.assertEqual(res.status_code, 200)
        upload_data = res.json()
        resume_id = upload_data["resume_id"]
        TestAuthDataIsolation.resume_a_id = resume_id

        # Retrieve by ID
        res_get = self.client.get(f"/api/resume/{resume_id}", headers=headers_a)
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["resume_id"], resume_id)
        self.assertEqual(res_get.json()["filename"], "Alice_Smith_CV.txt")

        # Retrieve latest
        res_latest = self.client.get("/api/resume/latest", headers=headers_a)
        self.assertEqual(res_latest.status_code, 200)
        self.assertEqual(res_latest.json()["resume_id"], resume_id)

    # ─────────────────────────────────────────────────────────────────
    # 2. User B cannot retrieve User A's resume by ID
    # ─────────────────────────────────────────────────────────────────
    def test_02_user_b_cannot_retrieve_user_a_resume(self):
        headers_b = self.auth_headers(self.token_b)
        resume_a_id = getattr(self, "resume_a_id", None)
        self.assertIsNotNone(resume_a_id, "User A resume must exist")

        # User B attempts to access User A's resume by exact ID
        res = self.client.get(f"/api/resume/{resume_a_id}", headers=headers_b)
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    # ─────────────────────────────────────────────────────────────────
    # 3. User B cannot access User A's match, simulation, roadmap, or audit
    # ─────────────────────────────────────────────────────────────────
    def test_03_cross_user_isolation_on_matches_simulations_roadmaps_audits(self):
        headers_a = self.auth_headers(self.token_a)
        headers_b = self.auth_headers(self.token_b)
        resume_a_id = self.resume_a_id

        # User A creates a job match
        res_match_a = self.client.post("/api/match", json={
            "resume_id": resume_a_id,
            "job_id": "job-backend-001"
        }, headers=headers_a)
        self.assertEqual(res_match_a.status_code, 200)

        # User B attempts to run job match referencing User A's resume_id
        res_match_b = self.client.post("/api/match", json={
            "resume_id": resume_a_id,
            "job_id": "job-backend-001"
        }, headers=headers_b)
        self.assertIn(res_match_b.status_code, [400, 404])

        # User B attempts career simulation with User A's resume_id
        res_sim_b = self.client.post("/api/career/simulate", json={
            "resume_id": resume_a_id,
            "job_id": "job-backend-001",
            "hypothetical_skills": ["Kubernetes"]
        }, headers=headers_b)
        self.assertIn(res_sim_b.status_code, [400, 404])

        # User B attempts career paths with User A's resume_id
        res_paths_b = self.client.get(f"/api/career/paths?resume_id={resume_a_id}", headers=headers_b)
        self.assertIn(res_paths_b.status_code, [400, 404])

        # User B attempts learning roadmap with User A's resume_id
        res_map_b = self.client.get(
            f"/api/career/roadmap?resume_id={resume_a_id}&job_id=job-backend-001",
            headers=headers_b
        )
        self.assertEqual(res_map_b.status_code, 404)

        # User B attempts security audit retrieval for User A's resume_id
        res_audit_b = self.client.get(f"/api/security/audit/{resume_a_id}", headers=headers_b)
        self.assertEqual(res_audit_b.status_code, 404)

        # User B attempts to run security audit with User A's resume_id
        res_audit_post_b = self.client.post("/api/security/audit", json={
            "resume_id": resume_a_id
        }, headers=headers_b)
        self.assertEqual(res_audit_post_b.status_code, 404)

    # ─────────────────────────────────────────────────────────────────
    # 4. User B cannot modify User A's roadmap progress
    # ─────────────────────────────────────────────────────────────────
    def test_04_user_b_cannot_modify_user_a_roadmap_progress(self):
        headers_a = self.auth_headers(self.token_a)
        headers_b = self.auth_headers(self.token_b)
        resume_a_id = self.resume_a_id

        # User A sets progress to in_progress
        res_prog_a = self.client.post("/api/career/roadmap/progress", json={
            "resume_id": resume_a_id,
            "job_id": "job-backend-001",
            "skill_name": "Docker",
            "status": "in_progress"
        }, headers=headers_a)
        self.assertEqual(res_prog_a.status_code, 200)

        # User B tries to overwrite User A's progress to completed
        res_prog_b = self.client.post("/api/career/roadmap/progress", json={
            "resume_id": resume_a_id,
            "job_id": "job-backend-001",
            "skill_name": "Docker",
            "status": "completed"
        }, headers=headers_b)
        self.assertEqual(res_prog_b.status_code, 404)

        # Verify that User A's status is STILL 'in_progress'
        res_map_a = self.client.get(
            f"/api/career/roadmap?resume_id={resume_a_id}&job_id=job-backend-001",
            headers=headers_a
        )
        self.assertEqual(res_map_a.status_code, 200)
        steps = res_map_a.json()["steps"]
        docker_step = next((s for s in steps if s.get("skill", "").lower() == "docker"), None)
        if docker_step:
            self.assertEqual(docker_step["status"], "in_progress")

    # ─────────────────────────────────────────────────────────────────
    # 5. Client-supplied user_id cannot spoof identity
    # ─────────────────────────────────────────────────────────────────
    def test_05_client_supplied_user_id_cannot_change_authenticated_identity(self):
        headers_b = self.auth_headers(self.token_b)
        # User B tries to inject user_id="user_a" into json payload
        res = self.client.post("/api/resume/analyze", json={
            "resume_text": RESUME_TEXT_USER_B,
            "filename": "Bob_Injected.txt",
            "user_id": self.user_a_id  # Spoof attempt
        }, headers=headers_b)
        self.assertEqual(res.status_code, 200)
        bob_resume_id = res.json()["resume_id"]

        # Directly inspect database: ensure resume is owned by User B, NOT User A
        record = get_resume_by_id(bob_resume_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["user_id"], self.user_b_id)
        self.assertNotEqual(record["user_id"], self.user_a_id)

    # ─────────────────────────────────────────────────────────────────
    # 6. Unauthenticated requests are rejected across all protected routes
    # ─────────────────────────────────────────────────────────────────
    def test_06_unauthenticated_requests_cannot_access_protected_resources(self):
        protected_endpoints = [
            ("POST", "/api/resume/analyze", {"resume_text": "Sample text exceeding twenty chars"}),
            ("GET", "/api/resume/latest", None),
            ("GET", f"/api/resume/{self.resume_a_id}", None),
            ("GET", "/api/resumes", None),
            ("POST", "/api/match", {"resume_id": self.resume_a_id, "job_id": "job-backend-001"}),
            ("POST", "/api/career/simulate", {"resume_id": self.resume_a_id, "job_id": "job-backend-001", "hypothetical_skills": ["Go"]}),
            ("GET", f"/api/career/paths?resume_id={self.resume_a_id}", None),
            ("GET", f"/api/career/roadmap?resume_id={self.resume_a_id}&job_id=job-backend-001", None),
            ("POST", "/api/career/roadmap/progress", {"resume_id": self.resume_a_id, "job_id": "job-backend-001", "skill_name": "Go", "status": "completed"}),
            ("POST", "/api/security/audit", {"resume_id": self.resume_a_id}),
            ("GET", "/api/security/audit/latest", None),
            ("GET", f"/api/security/audit/{self.resume_a_id}", None),
            ("GET", "/api/auth/me", None),
        ]

        for method, path, payload in protected_endpoints:
            with self.subTest(method=method, path=path):
                if method == "POST":
                    res = self.client.post(path, json=payload)
                else:
                    res = self.client.get(path)
                self.assertEqual(res.status_code, 401, f"{method} {path} should return 401 Unauthorized")

    # ─────────────────────────────────────────────────────────────────
    # 7. Invalid, expired, and malformed credentials are rejected
    # ─────────────────────────────────────────────────────────────────
    def test_07_invalid_expired_and_malformed_credentials_rejected(self):
        # 1. Malformed token format
        res_malformed = self.client.get("/api/auth/me", headers={"Authorization": "NotBearer some_junk_token"})
        self.assertEqual(res_malformed.status_code, 401)

        # 2. Tampered / invalid JWT signature
        fake_token = self.token_a[:-8] + "abcdefgh"
        res_fake = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
        self.assertEqual(res_fake.status_code, 401)

        # 3. Expired token
        expired_token, _, _ = create_access_token(
            user_id=self.user_a_id,
            email=self.email_a,
            expires_delta=timedelta(seconds=-10)
        )
        res_expired = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(res_expired.status_code, 401)
        self.assertIn("expired", res_expired.json()["detail"].lower())

        # 4. Wrong password login
        res_wrong_pw = self.client.post("/api/auth/login", json={
            "email": self.email_a,
            "password": "IncorrectPassword999!"
        })
        self.assertEqual(res_wrong_pw.status_code, 401)
        self.assertEqual(res_wrong_pw.json()["detail"], "Invalid username and email id")

        # 5. Non-existent email login
        res_no_user = self.client.post("/api/auth/login", json={
            "email": "does_not_exist_98765@careerlens.ai",
            "password": "AnyPassword123!"
        })
        self.assertEqual(res_no_user.status_code, 401)
        self.assertEqual(res_no_user.json()["detail"], "Invalid username and email id")

        # 6. Registration with weak password (< 8 chars)
        res_weak = self.client.post("/api/auth/register", json={
            "email": f"weak_{uuid.uuid4().hex[:6]}@test.com",
            "password": "short"
        })
        self.assertIn(res_weak.status_code, [400, 422])

        # 7. Registration with invalid email format
        res_bad_email = self.client.post("/api/auth/register", json={
            "email": "not-an-email-address",
            "password": "ValidPassword123!"
        })
        self.assertEqual(res_bad_email.status_code, 400)

    # ─────────────────────────────────────────────────────────────────
    # 8. Logout and session invalidation
    # ─────────────────────────────────────────────────────────────────
    def test_08_logout_and_session_invalidation(self):
        # Register a disposable user for logout test
        disp_email = f"disposable_{uuid.uuid4().hex[:8]}@test.com"
        res_reg = self.client.post("/api/auth/register", json={
            "email": disp_email,
            "password": "Password123!",
            "name": "Disposable User"
        })
        self.assertEqual(res_reg.status_code, 200)
        disp_token = res_reg.json()["access_token"]
        disp_headers = self.auth_headers(disp_token)

        # Confirm token works
        res_me = self.client.get("/api/auth/me", headers=disp_headers)
        self.assertEqual(res_me.status_code, 200)

        # Logout
        res_logout = self.client.post("/api/auth/logout", headers=disp_headers)
        self.assertEqual(res_logout.status_code, 200)

        # Attempt to use the revoked token -> should be rejected with 401
        res_after = self.client.get("/api/auth/me", headers=disp_headers)
        self.assertEqual(res_after.status_code, 401)
        self.assertIn("revoked", res_after.json()["detail"].lower())

    # ─────────────────────────────────────────────────────────────────
    # 9. Legacy records remain protected after migration
    # ─────────────────────────────────────────────────────────────────
    def test_09_legacy_demo_records_remain_protected(self):
        headers_b = self.auth_headers(self.token_b)

        # User B cannot access demo_user's latest resume as their own
        res_latest_b = self.client.get("/api/resume/latest", headers=headers_b)
        # If Bob has uploaded resumes, latest will be Bob's; if not, 404.
        # In either case, it MUST NOT be demo_user's resume.
        if res_latest_b.status_code == 200:
            self.assertEqual(res_latest_b.json().get("filename"), "Bob_Injected.txt")
            self.assertNotEqual(res_latest_b.json().get("filename"), "Alex_Mercer.txt")

        # User B cannot guess demo_user resume IDs (e.g. res_22f09c1d)
        res_demo_probe = self.client.get("/api/resume/res_22f09c1d", headers=headers_b)
        self.assertEqual(res_demo_probe.status_code, 404)

    # ─────────────────────────────────────────────────────────────────
    # 10. Existing single-user workflows still work under authenticated model
    # ─────────────────────────────────────────────────────────────────
    def test_10_authenticated_single_user_workflow_lifecycle(self):
        user_email = f"workflow_{uuid.uuid4().hex[:8]}@test.com"
        pwd = "FullWorkflowPassword123!"

        # Step 1: Register
        res_reg = self.client.post("/api/auth/register", json={
            "email": user_email,
            "password": pwd,
            "name": "Workflow Candidate"
        })
        self.assertEqual(res_reg.status_code, 200)
        token = res_reg.json()["access_token"]
        headers = self.auth_headers(token)

        # Step 2: Login
        res_login = self.client.post("/api/auth/login", json={
            "email": user_email,
            "password": pwd
        })
        self.assertEqual(res_login.status_code, 200)

        # Step 3: Upload / Analyze Resume
        res_upload = self.client.post("/api/resume/analyze", json={
            "resume_text": RESUME_TEXT_USER_A,
            "filename": "Workflow_Candidate.txt"
        }, headers=headers)
        self.assertEqual(res_upload.status_code, 200)
        resume_id = res_upload.json()["resume_id"]

        # Step 4: Verify latest resume
        res_latest = self.client.get("/api/resume/latest", headers=headers)
        self.assertEqual(res_latest.status_code, 200)
        self.assertEqual(res_latest.json()["resume_id"], resume_id)

        # Step 5: Execute Match
        res_match = self.client.post("/api/match", json={
            "resume_id": resume_id,
            "job_id": "job-backend-001"
        }, headers=headers)
        self.assertEqual(res_match.status_code, 200)
        self.assertIn("overall_score", res_match.json())

        # Step 6: Career Simulator
        res_sim = self.client.post("/api/career/simulate", json={
            "resume_id": resume_id,
            "job_id": "job-backend-001",
            "hypothetical_skills": ["Docker", "Kubernetes"]
        }, headers=headers)
        self.assertEqual(res_sim.status_code, 200)

        # Step 7: Learning Roadmap
        res_map = self.client.get(
            f"/api/career/roadmap?resume_id={resume_id}&job_id=job-backend-001",
            headers=headers
        )
        self.assertEqual(res_map.status_code, 200)

        # Step 8: Update Progress
        res_prog = self.client.post("/api/career/roadmap/progress", json={
            "resume_id": resume_id,
            "job_id": "job-backend-001",
            "skill_name": "Docker",
            "status": "completed"
        }, headers=headers)
        self.assertEqual(res_prog.status_code, 200)

        # Step 9: Security Audit
        res_audit = self.client.post("/api/security/audit", json={
            "resume_id": resume_id
        }, headers=headers)
        self.assertEqual(res_audit.status_code, 200)

        # Step 10: Logout
        res_logout = self.client.post("/api/auth/logout", headers=headers)
        self.assertEqual(res_logout.status_code, 200)


if __name__ == "__main__":
    unittest.main()
