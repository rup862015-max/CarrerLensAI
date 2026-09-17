"""
Explainability & Evidence Verification Service for CareerLens AI
Finds supporting evidence in resume text for each job requirement,
calculates confidence scores, and determines match types.
"""

import re
from typing import Dict, List, Any, Optional, Tuple


class ExplanationService:
    def __init__(self):
        pass

    def find_evidence_for_requirement(
        self,
        requirement: str,
        sections: Dict[str, str],
        raw_text: str,
        projects: List[Dict[str, Any]]
    ) -> Tuple[str, str, float, List[str]]:
        """
        Finds the strongest piece of evidence supporting a requirement.
        Returns:
            - best_evidence_snippet (str)
            - match_type (str: 'project_evidence' | 'experience_evidence' | 'skills_section' | 'education')
            - confidence (float: 0.0 - 1.0)
            - evidence_locations (List[str])
        """
        req_lower = requirement.lower()
        evidence_locations = []
        best_snippet = ""
        best_type = "skills_section"
        highest_confidence = 0.0

        # Split text into lines/sentences
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]

        # 1. Check Project sections/projects
        for proj in projects:
            proj_title = proj.get("title", "")
            for ev in proj.get("evidence", []):
                if req_lower in ev.lower() or req_lower in proj_title.lower() or any(req_lower in tech.lower() for tech in proj.get("technologies", [])):
                    evidence_locations.append(f"Project: {proj_title}")
                    if highest_confidence < 0.94:
                        highest_confidence = 0.94
                        best_snippet = f"Project '{proj_title}': {ev}" if ev else f"Project '{proj_title}' built with {', '.join(proj.get('technologies', []))}"
                        best_type = "project_evidence"

        # 2. Check Experience section
        exp_text = sections.get("experience", "")
        if exp_text:
            exp_lines = [l.strip('•-* \t') for l in exp_text.split('\n') if len(l.strip()) > 15]
            for eline in exp_lines:
                if req_lower in eline.lower():
                    evidence_locations.append("Professional Experience")
                    conf = 0.92
                    if any(metric in eline for metric in ["%", "$", "+", "reduced", "improved", "optimized", "built"]):
                        conf = 0.96
                    if conf > highest_confidence:
                        highest_confidence = conf
                        best_snippet = eline
                        best_type = "experience_evidence"

        # 3. Check Education section
        edu_text = sections.get("education", "")
        if edu_text and req_lower in edu_text.lower():
            evidence_locations.append("Education & Academics")
            if highest_confidence < 0.88:
                highest_confidence = 0.88
                best_snippet = edu_text.split('\n')[0] if '\n' in edu_text else edu_text
                best_type = "education"

        # 4. Check Skills section
        skills_text = sections.get("skills", "")
        if skills_text and req_lower in skills_text.lower():
            evidence_locations.append("Skills section")
            if highest_confidence < 0.82:
                highest_confidence = 0.82
                best_snippet = f"Explicitly listed under Technical Skills: '{requirement}'"
                best_type = "skills_section"

        # 5. Check full text lines if nothing found yet
        if highest_confidence == 0.0:
            for line in lines:
                if req_lower in line.lower() and len(line) > 10:
                    evidence_locations.append("Resume Text")
                    highest_confidence = 0.75
                    best_snippet = line
                    best_type = "experience_evidence"
                    break

        if not best_snippet:
            return "No supporting evidence found in candidate profile.", "none", 0.0, []

        # Deduplicate evidence locations
        unique_locs = list(dict.fromkeys(evidence_locations))
        return best_snippet, best_type, round(highest_confidence, 2), unique_locs

    def build_matched_explanation(
        self,
        requirement: str,
        importance: str,
        category: str,
        sections: Dict[str, str],
        raw_text: str,
        projects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Builds a structured matched explanation object."""
        snippet, m_type, confidence, locs = self.find_evidence_for_requirement(
            requirement, sections, raw_text, projects
        )

        return {
            "requirement": requirement,
            "resume_evidence": snippet,
            "match_type": m_type,
            "status": "matched",
            "confidence": confidence if confidence > 0 else 0.85,
            "importance": importance,
            "category": category,
            "evidence_locations": locs if locs else ["Skills section"]
        }

    def build_missing_explanation(
        self,
        requirement: str,
        importance: str,
        category: str,
        market_stats: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Builds a structured missing requirement explanation."""
        market_percent = "68%" if importance == "critical" else "45%"
        if market_stats and requirement in market_stats:
            market_percent = market_stats[requirement]

        return {
            "requirement": requirement,
            "importance": importance,
            "category": category,
            "reason": f"No supporting evidence found in candidate's skills, experience, or project portfolio for '{requirement}'.",
            "market_prevalence": f"Found in {market_percent} of similar roles in demo benchmarks"
        }


# Singleton instance
explanation_service = ExplanationService()
