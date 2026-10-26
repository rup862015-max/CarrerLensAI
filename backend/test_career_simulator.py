"""
Automated Test Suite for CareerLens AI Phase 2, Stage 2A: Career Simulator
Uses unittest.TestCase for standalone runner compatibility.
Covers all 11 required scenarios:
1. Baseline simulation score matches regular matching engine
2. Adding relevant hypothetical skill changes only appropriate requirements
3. Irrelevant skills do not produce artificial improvements
4. Unknown skills are handled safely
5. Original resume data is unchanged after simulation
6. Missing resume and job return proper errors
7. Identical inputs produce reproducible results
8. Evidence labels distinguish hypothetical and verified skills
9. Scoring configuration is reused
10. Career paths use actual available taxonomy/profile data (no fabricated salaries)
11. API failures and edge cases handled properly
"""

import os
import sys
import copy
import unittest
from fastapi.testclient import TestClient

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from config import (
    MATCHING_WEIGHTS,
    HYPOTHETICAL_SKILL_CREDIT,
    REQUIREMENT_STATUSES
)
from services.matching_service import matching_service
from services.career_service import career_service
from services.skill_service import skill_service


# ─── Test Fixtures ───
SAMPLE_RESUME_PROFILE = {
    "candidate_name": "Jordan Lee",
    "email": "jordan.lee@example.com",
    "education": ["B.S. in Computer Science, State University"],
    "experience": [
        "Software Engineer at Acme Corp (2022-2024). Developed backend microservices using Python and FastAPI."
    ],
    "years_of_experience": 2.5,
    "skills": ["Python", "FastAPI", "SQL", "Git"],
    "detailed_skills": [
        {"name": "Python", "category": "Languages", "skill_type": "explicit"},
        {"name": "FastAPI", "category": "Frameworks", "skill_type": "explicit"},
        {"name": "SQL", "category": "Databases", "skill_type": "explicit"},
        {"name": "Git", "category": "DevOps", "skill_type": "explicit"}
    ],
    "projects": [
        {
            "title": "API Gateway",
            "technologies": ["Python", "FastAPI", "PostgreSQL"],
            "evidence": ["Built REST microservices routing 10k requests/min."]
        }
    ]
}

SAMPLE_RESUME_TEXT = """Jordan Lee
jordan.lee@example.com | San Francisco, CA

SUMMARY
Backend engineer with 2+ years experience building APIs and database systems using Python, FastAPI, and SQL.

EDUCATION
B.S. in Computer Science, State University (2022)

EXPERIENCE
Software Engineer | Acme Corp (2022 - 2024)
- Built backend services in Python and FastAPI.
- Wrote complex SQL queries and maintained database models.

PROJECTS
API Gateway
- Built REST microservices routing 10k requests/min using Python and FastAPI.

SKILLS
Python, FastAPI, SQL, Git
"""

SAMPLE_JOB_DATA = {
    "id": "test_job_fullstack",
    "title": "Cloud Backend Engineer",
    "description": "Seeking a Backend Engineer proficient in Python, SQL, Docker, and Kubernetes for distributed cloud systems.",
    "requirements": [
        {"name": "Python", "importance": "critical", "category": "Languages"},
        {"name": "SQL", "importance": "required", "category": "Databases"},
        {"name": "Docker", "importance": "critical", "category": "DevOps"},
        {"name": "Kubernetes", "importance": "recommended", "category": "DevOps"}
    ]
}


