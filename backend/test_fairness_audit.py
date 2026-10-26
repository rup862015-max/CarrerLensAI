"""
Fairness Audit & Scoring Consistency Automated Test Suite for CareerLens AI (Stage 5)
Tests:
- Demographic proxy counterfactual invariance
- Layout and section order invariance
- Contact info and location invariance
- Formatting and bullet styling invariance
- Skill alias normalization consistency
- Boundary conditions and null-safety
- Scoring isolation from security audits and interview sessions
- Fairness metrics calculation
- Authenticated user data isolation and persistence
"""

import unittest
import os
import sys
import uuid
import json

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from main import app
from services.fairness_service import fairness_service, TOLERANCES, SCORING_POLICY_VERSION
from services.matching_service import matching_service
from services.auth_service import create_access_token, rate_limiter
from database import (
    save_fairness_audit,
    get_fairness_audit,
    list_fairness_audits,
    delete_fairness_audit
)


class TestFairnessAuditSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rate_limiter._records.clear()
        cls.client = TestClient(app)

        # Register test users via API
        cls.uid_a = uuid.uuid4().hex[:8]
        cls.user_a_email = f"fairness_user_a_{cls.uid_a}@example.com"
        res_a = cls.client.post("/api/auth/register", json={
            "email": cls.user_a_email,
            "password": "Password123!",
            "name": "User Alpha"
        })
        data_a = res_a.json()
        cls.user_a_id = data_a["user"]["id"]
        cls.token_a = data_a["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        cls.uid_b = uuid.uuid4().hex[:8]
        cls.user_b_email = f"fairness_user_b_{cls.uid_b}@example.com"
        res_b = cls.client.post("/api/auth/register", json={
            "email": cls.user_b_email,
            "password": "Password123!",
            "name": "User Beta"
        })
        data_b = res_b.json()
        cls.user_b_id = data_b["user"]["id"]
        cls.token_b = data_b["access_token"]
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    def test_01_demographic_proxy_invariance(self):
        """Demographic proxy variants (different names) on identical qualifications must have invariant deterministic subscores."""
        report = fairness_service.run_audit_suite(user_id=self.user_a_id)
        demo_tests = [t for t in report["test_results"] if t.get("category") == "demographic_proxy_invariance"]

        self.assertGreaterEqual(len(demo_tests), 6, "Expected at least 6 demographic proxy tests")
        for t in demo_tests:
            # Deterministic components (skill, experience, education, projects) must have zero delta
            for comp in ["skill_match", "experience_match", "education_match", "project_relevance"]:
                self.assertEqual(
                    t["component_deltas"][comp]["delta"],
                    0,
                    f"Component {comp} varied on demographic proxy test {t['test_id']}: {t['component_deltas'][comp]}"
                )
            # Overall score must remain within tolerance of 1 point
            self.assertLessEqual(
                abs(t["score_delta"]),
                TOLERANCES["overall_score_counterfactual"],
                f"Overall score delta {t['score_delta']} exceeded tolerance on {t['test_id']}"
            )

    def test_02_section_order_invariance(self):
        """Reordering resume sections must produce invariant deterministic scores."""
        report = fairness_service.run_audit_suite(user_id=self.user_a_id)
        order_tests = [t for t in report["test_results"] if t.get("category") == "section_order_invariance"]

        self.assertGreaterEqual(len(order_tests), 3, "Expected at least 3 section order tests")
        for t in order_tests:
            self.assertEqual(t["score_delta"], 0, f"Section ordering caused delta on {t['test_id']}")
            for comp in ["skill_match", "experience_match", "education_match", "project_relevance"]:
                self.assertEqual(t["component_deltas"][comp]["delta"], 0)

    def test_03_contact_location_invariance(self):
        """Altering phone, email, or geographic location must not alter deterministic matching subscores."""
        report = fairness_service.run_audit_suite(user_id=self.user_a_id)
        contact_tests = [t for t in report["test_results"] if t.get("category") == "contact_location_invariance"]

        self.assertGreaterEqual(len(contact_tests), 3, "Expected at least 3 contact/location tests")
        for t in contact_tests:
            for comp in ["skill_match", "experience_match", "education_match", "project_relevance"]:
                self.assertEqual(
                    t["component_deltas"][comp]["delta"],
                    0,
                    f"Component {comp} changed on contact/location test {t['test_id']}"
                )

    def test_04_formatting_bullet_style_invariance(self):
        """Changing bullet markers (asterisk vs dash vs whitespace) must not change match scores."""
        report = fairness_service.run_audit_suite(user_id=self.user_a_id)
        fmt_tests = [t for t in report["test_results"] if t.get("category") == "layout_formatting_invariance"]

        self.assertGreaterEqual(len(fmt_tests), 3, "Expected at least 3 formatting tests")
        for t in fmt_tests:
            self.assertEqual(t["score_delta"], 0, f"Bullet style change caused delta on {t['test_id']}")

    def test_05_skill_alias_normalization(self):
        """Equivalent skill aliases (e.g. Postgres vs PostgreSQL, k8s vs Kubernetes) must match identically."""
        report = fairness_service.run_audit_suite(user_id=self.user_a_id)
        alias_tests = [t for t in report["test_results"] if t.get("category") == "alias_normalization_consistency"]

        self.assertGreaterEqual(len(alias_tests), 4, "Expected at least 4 alias normalization tests")
        for t in alias_tests:
            self.assertEqual(
                t["component_deltas"]["skill_match"]["delta"],
                0,
                f"Skill match subscore varied on alias test {t['test_id']}: {t['component_deltas']['skill_match']}"
            )
            self.assertEqual(
                t["component_deltas"]["project_relevance"]["delta"],
                0,
                f"Project relevance subscore varied on alias test {t['test_id']}"
            )
            self.assertLessEqual(
                abs(t["score_delta"]),
                2,
                f"Overall score varied beyond semantic tolerance on alias test {t['test_id']}"
            )
            self.assertEqual(t["status"], "passed")

    def test_06_boundary_and_null_safety(self):
        """Scoring pipeline must handle empty profiles, null years_of_experience, and extreme boundary values safely."""
        job = {
            "id": "test-job-null",
            "title": "Backend Dev",
            "requirements": [{"name": "Python", "importance": "critical"}]
        }

        # Null experience profile
        null_exp_profile = {
            "name": "Null Exp",
            "skills": ["Python"],
            "years_of_experience": None,
            "experience": [],
            "education": [],
            "projects": []
        }
        res_null_exp = matching_service.match_resume_to_job(null_exp_profile, "Python", job)
        self.assertIsInstance(res_null_exp["overall_score"], int)
        self.assertGreater(res_null_exp["overall_score"], 0)

        # Empty skills profile
        empty_profile = {
            "name": "Empty Candidate",
            "skills": None,
            "years_of_experience": 0,
            "experience": None,
            "education": None,
            "projects": None
        }
        res_empty = matching_service.match_resume_to_job(empty_profile, "", job)
        self.assertEqual(res_empty["skill_match"], 0)
        self.assertIsInstance(res_empty["overall_score"], int)

    def test_07_legitimate_experience_difference(self):
        """Experience difference genuinely relevant to senior role must legitimately alter experience subscore."""
        report = fairness_service.run_audit_suite(user_id=self.user_a_id)
        test = next((t for t in report["test_results"] if t["test_id"] == "BOUND-EXP-03"), None)

        self.assertIsNotNone(test, "BOUND-EXP-03 test not found")
        # 1 year exp should have a lower experience subscore than 10 years exp for a Senior role
        self.assertLess(
            test["variant_score"],
            test["baseline_score"],
            "1y experience should score lower than 10y experience for a Senior role"
        )
        self.assertGreater(test["score_delta"], 0)
        self.assertIn("legitimate", test["description"].lower())

    def test_08_score_isolation_guarantee(self):
        """Security audit scan and interview practice evaluations must never alter candidate match scores."""
        report = fairness_service.run_audit_suite(user_id=self.user_a_id)
        iso_tests = [t for t in report["test_results"] if t.get("category") == "score_isolation_guarantee"]

        self.assertGreaterEqual(len(iso_tests), 1)
        for t in iso_tests:
            self.assertEqual(t["score_delta"], 0, f"Score isolation failed on {t['test_id']}")
            self.assertEqual(t["variant_score"], t["baseline_score"])

    def test_09_metrics_validity(self):
        """Audit report must compute explicit mathematical metrics with non-empty definitions."""
        report = fairness_service.run_audit_suite(user_id=self.user_a_id)
        metrics = report["metrics"]
        self.assertIsInstance(metrics, list)
        self.assertGreaterEqual(len(metrics), 4)

        metric_names = [m["name"] for m in metrics]
        self.assertTrue(any("Delta_max" in n for n in metric_names))
        self.assertTrue(any("Delta_avg" in n for n in metric_names))
        self.assertTrue(any("Demographic Proxy" in n for n in metric_names))
        self.assertTrue(any("Deterministic Component" in n for n in metric_names))
        self.assertTrue(any("Discrepancy Rate" in n for n in metric_names))

        for m in metrics:
            self.assertTrue(len(m["formula"]) > 0, f"Metric {m['name']} missing formula")
            self.assertTrue(len(m["description"]) > 0, f"Metric {m['name']} missing description")
            self.assertTrue(len(m["limitations"]) > 0, f"Metric {m['name']} missing limitations")
            self.assertGreater(m["sample_size"], 0, f"Metric {m['name']} has zero sample size")

    def test_10_documented_findings_and_unassessed_dimensions(self):
        """Audit report must catalog confirmed defects, remediations, and unassessed ethical dimensions."""
        report = fairness_service.run_audit_suite(user_id=self.user_a_id)
        findings = report["findings"]
        unassessed = report["unassessed_dimensions"]

        finding_ids = [f["id"] for f in findings]
        self.assertIn("FAIR-001", finding_ids)
        self.assertIn("FAIR-002", finding_ids)
        self.assertIn("FAIR-003", finding_ids)
        self.assertIn("FAIR-004", finding_ids)

        # Verify FAIR-001 is remediated
        f1 = next(f for f in findings if f["id"] == "FAIR-001")
        self.assertIn(f1["status"], ["remediated", "resolved"])

        # Verify unassessed dimensions
        self.assertGreaterEqual(len(unassessed), 2)
        unassessed_titles = [u["dimension"] for u in unassessed]
        self.assertTrue(any("Demographic Parity" in d for d in unassessed_titles))

    def test_11_audit_api_endpoints_and_user_isolation(self):
        """Fairness audit endpoints must enforce authentication and strict user data isolation."""
        # Unauthenticated request rejected
        unauth_res = self.client.post("/api/fairness/audit")
        self.assertEqual(unauth_res.status_code, 401)

        # User A executes audit
        res_a = self.client.post("/api/fairness/audit", headers=self.headers_a)
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.json()
        audit_id_a = data_a["audit_id"]
        self.assertEqual(data_a["user_id"], self.user_a_id)

        # User A can retrieve audit
        get_res_a = self.client.get(f"/api/fairness/audit/{audit_id_a}", headers=self.headers_a)
        self.assertEqual(get_res_a.status_code, 200)
        self.assertEqual(get_res_a.json()["audit_id"], audit_id_a)

        # User B CANNOT retrieve User A's audit (data isolation: 404)
        get_res_b = self.client.get(f"/api/fairness/audit/{audit_id_a}", headers=self.headers_b)
        self.assertEqual(get_res_b.status_code, 404)

        # User B CANNOT delete User A's audit
        del_res_b = self.client.delete(f"/api/fairness/audit/{audit_id_a}", headers=self.headers_b)
        self.assertEqual(del_res_b.status_code, 404)

        # User A CAN delete their own audit
        del_res_a = self.client.delete(f"/api/fairness/audit/{audit_id_a}", headers=self.headers_a)
        self.assertEqual(del_res_a.status_code, 200)

        # After deletion, User A receives 404
        get_deleted = self.client.get(f"/api/fairness/audit/{audit_id_a}", headers=self.headers_a)
        self.assertEqual(get_deleted.status_code, 404)

    def test_12_policy_endpoint(self):
        """Policy endpoint returns authoritative scoring version, weights, and tolerances."""
        res = self.client.get("/api/fairness/policy", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["policy_version"], SCORING_POLICY_VERSION)
        self.assertIn("weights", data)
        self.assertIn("tolerances", data)
        self.assertIn("components", data)
        self.assertIn("irrelevant_attributes", data)


if __name__ == "__main__":
    unittest.main()
