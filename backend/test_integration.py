"""
Integration Test Suite for AI Resume Analysis Engine
Tests end-to-end extraction, ATS scoring, keyword gap detection, and bullet point optimization.
"""

import sys
import os
import unittest

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_resume_analysis import ResumeAnalyzer, SKILLS_TAXONOMY


class TestAIResumeAnalysis(unittest.TestCase):
    def setUp(self):
        self.analyzer = ResumeAnalyzer()
        self.sample_resume = """
        Jane Smith
        jane.smith@techcorp.io | +1 (555) 987-6543 | linkedin.com/in/janesmith | github.com/janesmith
        
        PROFESSIONAL SUMMARY
        Lead Cloud Engineer with 7+ years of experience architecting distributed backend services,
        CI/CD pipelines, and microservices on AWS and Kubernetes.
        
        TECHNICAL SKILLS
        Languages: Python, TypeScript, Go, SQL
        Frameworks: FastAPI, React, Next.js, Node.js
        Cloud & DevOps: AWS, Docker, Kubernetes, Terraform, GitHub Actions
        Databases: PostgreSQL, Redis, MongoDB
        
        WORK EXPERIENCE
        Principal Cloud Architect | HyperScale Solutions (2021 - Present)
        • Orchestrated container migration to AWS EKS for 40+ microservices, cutting infrastructure costs by 32%.
        • Engineered automated CI/CD release pipeline, accelerating deployment frequency by 400% with zero downtime.
        • Scaled PostgreSQL database throughput by 55% using Redis caching and query indexing for 8M daily requests.
        
        EDUCATION
        B.S. in Computer Science | Stanford University
        """

        self.sample_job_desc = """
        Looking for a Lead Cloud Architect with experience in Python, AWS, Docker, Kubernetes, Terraform, and PostgreSQL.
        Must have strong distributed systems background and team leadership.
        """

    def test_section_extraction(self):
        """Test extraction of standard resume sections."""
        sections = self.analyzer.extract_sections(self.sample_resume)
        self.assertIn("summary", sections)
        self.assertIn("experience", sections)
        self.assertIn("skills", sections)
        self.assertIn("education", sections)
        self.assertIn("FastAPI", sections["skills"])

    def test_contact_and_ats_formatting(self):
        """Test ATS parseability and contact info recognition."""
        sections = self.analyzer.extract_sections(self.sample_resume)
        ats_eval = self.analyzer.calculate_ats_formatting_score(self.sample_resume, sections)
        self.assertGreaterEqual(ats_eval["score"], 80)
        self.assertTrue(any("email" in f.lower() for f in ats_eval["feedback"]))

    def test_metric_density_evaluation(self):
        """Test detection of quantifiable metrics in experience bullets."""
        metric_eval = self.analyzer.evaluate_metric_density(self.sample_resume)
        self.assertGreaterEqual(metric_eval["metric_count"], 3)
        self.assertGreaterEqual(metric_eval["score"], 70)

    def test_keyword_matching_and_gaps(self):
        """Test keyword extraction and comparison against job description."""
        keyword_eval = self.analyzer.analyze_keywords(self.sample_resume, self.sample_job_desc)
        self.assertGreaterEqual(keyword_eval["matched_count"], 5)
        self.assertGreaterEqual(keyword_eval["score"], 60)
        
        # Check specific key skills were detected
        gaps = keyword_eval["gaps"]
        found_keywords = [g["keyword"].lower() for g in gaps if g["foundInResume"]]
        self.assertIn("python", found_keywords)
        self.assertIn("aws", found_keywords)
        self.assertIn("kubernetes", found_keywords)

    def test_bullet_improvements(self):
        """Test generation of STAR-method enhanced bullet points."""
        bullets = self.analyzer.generate_bullet_improvements(self.sample_resume)
        self.assertIsInstance(bullets, list)
        self.assertGreater(len(bullets), 0)
        for b in bullets:
            self.assertIn("original", b)
            self.assertIn("improved", b)
            self.assertIn("reason", b)
            self.assertGreater(b["impactScoreAfter"], b["impactScoreBefore"])

    def test_full_analysis_pipeline(self):
        """Test complete end-to-end resume evaluation output structure."""
        result = self.analyzer.analyze(
            resume_text=self.sample_resume,
            job_description=self.sample_job_desc,
            target_role="Lead Cloud Architect"
        )
        self.assertIn("overallScore", result)
        self.assertIn("atsScore", result)
        self.assertIn("keywordMatchScore", result)
        self.assertIn("impactScore", result)
        self.assertIn("matchGrade", result)
        self.assertIn("summary", result)
        self.assertIn("strengths", result)
        self.assertIn("criticalIssues", result)
        self.assertIn("keywordGaps", result)
        self.assertIn("sections", result)
        self.assertIn("bulletImprovements", result)
        self.assertIn("interviewQuestions", result)
        
        self.assertGreaterEqual(result["overallScore"], 75)
        self.assertIn(result["matchGrade"], ["A+", "A", "B+", "B"])

    def test_empty_resume_handling(self):
        """Test that empty resume input raises ValueError."""
        with self.assertRaises(ValueError):
            self.analyzer.analyze("")


if __name__ == "__main__":
    unittest.main(verbosity=2)