class TestCareerSimulator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        from services.auth_service import get_test_token
        cls.client.headers["Authorization"] = f"Bearer {get_test_token('demo_user', 'candidate@careerlens.ai')}"

    # ─── 1. Baseline Simulation Score Matches Regular Matching Engine ───
    def test_01_baseline_simulation_score_matches_regular_matching_engine(self):
        regular_match = matching_service.match_resume_to_job(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            job_data=SAMPLE_JOB_DATA
        )

        sim_result = career_service.simulate_what_if(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            job_data=SAMPLE_JOB_DATA,
            added_skills=[]
        )

        self.assertEqual(
            sim_result["baseline_score"],
            regular_match["overall_score"],
            f"Baseline score {sim_result['baseline_score']} does not match regular engine {regular_match['overall_score']}"
        )
        self.assertEqual(sim_result["baseline_grade"], regular_match["match_grade"])
        self.assertEqual(sim_result["simulated_score"], sim_result["baseline_score"])
        self.assertEqual(sim_result["score_delta"], 0)
        self.assertEqual(sim_result["subscore_deltas"]["overall"]["delta"], 0)

    # ─── 2. Adding Relevant Skill Changes Only Appropriate Requirements ───
    def test_02_adding_relevant_skill_changes_only_appropriate_requirements(self):
        sim_result = career_service.simulate_what_if(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            job_data=SAMPLE_JOB_DATA,
            added_skills=["Docker"]
        )

        self.assertGreater(sim_result["score_delta"], 0, "Adding Docker should improve match score")
        self.assertIn("Docker", sim_result["closed_gaps"], "Docker gap should be closed")
        self.assertIn("Kubernetes", sim_result["remaining_gaps"], "Kubernetes should remain a gap")

        affected = sim_result["affected_requirements"]
        self.assertEqual(len(affected), 1, f"Expected 1 affected requirement, got {len(affected)}")
        docker_req = affected[0]
        self.assertEqual(docker_req["requirement"], "Docker")
        self.assertEqual(docker_req["baseline_status"], REQUIREMENT_STATUSES["MISSING"])
        self.assertEqual(docker_req["simulated_status"], REQUIREMENT_STATUSES["HYPOTHETICAL"])
        self.assertTrue(docker_req["status_changed"])
        self.assertEqual(docker_req["evidence_type"], "hypothetical_skill")
        self.assertEqual(docker_req["contributing_skill"], "Docker")

        for r in sim_result["requirement_deltas"]:
            if r["requirement"] in ["Python", "SQL"]:
                self.assertFalse(r["status_changed"])
                self.assertEqual(r["evidence_type"], "verified_resume")
            elif r["requirement"] == "Kubernetes":
                self.assertFalse(r["status_changed"])
                self.assertEqual(r["simulated_status"], REQUIREMENT_STATUSES["MISSING"])

    # ─── 3. Irrelevant Skills Do Not Produce Artificial Improvements ───
    def test_03_irrelevant_skills_do_not_produce_artificial_improvements(self):
        sim_result = career_service.simulate_what_if(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            job_data=SAMPLE_JOB_DATA,
            added_skills=["Origami", "Underwater Welding", "Latin Literature"]
        )

        self.assertEqual(sim_result["score_delta"], 0, f"Expected 0 score delta for irrelevant skills, got {sim_result['score_delta']}")
        self.assertEqual(len(sim_result["affected_requirements"]), 0)
        self.assertEqual(len(sim_result["closed_gaps"]), 0)
        self.assertEqual(sim_result["simulated_score"], sim_result["baseline_score"])

    # ─── 4. Unknown Skills Are Handled Safely ───
    def test_04_unknown_skills_are_handled_safely(self):
        custom_skill = "QuantumTranspiler99X"
        sim_result = career_service.simulate_what_if(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            job_data=SAMPLE_JOB_DATA,
            added_skills=[custom_skill]
        )

        evals = sim_result["hypothetical_skills_evaluated"]
        self.assertEqual(len(evals), 1)
        eval_item = evals[0]
        self.assertFalse(eval_item["is_recognized"])
        self.assertEqual(eval_item["status"], "custom_unverified")
        self.assertEqual(sim_result["score_delta"], 0)

    # ─── 5. Original Resume Data Is Unchanged After Simulation ───
    def test_05_original_resume_data_is_unchanged_after_simulation(self):
        profile_before = copy.deepcopy(SAMPLE_RESUME_PROFILE)
        text_before = str(SAMPLE_RESUME_TEXT)

        career_service.simulate_what_if(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            job_data=SAMPLE_JOB_DATA,
            added_skills=["Docker", "Kubernetes", "AWS", "Terraform"]
        )

        self.assertEqual(SAMPLE_RESUME_PROFILE, profile_before, "Candidate profile dictionary was mutated by simulation!")
        self.assertEqual(SAMPLE_RESUME_TEXT, text_before, "Raw resume text was mutated by simulation!")
        self.assertNotIn("Docker", SAMPLE_RESUME_PROFILE["skills"], "Hypothetical skill leaked into verified skills list!")

    # ─── 6. Missing Resume and Job Return Proper Errors ───
    def test_06_missing_resume_and_job_return_proper_errors(self):
        # 1. Non-existent resume ID
        res = self.client.post("/api/career/simulate", json={
            "resume_id": "non_existent_resume_99999",
            "job_id": "job-backend-001",
            "hypothetical_skills": ["Docker"]
        })
        self.assertIn(res.status_code, [400, 404, 422])

        # 2. Invalid non-existent job ID
        res = self.client.post("/api/career/simulate", json={
            "resume_profile": SAMPLE_RESUME_PROFILE,
            "resume_text": SAMPLE_RESUME_TEXT,
            "job_id": "non_existent_job_9999",
            "hypothetical_skills": ["Docker"]
        })
        self.assertEqual(res.status_code, 404)

        # 3. Missing both job_id and job_description
        res = self.client.post("/api/career/simulate", json={
            "resume_profile": SAMPLE_RESUME_PROFILE,
            "resume_text": SAMPLE_RESUME_TEXT,
            "hypothetical_skills": ["Docker"]
        })
        self.assertEqual(res.status_code, 400)

    # ─── 7. Identical Inputs Produce Reproducible Results ───
    def test_07_identical_inputs_produce_reproducible_results(self):
        run1 = career_service.simulate_what_if(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            job_data=SAMPLE_JOB_DATA,
            added_skills=["Docker"]
        )
        run2 = career_service.simulate_what_if(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            job_data=SAMPLE_JOB_DATA,
            added_skills=["Docker"]
        )

        self.assertEqual(run1["baseline_score"], run2["baseline_score"])
        self.assertEqual(run1["simulated_score"], run2["simulated_score"])
        self.assertEqual(run1["score_delta"], run2["score_delta"])
        self.assertEqual(run1["subscore_deltas"], run2["subscore_deltas"])
        self.assertEqual(run1["closed_gaps"], run2["closed_gaps"])

    # ─── 8. Evidence Labels Distinguish Hypothetical and Verified Skills ───
    def test_08_evidence_labels_distinguish_hypothetical_and_verified_skills(self):
        sim_result = career_service.simulate_what_if(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            job_data=SAMPLE_JOB_DATA,
            added_skills=["Docker"]
        )

        reqs_by_name = {r["requirement"]: r for r in sim_result["requirement_deltas"]}
        
        # Verified skill
        python_req = reqs_by_name["Python"]
        self.assertEqual(python_req["evidence_type"], "verified_resume")
        self.assertIn(python_req["simulated_status"], [REQUIREMENT_STATUSES["MATCHED"], REQUIREMENT_STATUSES["UNVERIFIED"]])

        # Hypothetical skill
        docker_req = reqs_by_name["Docker"]
        self.assertEqual(docker_req["evidence_type"], "hypothetical_skill")
        self.assertEqual(docker_req["simulated_status"], REQUIREMENT_STATUSES["HYPOTHETICAL"])
        self.assertIn("Simulated competency only", docker_req["uncertainty_note"])

    # ─── 9. Scoring Configuration Is Reused ───
    def test_09_scoring_configuration_is_reused(self):
        sim_result = career_service.simulate_what_if(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            job_data=SAMPLE_JOB_DATA,
            added_skills=["Docker"]
        )

        policy = sim_result["simulation_policy"]
        self.assertEqual(policy["hypothetical_skill_credit"], HYPOTHETICAL_SKILL_CREDIT)
        self.assertEqual(policy["weights_summary"], MATCHING_WEIGHTS)
        self.assertTrue(policy["scoring_weights_reused"])

        subscores = sim_result["subscore_deltas"]
        self.assertEqual(subscores["experience_match"]["delta"], 0)
        self.assertEqual(subscores["education_match"]["delta"], 0)
        self.assertEqual(subscores["project_relevance"]["delta"], 0)

    # ─── 10. Career Paths Use Actual Available Taxonomy/Profile Data ───
    def test_10_career_paths_use_actual_available_taxonomy_and_profile_data(self):
        paths_result = career_service.analyze_career_paths(
            resume_profile=SAMPLE_RESUME_PROFILE,
            raw_resume_text=SAMPLE_RESUME_TEXT,
            target_roles=[SAMPLE_JOB_DATA]
        )

        self.assertIn("paths", paths_result)
        self.assertGreater(len(paths_result["paths"]), 0)
        path_item = paths_result["paths"][0]
        
        self.assertIn("role_title", path_item)
        self.assertIn("overall_score", path_item)
        self.assertIn("matched_skills", path_item)
        self.assertIn("missing_skills", path_item)
        self.assertIn("transferable_skills", path_item)
        self.assertIn("readiness", path_item)

        self.assertNotIn("salary", path_item)
        self.assertNotIn("market_demand", path_item)
        self.assertNotIn("guarantee", str(path_item).lower())

    # ─── 11. API Simulation End-to-End Success ───
    def test_11_api_simulation_end_to_end_success(self):
        res = self.client.post("/api/career/simulate", json={
            "resume_profile": SAMPLE_RESUME_PROFILE,
            "resume_text": SAMPLE_RESUME_TEXT,
            "job_id": "job-backend-001",
            "hypothetical_skills": ["Docker", "Kubernetes"]
        })

        self.assertEqual(res.status_code, 200, f"Simulate endpoint failed: {res.text}")
        data = res.json()
        self.assertIn("simulation_id", data)
        self.assertIn("baseline_score", data)
        self.assertIn("simulated_score", data)
        self.assertIn("score_delta", data)
        self.assertIn("subscore_deltas", data)
        self.assertIn("requirement_deltas", data)
        self.assertIn("simulation_policy", data)
        self.assertIn("recommendation", data)
        self.assertGreater(len(data["requirement_deltas"]), 0)

    # ─── 12. API Career Paths End-to-End Success ───
    def test_12_api_career_paths_end_to_end_success(self):
        # First ensure a resume is in the DB
        ana_res = self.client.post("/api/resume/analyze", json={
            "resume_text": SAMPLE_RESUME_TEXT,
            "filename": "Jordan_Lee_Resume.txt"
        })
        self.assertEqual(ana_res.status_code, 200)
        resume_id = ana_res.json()["resume_id"]

        # Call GET /api/career/paths with resume_id
        res = self.client.get(f"/api/career/paths?resume_id={resume_id}")
        self.assertEqual(res.status_code, 200, f"Career paths endpoint failed: {res.text}")
        data = res.json()
        self.assertIn("analysis_id", data)
        self.assertIn("candidate_name", data)
        self.assertIn("paths", data)
        self.assertGreater(len(data["paths"]), 0)
        self.assertIn("best_fit", data)
        first_path = data["paths"][0]
        self.assertIn("overall_score", first_path)
        self.assertIn("transferable_skills", first_path)
        self.assertNotIn("salary", first_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
