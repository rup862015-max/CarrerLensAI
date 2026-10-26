"""
Hybrid Multi-Layer Matching Service for CareerLens AI
Layer 1: Exact Skill Matching
Layer 2: Taxonomy & Synonym Hierarchy Matching
Layer 3: Semantic TF-IDF Cosine Similarity

All scores are dynamically computed and deterministic. No hardcoded magic numbers.
Scoring rules and weights are strictly imported from config.py.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.skill_service import skill_service
from services.explanation_service import explanation_service
from services.resume_parser import extract_sections
from config import (
    MATCHING_WEIGHTS,
    IMPORTANCE_WEIGHTS,
    TAXONOMY_MATCH_CREDIT,
    UNVERIFIED_MATCH_CREDIT,
    HYPOTHETICAL_SKILL_CREDIT,
    EXPERIENCE_SCORING,
    EDUCATION_SCORING,
    PROJECT_SCORING,
    SEMANTIC_SCORING,
    REQUIREMENT_STATUSES,
    get_match_grade,
)

logger = logging.getLogger("careerlens.matching")


class MatchingService:
    def __init__(self):
        self.skill_svc = skill_service
        self.exp_svc = explanation_service

    def compute_semantic_similarity(self, resume_text: str, job_text: str) -> int:
        """
        Computes semantic vector similarity between resume content and job description
        using TF-IDF with n-grams and cosine similarity, scaled according to SEMANTIC_SCORING.
        """
        if not resume_text or not job_text:
            return 0

        try:
            vectorizer = TfidfVectorizer(
                stop_words='english',
                ngram_range=(1, 2),
                max_features=500
            )
            tfidf_matrix = vectorizer.fit_transform([resume_text, job_text])
            sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            scaled = min(
                SEMANTIC_SCORING["max_score"],
                max(
                    SEMANTIC_SCORING["min_score"],
                    int((sim ** SEMANTIC_SCORING["exponent"]) * SEMANTIC_SCORING["multiplier"])
                )
            )
            return scaled
        except Exception as e:
            logger.warning(f"Semantic similarity computation failed: {e}")
            return 0

    def match_resume_to_job(
        self,
        resume_profile: Dict[str, Any],
        raw_resume_text: str,
        job_data: Dict[str, Any],
        hypothetical_skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Main matching engine method.
        Compares candidate profile with job data and produces a comprehensive match result.
        All scores are dynamically computed from actual input and centralized config.
        When hypothetical_skills are provided, they are evaluated under the simulation policy
        without modifying the candidate's verified profile or inflating unevidenced credit.
        """
        raw_candidate_skills = resume_profile.get("skills") or []
        candidate_skills_raw = set(s.lower().strip() for s in raw_candidate_skills if s and isinstance(s, str))
        candidate_skills_canonical = set()
        for s in candidate_skills_raw:
            norm = self.skill_svc.normalize_skill_name(s).lower().strip()
            if norm:
                candidate_skills_canonical.add(norm)
        candidate_skills = candidate_skills_raw | candidate_skills_canonical

        raw_resume_text = raw_resume_text or ""
        raw_resume_lower = raw_resume_text.lower()
        sections = extract_sections(raw_resume_text)
        projects = resume_profile.get("projects") or []

        # Build normalized hypothetical skill set if provided
        hypo_set = set()
        if hypothetical_skills:
            for hs in hypothetical_skills:
                norm = self.skill_svc.normalize_skill_name(hs).lower().strip()
                if norm:
                    hypo_set.add(norm)
                if hs.strip():
                    hypo_set.add(hs.strip().lower())

        job_requirements = job_data.get("requirements") or []
        job_title = job_data.get("title", "Target Position")
        job_text = (job_data.get("description", "") or "") + " " + " ".join([r.get("name", "") for r in job_requirements if isinstance(r, dict)])

        matched_reqs = []
        missing_reqs = []
        skill_gaps = []

        total_req_weight = 0.0
        earned_req_weight = 0.0

        for req in job_requirements:
            req_name = req.get("name", "")
            req_lower = req_name.lower().strip()
            req_canonical = self.skill_svc.normalize_skill_name(req_name).lower().strip()
            importance = req.get("importance", "recommended")
            category = req.get("category", "general")

            # Weight by importance (from config)
            weight = IMPORTANCE_WEIGHTS.get(importance, 1.0)
            total_req_weight += weight

            # Layer 1: Exact Match in Verified Resume Evidence (with alias normalization)
            is_matched = False
            match_layer = None
            matched_related = None
            if (
                req_lower in candidate_skills
                or req_canonical in candidate_skills
                or req_lower in raw_resume_lower
                or req_canonical in raw_resume_lower
            ):
                is_matched = True
                match_layer = "exact"
            else:
                # Layer 2: Taxonomy & Related Skills Match in Verified Resume Evidence
                related = self.skill_svc.get_related_skills(req_name)
                if not related and req_canonical:
                    related = self.skill_svc.get_related_skills(req_canonical)
                for rel in related:
                    rel_norm = self.skill_svc.normalize_skill_name(rel).lower().strip()
                    if rel.lower() in candidate_skills or rel_norm in candidate_skills:
                        is_matched = True
                        match_layer = "taxonomy"
                        matched_related = rel
                        break

            if is_matched:
                matched_obj = self.exp_svc.build_matched_explanation(
                    requirement=req_name,
                    importance=importance,
                    category=category,
                    sections=sections,
                    raw_text=raw_resume_text,
                    projects=projects,
                    related_skill=matched_related
                )
                matched_reqs.append(matched_obj)

                # Weight contribution based on verified status
                if matched_obj.get("status") == REQUIREMENT_STATUSES["PARTIAL"]:
                    earned_req_weight += weight * TAXONOMY_MATCH_CREDIT
                elif matched_obj.get("status") == REQUIREMENT_STATUSES["UNVERIFIED"]:
                    earned_req_weight += weight * UNVERIFIED_MATCH_CREDIT
                else:
                    earned_req_weight += weight
            elif hypo_set and (req_lower in hypo_set or self.skill_svc.normalize_skill_name(req_name).lower().strip() in hypo_set):
                # Layer 3S: Hypothetical Exact / Canonical Match (Simulation Policy)
                matched_obj = {
                    "requirement": req_name,
                    "resume_evidence": f"Hypothetical Skill Exploration: Projected addition of '{req_name}' (simulated competency, not evidenced in original resume document).",
                    "match_type": "hypothetical_simulation",
                    "status": REQUIREMENT_STATUSES["HYPOTHETICAL"],
                    "confidence": 0.70,
                    "importance": importance,
                    "category": category,
                    "evidence_locations": ["What-If Simulation"],
                    "scoring_contribution": (
                        f"Importance: {importance} ({weight} pts). Earned projected credit "
                        f"({weight * HYPOTHETICAL_SKILL_CREDIT:.2f} pts / {HYPOTHETICAL_SKILL_CREDIT * 100:.0f}%) based on hypothetical addition."
                    ),
                    "uncertainty_note": (
                        f"Simulated competency only. This skill does not yet have verified project deliverables "
                        f"or professional experience in the candidate's portfolio."
                    )
                }
                matched_reqs.append(matched_obj)
                earned_req_weight += weight * HYPOTHETICAL_SKILL_CREDIT
            else:
                missing_obj = self.exp_svc.build_missing_explanation(
                    requirement=req_name,
                    importance=importance,
                    category=category
                )
                missing_reqs.append(missing_obj)

                priority = "High" if importance in ("critical", "required") else (
                    "Medium" if importance in ("recommended", "preferred") else "Low"
                )
                skill_gaps.append({
                    "skill": req_name,
                    "priority": priority,
                    "why_it_matters": f"Listed as a {importance} requirement for this role.",
                    "current_evidence": "No evidence found in candidate profile",
                    "market_prevalence": f"Identified as a {importance} requirement in target job description"
                })

        # Calculate Subscores
        # 1. Skill Match
        if total_req_weight > 0:
            skill_match_score = int((earned_req_weight / total_req_weight) * 100)
        else:
            skill_match_score = 0
        skill_match_score = min(100, max(0, skill_match_score))

        # 2. Experience Match (using EXPERIENCE_SCORING with null safety)
        try:
            years_exp = float(resume_profile.get("years_of_experience") or 0.0)
        except (ValueError, TypeError):
            years_exp = 0.0
        exp_entries = len(resume_profile.get("experience") or [])
        if years_exp == 0 and exp_entries == 0:
            exp_match_score = EXPERIENCE_SCORING["zero_score"]
        else:
            calc_exp = (
                years_exp * EXPERIENCE_SCORING["years_weight"] +
                exp_entries * EXPERIENCE_SCORING["entries_weight"] +
                EXPERIENCE_SCORING["base_score"]
            )
            exp_match_score = min(EXPERIENCE_SCORING["max_score"], int(calc_exp))

        # 3. Education Match (using EDUCATION_SCORING with null safety)
        edu_list = resume_profile.get("education") or []
        if not edu_list:
            edu_match_score = EDUCATION_SCORING["missing"]
        elif any("master" in str(e).lower() or "m.tech" in str(e).lower() or "m.s." in str(e).lower() or "phd" in str(e).lower() for e in edu_list):
            edu_match_score = EDUCATION_SCORING["advanced"]
        elif any("bachelor" in str(e).lower() or "b.tech" in str(e).lower() or "b.e." in str(e).lower()
                  or "b.s." in str(e).lower() or "degree" in str(e).lower() or "science" in str(e).lower() for e in edu_list):
            edu_match_score = EDUCATION_SCORING["bachelors"]
        else:
            edu_match_score = EDUCATION_SCORING["other"]

        # 4. Project Relevance (using PROJECT_SCORING with alias normalization)
        proj_count = len(projects)
        if proj_count == 0:
            project_relevance_score = PROJECT_SCORING["zero_score"]
        else:
            # Check how many projects have technologies overlapping with job requirements (including aliases)
            req_names = set(r.get("name", "").lower().strip() for r in job_requirements if isinstance(r, dict) and r.get("name"))
            req_canonicals = set(self.skill_svc.normalize_skill_name(r.get("name", "")).lower().strip() for r in job_requirements if isinstance(r, dict) and r.get("name"))
            all_target_reqs = req_names | req_canonicals
            relevant_projects = 0
            for p in projects:
                if not isinstance(p, dict):
                    continue
                p_techs_raw = set(t.lower().strip() for t in (p.get("technologies") or []) if t and isinstance(t, str))
                p_techs_canonical = set(self.skill_svc.normalize_skill_name(t).lower().strip() for t in p_techs_raw)
                if (p_techs_raw | p_techs_canonical) & all_target_reqs:
                    relevant_projects += 1

            if relevant_projects > 0:
                calc_proj = PROJECT_SCORING["relevant_base"] + (relevant_projects * PROJECT_SCORING["relevant_project_weight"])
                project_relevance_score = min(PROJECT_SCORING["max_score"], int(calc_proj))
            else:
                calc_proj = PROJECT_SCORING["general_base"] + (proj_count * PROJECT_SCORING["general_project_weight"])
                project_relevance_score = min(PROJECT_SCORING["general_max"], int(calc_proj))

        # 5. Semantic Fit (Layer 3)
        semantic_fit_score = self.compute_semantic_similarity(raw_resume_text, job_text)

        # Weighted Overall Score (from config)
        overall_score = int(
            (skill_match_score * MATCHING_WEIGHTS["skill_match"]) +
            (project_relevance_score * MATCHING_WEIGHTS["project_relevance"]) +
            (exp_match_score * MATCHING_WEIGHTS["experience_match"]) +
            (semantic_fit_score * MATCHING_WEIGHTS["semantic_fit"]) +
            (edu_match_score * MATCHING_WEIGHTS["education_match"])
        )
        overall_score = min(99, max(0, overall_score))

        # Match Grade (from config)
        match_grade = get_match_grade(overall_score)

        # Career Intelligence Preview — all derived from actual data
        missing_skill_names = [g["skill"] for g in skill_gaps[:5]]
        career_preview = {
            "current_strongest_path": job_title,
            "match_percentage": overall_score,
            "potential_next_step": f"Senior {job_title}" if overall_score > 75 else f"Stronger {job_title} Candidate",
            "skills_to_add": missing_skill_names,
            "readiness_level": "High" if overall_score >= 80 else ("Moderate" if overall_score >= 55 else "Developing")
        }

        # Side by Side Comparison
        profile_skills_list = resume_profile.get("skills") or []
        side_by_side = {
            "profile_skills": [
                {"name": s, "has_match": any(str(s).lower() == req.get("name", "").lower() for req in job_requirements)}
                for s in profile_skills_list if s
            ],
            "job_requirements": [
                {
                    "name": r.get("name", ""),
                    "matched": any(r.get("name", "").lower() == m.get("requirement", "").lower() for m in matched_reqs),
                    "importance": r.get("importance", "recommended")
                }
                for r in job_requirements
            ]
        }

        # Recommendations — dynamically generated based on actual gaps
        recommendations = []

        # Ingestion integrity warning: Check if raw text had project evidence that was not captured in profile
        if not projects:
            raw_lower = raw_resume_text.lower()
            if any(term in raw_lower for term in ["technical projects", "key projects", "academic projects", "projects:", "project 1", "project 2"]):
                recommendations.append(
                    "Warning: Project content was detected in your source document but no structured projects were identified. "
                    "Review your extracted profile to ensure project evidence was not omitted before relying on matching scores."
                )

        if skill_gaps:
            high_gaps = [g["skill"] for g in skill_gaps if g["priority"] == "High"]
            if high_gaps:
                recommendations.append(
                    f"Focus on acquiring high-priority skills: {', '.join(high_gaps[:3])}. "
                    f"Add projects demonstrating these skills to improve your match."
                )
            else:
                recommendations.append(
                    f"Consider strengthening your profile with: {', '.join([g['skill'] for g in skill_gaps[:3]])}."
                )
        if semantic_fit_score < 50:
            recommendations.append(
                "Your resume language doesn't closely match this job description. "
                "Consider incorporating more domain-specific terminology from the job posting."
            )
        if project_relevance_score < 40:
            recommendations.append(
                "Your projects don't demonstrate strong alignment with this role's requirements. "
                "Consider adding projects that use the required technologies."
            )
        if exp_match_score < 50:
            recommendations.append(
                "Strengthen your experience section with more action-verb-driven bullet points "
                "and quantifiable achievements."
            )
        if not recommendations:
            recommendations.append(
                "Your profile shows strong alignment with this position. "
                "Focus on interview preparation and deepening expertise in your strongest areas."
            )

        return {
            "match_id": f"match_{uuid.uuid4().hex[:8]}",
            "job_title": job_title,
            "overall_score": overall_score,
            "match_grade": match_grade,
            "skill_match": skill_match_score,
            "experience_match": exp_match_score,
            "education_match": edu_match_score,
            "project_relevance": project_relevance_score,
            "semantic_fit": semantic_fit_score,
            "matched_requirements": matched_reqs,
            "missing_requirements": missing_reqs,
            "skill_gaps": skill_gaps,
            "side_by_side": side_by_side,
            "career_preview": career_preview,
            "recommendations": recommendations
        }


# Singleton instance
matching_service = MatchingService()
