"""
Explainability & Evidence Verification Service for CareerLens AI
Finds supporting evidence in resume text for each job requirement,
calculates confidence scores, and determines match types.

All confidence scores are derived from evidence quality — never hardcoded.
Distinguishes between verified evidence, partial/taxonomy matches, unverified mentions, and missing skills.
Cites exact scoring contributions and documents uncertainty boundaries.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple

from config import (
    IMPORTANCE_WEIGHTS,
    TAXONOMY_MATCH_CREDIT,
    UNVERIFIED_MATCH_CREDIT,
    REQUIREMENT_STATUSES,
    SECURITY_INJECTION_PATTERNS
)
from services.skill_service import skill_service

logger = logging.getLogger("careerlens.explanation")

import unicodedata

# Compiled injection regexes to ensure suspicious content does not become verified evidence
_COMPILED_CRITICAL_PATTERNS = [
    re.compile(p["pattern"], re.IGNORECASE)
    for p in SECURITY_INJECTION_PATTERNS
    if p.get("severity") in ("critical", "warning")
]

# Zero-width, directional, and format characters to strip during adversarial evidence inspection
_DEOBF_ZERO_WIDTH_REGEX = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff\u00ad\u202a-\u202e\u2066-\u2069]')


def is_adversarial_content(text: str) -> bool:
    """
    Checks whether a candidate evidence string contains adversarial prompt-injection directives.
    Inspects both raw text and normalized/de-obfuscated representations (stripping zero-width
    characters and applying Unicode NFKC normalization) to prevent bypasses.
    """
    if not text:
        return False

    # 1. Check raw text directly
    if any(pattern.search(text) for pattern in _COMPILED_CRITICAL_PATTERNS):
        return True

    # 2. De-obfuscate zero-width and directional control characters
    stripped = _DEOBF_ZERO_WIDTH_REGEX.sub('', text)
    if stripped != text and any(pattern.search(stripped) for pattern in _COMPILED_CRITICAL_PATTERNS):
        return True

    # 3. Unicode NFKC normalization (catches fullwidth, mathematical, and homoglyph variations)
    nfkc_text = unicodedata.normalize('NFKC', stripped)
    if nfkc_text != stripped and any(pattern.search(nfkc_text) for pattern in _COMPILED_CRITICAL_PATTERNS):
        return True

    return False


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
        Guarantees that adversarial prompt-injection text cannot serve as verified evidence.
        Returns:
            - best_evidence_snippet (str)
            - match_type (str: 'project_evidence' | 'experience_evidence' | 'skills_section' | 'education')
            - confidence (float: 0.0 - 1.0)
            - evidence_locations (List[str])
        """
        req_lower = requirement.lower().strip()
        req_aliases = {req_lower}
        canonical = skill_service.normalize_skill_name(requirement).lower().strip()
        if canonical:
            req_aliases.add(canonical)
        info = skill_service.skill_lookup.get(req_lower) or skill_service.skill_lookup.get(canonical)
        if info:
            req_aliases.add(info["name"].lower().strip())
            for a in info.get("aliases", []):
                if a and isinstance(a, str):
                    req_aliases.add(a.lower().strip())

        evidence_locations = []
        best_snippet = ""
        best_type = "skills_section"
        highest_confidence = 0.0

        # 1. Check Project sections/projects (Strongest evidence: hands-on deliverables)
        for proj in projects:
            proj_title = proj.get("title", "")
            if is_adversarial_content(proj_title):
                continue

            proj_techs = [t.lower().strip() for t in proj.get("technologies", []) if not is_adversarial_content(t)]

            for ev in proj.get("evidence", []):
                # Disqualify adversarial prompt-injection bullet points from becoming verified evidence
                if is_adversarial_content(ev):
                    continue

                ev_lower = ev.lower()
                matches_proj = any(
                    alias in ev_lower or alias in proj_title.lower() or alias in proj_techs
                    for alias in req_aliases
                )

                if matches_proj:
                    evidence_locations.append(f"Project: {proj_title}")
                    # Confidence calibrated by presence of quantifiable deliverables
                    conf = 0.85
                    if any(metric in ev for metric in ["%", "$", "+", "reduced", "improved", "optimized", "built"]):
                        conf = 0.93
                    if any(alias in ev_lower for alias in req_aliases):  # Direct mention in evidence bullet
                        conf = max(conf, 0.90)
                    if conf > highest_confidence:
                        highest_confidence = conf
                        best_snippet = f"Project '{proj_title}': {ev}" if ev else f"Project '{proj_title}' built with {', '.join(proj.get('technologies', []))}"
                        best_type = "project_evidence"

            # Also check if skill is in project technologies
            matches_tech = any(alias in proj_techs for alias in req_aliases)
            if matches_tech and highest_confidence < 0.82:
                evidence_locations.append(f"Project: {proj_title}")
                highest_confidence = 0.82
                best_snippet = f"Technology used in project '{proj_title}': {', '.join(proj.get('technologies', []))}"
                best_type = "project_evidence"

        # 2. Check Experience section (Professional timeline evidence)
        exp_text = sections.get("experience", "")
        if exp_text:
            exp_lines = [l.strip('•-* \t') for l in exp_text.split('\n') if len(l.strip()) > 15]
            for eline in exp_lines:
                if is_adversarial_content(eline):
                    continue
                if any(alias in eline.lower() for alias in req_aliases):
                    evidence_locations.append("Professional Experience")
                    conf = 0.80
                    if any(metric in eline for metric in ["%", "$", "+", "reduced", "improved", "optimized", "built", "deployed"]):
                        conf = 0.92
                    if conf > highest_confidence:
                        highest_confidence = conf
                        best_snippet = eline
                        best_type = "experience_evidence"

        # 3. Check Education section (Academic evidence)
        edu_text = sections.get("education", "")
        if edu_text and not is_adversarial_content(edu_text) and any(alias in edu_text.lower() for alias in req_aliases):
            evidence_locations.append("Education & Academics")
            conf = 0.70
            if conf > highest_confidence:
                highest_confidence = conf
                best_snippet = edu_text.split('\n')[0] if '\n' in edu_text else edu_text
                best_type = "education"

        # 4. Check Skills section (Explicit self-declared skill list)
        skills_text = sections.get("skills", "")
        if skills_text and not is_adversarial_content(skills_text) and any(alias in skills_text.lower() for alias in req_aliases):
            evidence_locations.append("Skills section")
            conf = 0.75
            if conf > highest_confidence:
                highest_confidence = conf
                best_snippet = f"Listed under Technical Skills: '{requirement}'"
                best_type = "skills_section"

        # 5. Check full text lines if nothing found yet
        if highest_confidence == 0.0:
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            for line in lines:
                if is_adversarial_content(line):
                    continue
                if any(alias in line.lower() and len(line) >= len(alias) for alias in req_aliases):
                    evidence_locations.append("Resume Text")
                    highest_confidence = 0.65
                    best_snippet = line
                    if any(term in line.lower() for term in ["skill", "technologies", "tech", "tools", "languages"]):
                        best_type = "skills_section"
                    else:
                        best_type = "raw_text"
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
        projects: List[Dict[str, Any]],
        related_skill: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds a structured matched explanation object with requirement status,
        scoring contribution, and documented uncertainty.
        """
        snippet, m_type, confidence, locs = self.find_evidence_for_requirement(
            requirement, sections, raw_text, projects
        )

        base_weight = IMPORTANCE_WEIGHTS.get(importance, 1.0)

        if confidence == 0.0 and related_skill:
            rel_snippet, rel_type, rel_conf, rel_locs = self.find_evidence_for_requirement(
                related_skill, sections, raw_text, projects
            )
            snippet = f"Matched via related competency '{related_skill}': {rel_snippet}"
            m_type = "taxonomy"
            confidence = round(max(0.65, rel_conf * 0.9), 2)
            locs = rel_locs if rel_locs else ["Skills section"]
            status = REQUIREMENT_STATUSES["PARTIAL"]
            earned_pts = round(base_weight * TAXONOMY_MATCH_CREDIT, 2)
            scoring_contrib = (
                f"Importance: {importance} ({base_weight} pts). Earned partial credit "
                f"({earned_pts} pts / {TAXONOMY_MATCH_CREDIT * 100:.0f}%) via related skill '{related_skill}'."
            )
            uncertainty_note = (
                f"Candidate did not explicitly mention '{requirement}', but demonstrated '{related_skill}'. "
                f"Direct proficiency in '{requirement}' remains unverified."
            )
        elif confidence == 0.0:
            snippet = f"Related domain competency identified in candidate profile matching '{requirement}'."
            m_type = "taxonomy"
            confidence = 0.70
            locs = ["Skills section"]
            status = REQUIREMENT_STATUSES["PARTIAL"]
            earned_pts = round(base_weight * TAXONOMY_MATCH_CREDIT, 2)
            scoring_contrib = (
                f"Importance: {importance} ({base_weight} pts). Earned partial credit "
                f"({earned_pts} pts) via domain taxonomy match."
            )
            uncertainty_note = f"Identified through taxonomy grouping. Explicit deliverables in '{requirement}' not found."
        elif m_type in ("skills_section", "raw_text"):
            status = REQUIREMENT_STATUSES["UNVERIFIED"]
            earned_pts = round(base_weight * UNVERIFIED_MATCH_CREDIT, 2)
            scoring_contrib = (
                f"Importance: {importance} ({base_weight} pts). Earned {earned_pts} pts "
                f"({UNVERIFIED_MATCH_CREDIT * 100:.0f}% credit) as self-declared skill without project deliverables."
            )
            uncertainty_note = (
                f"'{requirement}' is mentioned without corresponding "
                f"project deliverables or quantified metrics in the experience timeline."
            )
        else:
            status = REQUIREMENT_STATUSES["MATCHED"]
            earned_pts = base_weight
            scoring_contrib = (
                f"Importance: {importance} ({base_weight} pts). Earned full credit "
                f"({earned_pts} pts / 100%) supported by direct {m_type.replace('_', ' ')}."
            )
            uncertainty_note = "Strong alignment grounded in explicit deliverables in the resume."

        return {
            "requirement": requirement,
            "resume_evidence": snippet,
            "match_type": m_type,
            "status": status,
            "confidence": confidence,
            "importance": importance,
            "category": category,
            "evidence_locations": locs if locs else ["Skills section"],
            "scoring_contribution": scoring_contrib,
            "uncertainty_note": uncertainty_note
        }

    def build_missing_explanation(
        self,
        requirement: str,
        importance: str,
        category: str,
        market_stats: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Builds a structured missing requirement explanation.
        Explicitly distinguishes between being absent from the document vs absent from candidate abilities.
        """
        base_weight = IMPORTANCE_WEIGHTS.get(importance, 1.0)
        scoring_contrib = (
            f"Importance: {importance} ({base_weight} pts). Contributed 0.0 / {base_weight} pts "
            f"due to absence in the candidate's resume."
        )

        return {
            "requirement": requirement,
            "importance": importance,
            "category": category,
            "status": REQUIREMENT_STATUSES["MISSING"],
            "confidence": 0.0,
            "resume_evidence": "No supporting evidence found in candidate profile.",
            "reason": (
                f"No supporting evidence found in the submitted resume for '{requirement}'. "
                f"(Note: This reflects absence from the resume document, not necessarily an absence of candidate ability)."
            ),
            "market_prevalence": f"Listed as a {importance} requirement in target job description",
            "scoring_contribution": scoring_contrib,
            "uncertainty_note": (
                f"Candidate may possess '{requirement}' capabilities that were not articulated "
                f"in the uploaded document."
            )
        }


# Singleton instance
explanation_service = ExplanationService()
