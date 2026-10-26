"""
Pluggable AI Service Layer for CareerLens AI
Provides clean abstraction for LLM integration (OpenAI, Gemini, Claude, etc.)
with a high-quality deterministic NLP fallback engine when no API key is provided.

All extraction is dynamic — no hardcoded candidate-specific data.
Integrates section preservation, project integrity, and explainability verification.
"""

import os
import re
import uuid
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

from services.resume_parser import extract_sections_detailed, clean_text
from services.skill_service import skill_service
from services.integrity_service import integrity_service
from services.security_service import security_service

logger = logging.getLogger("careerlens.ai")


class AIService:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY", "").strip()
        self.provider = os.getenv("LLM_PROVIDER", "mock").lower()
        self.skill_svc = skill_service
        self.integrity_svc = integrity_service
        self.security_svc = security_service

    def is_llm_active(self) -> bool:
        """Returns True if a live LLM API key is configured."""
        return bool(self.api_key and self.provider != "mock")

    def analyze_resume(self, text: str, filename: str = "Uploaded_Resume.pdf", file_type: str = "pdf") -> Dict[str, Any]:
        """
        Extracts structured candidate profile, preserves sections, checks ingestion integrity,
        executes deterministic security audit, and computes resume health scores.
        All values derived from actual input text.
        """
        cleaned = clean_text(text)
        detailed_sections = extract_sections_detailed(cleaned)
        sections = detailed_sections["canonical"]
        unrecognized_sections = detailed_sections["unrecognized"]
        header_text = detailed_sections.get("header", "")

        # Deterministic Security Audit & Injection Defense Scan
        security_audit = self.security_svc.scan_text(
            cleaned,
            filename=filename,
            source_type="resume"
        )

        # Extract Profile Components
        candidate_name = self._extract_name(cleaned, header_text)
        email, phone = self._extract_contact(cleaned)
        education = self._extract_education(sections.get("education", ""), cleaned)
        experience, years_exp = self._extract_experience(sections.get("experience", ""), cleaned)
        all_skills, detailed_skills = self.skill_svc.extract_profile_skills(sections, cleaned)
        projects = self._extract_projects(sections.get("projects", ""), cleaned)

        extracted_profile = {
            "candidate_name": candidate_name,
            "email": email,
            "phone": phone,
            "education": education,
            "experience": experience,
            "years_of_experience": years_exp,
            "skills": all_skills,
            "detailed_skills": detailed_skills,
            "projects": projects,
            "unrecognized_sections": unrecognized_sections
        }

        # Ingestion Integrity Validation
        integrity_result = self.integrity_svc.validate_integrity(
            raw_text=cleaned,
            sections=sections,
            unrecognized_sections=unrecognized_sections,
            profile=extracted_profile,
            file_type=file_type
        )

        # Calculate Resume Health Breakdown
        health_scores = self._calculate_health_scores(extracted_profile, sections, cleaned)

        resume_id = f"res_{uuid.uuid4().hex[:8]}"

        warnings = list(integrity_result["warnings"])
        if security_audit.get("status") == "blocked":
            warnings.append("Security Alert: Potential prompt-injection directive detected. Downstream LLM execution restricted.")
        elif security_audit.get("status") == "warning":
            warnings.append("Security Notice: Suspicious formatting or invisible characters detected.")

        return {
            "resume_id": resume_id,
            "filename": filename,
            "health_scores": health_scores,
            "extracted_profile": extracted_profile,
            "raw_text": cleaned,
            "extraction_status": integrity_result["status"],
            "warnings": warnings,
            "integrity_report": integrity_result,
            "security_audit": security_audit,
            "message": integrity_result["message"]
        }

    def analyze_job_description(self, text: str, title: str = "Custom Job Opening") -> Dict[str, Any]:
        """
        Parses an arbitrary job description text into structured requirements.
        Detects importance levels from context (required/preferred/optional).
        """
        cleaned = clean_text(text)
        found_skills = self.skill_svc.extract_skills(cleaned)

        # Detect importance from JD text context
        requirements = []
        lower_text = cleaned.lower()

        required_section = self._extract_importance_section(lower_text, ["required", "must have", "requirements", "qualifications"])
        preferred_section = self._extract_importance_section(lower_text, ["preferred", "nice to have", "desired", "bonus"])
        optional_section = self._extract_importance_section(lower_text, ["optional", "plus", "additional"])

        for s in found_skills:
            skill_lower = s["name"].lower()
            if required_section and skill_lower in required_section:
                importance = "critical"
            elif preferred_section and skill_lower in preferred_section:
                importance = "preferred"
            elif optional_section and skill_lower in optional_section:
                importance = "optional"
            else:
                importance = "critical" if s["category"] in ["languages", "databases", "practices"] else "recommended"

            requirements.append({
                "name": s["name"],
                "importance": importance,
                "category": s["category"]
            })

        if not requirements:
            logger.warning(f"No skills detected in job description: '{title}'")

        # Extract lines for responsibilities
        lines = [l.strip('•-* ') for l in cleaned.split('\n') if len(l.strip()) > 20]
        responsibilities = lines[:6] if lines else []

        experience_level = self._detect_experience_level(lower_text)

        return {
            "id": f"job_{uuid.uuid4().hex[:8]}",
            "title": title,
            "department": "Engineering",
            "location": "Remote / Flexible",
            "experience_level": experience_level,
            "description": cleaned[:400] + "..." if len(cleaned) > 400 else cleaned,
            "requirements": requirements,
            "education_requirement": self._detect_education_requirement(lower_text),
            "responsibilities": responsibilities
        }

    def _extract_importance_section(self, text: str, keywords: List[str]) -> str:
        """Extracts a section of text associated with importance keywords."""
        for kw in keywords:
            pattern = rf'(?:{re.escape(kw)})\s*[:\-]?\s*(.*?)(?:\n\n|\Z)'
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).lower()
        return ""

    def _detect_experience_level(self, text: str) -> str:
        """Detects experience level from JD text."""
        if any(w in text for w in ["senior", "lead", "principal", "staff", "7+", "8+", "10+"]):
            return "Senior (5+ years)"
        elif any(w in text for w in ["mid-level", "mid level", "3+", "4+", "5+"]):
            return "Mid-Level (3-5 years)"
        elif any(w in text for w in ["junior", "entry", "0-2", "1-2", "1+", "2+"]):
            return "Entry to Mid (1-3 years)"
        elif any(w in text for w in ["intern", "internship", "co-op"]):
            return "Intern / Entry"
        return "Not specified"

    def _detect_education_requirement(self, text: str) -> str:
        """Detects education requirement from JD text."""
        if any(w in text for w in ["master", "m.s.", "m.tech", "phd", "doctorate"]):
            return "Master's degree or higher in Computer Science or related field"
        elif any(w in text for w in ["bachelor", "b.s.", "b.tech", "b.e.", "degree"]):
            return "Bachelor's degree in Computer Science or related field"
        return "Not specified"

    def _extract_name(self, raw_text: str, header_text: str = "") -> str:
        """Extracts candidate name from header or top lines. Returns 'Candidate' if not detected."""
        source = header_text if header_text.strip() else raw_text
        lines = [l.strip() for l in source.split('\n') if l.strip()]
        for line in lines[:4]:
            # Names typically have <= 5 words, no emails, URLs, or section markers
            if (len(line) < 50
                and not any(c in line.lower() for c in ["@", "http", "resume", "summary", "curriculum", "vitae", "linkedin", "github", "phone"])
                and not re.search(r'\d{3}', line)
                and 1 <= len(line.split()) <= 5):
                return line
        return "Candidate"

    def _extract_contact(self, raw_text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extracts email and phone from resume text. Returns None if not found."""
        email_match = re.search(r'[\w\.\-\+]+@[\w\.-]+\.\w+', raw_text)
        phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', raw_text)

        email = email_match.group(0) if email_match else None
        phone = phone_match.group(0) if phone_match else None
        return email, phone

    def _extract_education(self, edu_text: str, raw_text: str) -> List[str]:
        """Extracts education entries from education section. Returns empty list if none found."""
        if not edu_text or not edu_text.strip():
            return []
        lines = [l.strip('•-* \t') for l in edu_text.split('\n') if l.strip()]
        edu_entries = []
        for line in lines:
            if any(term in line.lower() for term in [
                "bachelor", "b.tech", "b.e.", "b.s.", "b.sc",
                "master", "m.tech", "m.s.", "m.sc", "mba",
                "phd", "doctorate", "diploma",
                "university", "college", "institute",
                "gpa", "degree", "graduated", "high school"
            ]):
                edu_entries.append(line)
        return edu_entries[:4]

    def _extract_experience(self, exp_text: str, raw_text: str) -> Tuple[List[str], float]:
        """Extracts experience entries and estimates years from experience section. Returns empty list and 0.0 if none found."""
        if not exp_text or not exp_text.strip():
            return [], 0.0
        lines = [l.strip('•-* \t') for l in exp_text.split('\n') if len(l.strip()) > 15]

        exp_entries = []
        for line in lines:
            if any(verb in line.lower() for verb in [
                "developed", "architected", "engineered", "led", "managed",
                "built", "implemented", "optimized", "designed", "intern",
                "deployed", "created", "maintained", "integrated", "launched",
                "improved", "automated", "refactored", "migrated", "scaled",
                "spearheaded", "collaborated", "contributed", "established",
                "reduced", "increased", "delivered", "oversaw", "coordinated"
            ]):
                exp_entries.append(line)

        # Estimate years of experience from year mentions
        years = 0.0
        year_matches = re.findall(r'\b(20\d\d)\b', raw_text)
        if len(year_matches) >= 2:
            try:
                yrs = sorted([int(y) for y in year_matches])
                diff = yrs[-1] - yrs[0]
                if 0 < diff <= 30:
                    years = float(diff)
            except Exception:
                pass

        explicit_years = re.search(r'(\d+)\+?\s*years?\s*(?:of\s+)?(?:experience|exp)', raw_text, re.IGNORECASE)
        if explicit_years:
            try:
                stated = float(explicit_years.group(1))
                years = max(years, stated)
            except ValueError:
                pass

        return exp_entries[:8], years

    def _extract_projects(self, proj_text: str, raw_text: str) -> List[Dict[str, Any]]:
        """
        Extracts projects, cleanly separating project titles, technologies, and bullet deliverables.
        Ensures each project's evidence and technologies remain bound to that entry.
        Never splits bullet points into standalone projects.
        """
        projects = []
        if not proj_text or not proj_text.strip():
            return projects

        lines = [l.strip() for l in proj_text.split('\n') if l.strip()]
        current_project = None

        for line in lines:
            is_bullet = line.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')) or bool(re.match(r'^\d+[\.\)]\s+', line))
            clean_line = re.sub(r'^(?:[•\-*]|\d+[\.\)])\s*', '', line).strip()

            # Check if this line is an inline tech specification (e.g., 'Technology details: ...', 'Technologies: ...')
            tech_field_match = re.match(
                r'^(?:technologies|technology\s+details|tech\s+stack|tools|tools\s+used)\s*[:\-]\s*(.*)$',
                clean_line,
                re.IGNORECASE
            )
            if tech_field_match and current_project:
                tech_str = tech_field_match.group(1)
                found_skills = self.skill_svc.extract_skills(tech_str)
                for s in found_skills:
                    if s["name"] not in current_project["technologies"]:
                        current_project["technologies"].append(s["name"])
                current_project["evidence"].append(clean_line)
                continue

            # Check if this line is a new project title
            # Criteria: Not a bullet, reasonable length (< 120 chars), not a URL
            if not is_bullet and len(clean_line) < 120 and not re.match(r'^(?:https?://|github\.com|www\.)', clean_line, re.IGNORECASE):
                # Save previous project if it has valid contents
                if current_project and (current_project["evidence"] or current_project["technologies"] or len(current_project["title"]) > 5):
                    projects.append(current_project)

                title = clean_line
                techs = []

                # Extract technologies in parentheses e.g. "Platform (React, Node.js)"
                paren_match = re.search(r'\((.*?)\)', clean_line)
                if paren_match:
                    tech_str = paren_match.group(1)
                    for s in self.skill_svc.extract_skills(tech_str):
                        techs.append(s["name"])
                    title = re.sub(r'\(.*?\)', '', clean_line).strip()
                else:
                    # Extract skills directly mentioned in title
                    for s in self.skill_svc.extract_skills(clean_line):
                        techs.append(s["name"])

                current_project = {
                    "title": title,
                    "technologies": techs,
                    "evidence": [],
                    "inferred_skills": []
                }
            elif current_project:
                # Evidence bullet point or deliverable line
                if len(clean_line) > 3:
                    current_project["evidence"].append(clean_line)
                    # Extract skills mentioned in the bullet point
                    for s in self.skill_svc.extract_skills(clean_line):
                        if s["name"] not in current_project["technologies"]:
                            current_project["technologies"].append(s["name"])

        # Append last project
        if current_project and (current_project["evidence"] or current_project["technologies"] or len(current_project["title"]) > 5):
            projects.append(current_project)

        # Populate inferred skills based on evidence and technologies
        for p in projects:
            if not p.get("inferred_skills"):
                inferred = set()
                for tech in p.get("technologies", []):
                    related = self.skill_svc.get_related_skills(tech)
                    inferred.update(related)
                p["inferred_skills"] = [s for s in inferred if s not in p.get("technologies", [])][:3]

        return projects

    def _calculate_health_scores(
        self,
        profile: Dict[str, Any],
        sections: Dict[str, str],
        raw_text: str
    ) -> Dict[str, int]:
        """
        Calculates dynamic Resume Health scores based on actual content.
        No hardcoded defaults.
        """
        from config import HEALTH_WEIGHTS, RESUME_HEALTH_SCORING

        cq_cfg = RESUME_HEALTH_SCORING["content_quality"]
        ats_cfg = RESUME_HEALTH_SCORING["ats_readability"]

        # 1. Skills Coverage
        skills_count = len(profile.get("skills", []))
        if skills_count == 0:
            skills_coverage = 20
        elif skills_count <= 3:
            skills_coverage = 40
        elif skills_count <= 6:
            skills_coverage = 55
        elif skills_count <= 10:
            skills_coverage = 70
        elif skills_count <= 15:
            skills_coverage = 82
        else:
            skills_coverage = min(96, 82 + (skills_count - 15) * 2)

        # 2. Content Quality (Action verbs, metrics, structure)
        action_verb_count = len(re.findall(
            r'\b(developed|engineered|architected|built|designed|optimized|led|delivered|'
            r'implemented|created|deployed|managed|automated|reduced|increased|improved|'
            r'spearheaded|launched|scaled|migrated|refactored)\b',
            raw_text, re.IGNORECASE
        ))
        metric_count = len(re.findall(r'[\d]+%|\$[\d]+|\b\d+\+\b|\b\d+x\b', raw_text))

        if action_verb_count == 0 and metric_count == 0:
            content_quality = cq_cfg["zero_score"]
        else:
            calculated = (action_verb_count * cq_cfg["action_verb_weight"] +
                          metric_count * cq_cfg["metric_weight"] +
                          cq_cfg["base_score"])
            content_quality = min(cq_cfg["max_score"], max(cq_cfg["min_score"], int(calculated)))

        # 3. Experience Clarity
        exp_entries = len(profile.get("experience", []))
        if exp_entries == 0:
            experience_clarity = 20
        elif exp_entries <= 2:
            experience_clarity = 55
        elif exp_entries <= 4:
            experience_clarity = 72
        else:
            experience_clarity = min(95, 72 + (exp_entries - 4) * 5)

        # 4. Project Strength
        proj_entries = len(profile.get("projects", []))
        if proj_entries == 0:
            project_strength = 20
        elif proj_entries == 1:
            project_strength = 55
        elif proj_entries == 2:
            project_strength = 75
        else:
            project_strength = min(96, 75 + (proj_entries - 2) * 8)

        # 5. ATS Readability
        detected_sections = sum(1 for s in ["skills", "experience", "education", "projects"]
                                if sections.get(s, "").strip())
        if detected_sections >= 3:
            ats_readability = ats_cfg["section_3_plus"]
        elif detected_sections == 2:
            ats_readability = ats_cfg["section_2"]
        elif detected_sections == 1:
            ats_readability = ats_cfg["section_1"]
        else:
            ats_readability = ats_cfg["section_0"]

        has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text))
        has_phone = bool(re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', raw_text))
        if has_email:
            ats_readability = min(ats_cfg["max_score"], ats_readability + ats_cfg["email_bonus"])
        if has_phone:
            ats_readability = min(ats_cfg["max_score"], ats_readability + ats_cfg["phone_bonus"])

        # Overall Weighted Health
        overall = int(
            (content_quality * HEALTH_WEIGHTS["content_quality"]) +
            (skills_coverage * HEALTH_WEIGHTS["skills_coverage"]) +
            (experience_clarity * HEALTH_WEIGHTS["experience_clarity"]) +
            (project_strength * HEALTH_WEIGHTS["project_strength"]) +
            (ats_readability * HEALTH_WEIGHTS["ats_readability"])
        )
        overall = min(99, max(10, overall))

        return {
            "overall": overall,
            "content_quality": content_quality,
            "skills_coverage": skills_coverage,
            "experience_clarity": experience_clarity,
            "project_strength": project_strength,
            "ats_readability": ats_readability
        }


# Singleton instance
ai_service = AIService()
