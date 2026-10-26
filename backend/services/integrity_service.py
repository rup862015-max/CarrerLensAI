"""
Ingestion Integrity & Section Preservation Service for CareerLens AI
Provides deterministic integrity checking, source-to-structure reconciliation,
section preservation validation, and content loss detection.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("careerlens.integrity")


class IngestionIntegrityService:
    """
    Validates resume text extraction and structured profile creation.
    Categorizes outcome into:
      - 'success': Complete extraction, high confidence
      - 'warning': Extraction succeeded with minor anomalies or unrecognized sections preserved
      - 'partial': Likely content loss detected (e.g. projects/experience mentioned in source but not structured)
      - 'failed': Empty, unreadable, or invalid content
    """

    def validate_integrity(
        self,
        raw_text: str,
        sections: Dict[str, str],
        unrecognized_sections: Dict[str, str],
        profile: Dict[str, Any],
        file_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Executes comprehensive integrity checks on extracted text and structured profile.
        """
        warnings: List[str] = []
        checks: Dict[str, Any] = {}
        status = "success"

        # 1. Content Meaningfulness Check
        text_len = len(raw_text.strip())
        words = raw_text.split()
        word_count = len(words)

        if text_len < 30 or word_count < 10:
            return {
                "status": "failed",
                "warnings": ["Uploaded document contains insufficient readable text."],
                "details": {
                    "word_count": word_count,
                    "character_count": text_len,
                    "reason": "Document text is too brief to represent a resume."
                }
            }

        checks["meaningful_content"] = {
            "passed": True,
            "character_count": text_len,
            "word_count": word_count
        }

        # 2. Section Coverage & Identification
        identified_canonical = [s for s, content in sections.items() if content and content.strip()]
        preserved_unrecognized = list(unrecognized_sections.keys())
        
        checks["sections_identified"] = {
            "canonical": identified_canonical,
            "unrecognized_preserved": preserved_unrecognized,
            "total_sections": len(identified_canonical) + len(preserved_unrecognized)
        }

        # 3. Source-to-Structure Content Loss Detection: Projects
        # Look for project indicators in raw text
        raw_lower = raw_text.lower()
        has_projects_heading = bool(re.search(
            r'(?:^|\n)\s*(?:technical\s+projects|key\s+projects|academic\s+projects|personal\s+projects|selected\s+projects|recent\s+projects|projects)\b',
            raw_lower
        ))
        proj_count = len(profile.get("projects", []))
        proj_sec_content = sections.get("projects", "").strip()

        if has_projects_heading and proj_count == 0:
            status = "partial"
            msg = "Project section detected in source text, but structured extraction failed to preserve any projects."
            warnings.append(msg)
            checks["projects_integrity"] = {
                "passed": False,
                "heading_in_source": True,
                "extracted_count": 0,
                "section_content_length": len(proj_sec_content)
            }
        elif has_projects_heading and proj_count > 0:
            # Check if extracted projects have meaningful content (title and evidence/tech)
            incomplete_projects = [
                p.get("title", "Untitled") for p in profile.get("projects", [])
                if not p.get("evidence") and not p.get("technologies")
            ]
            if incomplete_projects and len(incomplete_projects) == proj_count:
                status = "partial"
                warnings.append("Extracted projects lack descriptions and technologies. Bullet points may have been lost.")
                checks["projects_integrity"] = {"passed": False, "incomplete_projects": incomplete_projects}
            else:
                checks["projects_integrity"] = {
                    "passed": True,
                    "extracted_count": proj_count,
                    "projects": [p.get("title") for p in profile.get("projects", [])]
                }
        else:
            # No projects in resume: valid state (not a failure)
            checks["projects_integrity"] = {
                "passed": True,
                "heading_in_source": False,
                "extracted_count": 0,
                "note": "No projects section present in source document."
            }

        # 4. Source-to-Structure Content Loss Detection: Experience
        has_experience_heading = bool(re.search(
            r'(?:^|\n)\s*(?:work\s+experience|professional\s+experience|employment\s+history|career\s+history|work\s+history|experience)\b',
            raw_lower
        ))
        exp_count = len(profile.get("experience", []))
        exp_sec_content = sections.get("experience", "").strip()

        if has_experience_heading and exp_count == 0 and len(exp_sec_content) > 30:
            if status != "partial":
                status = "partial"
            warnings.append("Work experience section detected in source text, but structured extraction extracted 0 experience items.")
            checks["experience_integrity"] = {"passed": False, "heading_in_source": True, "extracted_count": 0}
        else:
            checks["experience_integrity"] = {
                "passed": True,
                "heading_in_source": has_experience_heading,
                "extracted_count": exp_count
            }

        # 5. Unrecognized Sections Preservation
        if preserved_unrecognized:
            checks["unrecognized_sections"] = {
                "preserved": True,
                "sections": preserved_unrecognized
            }
            if status == "success":
                # Having unrecognized sections is informative/warning rather than error
                status = "warning"
                sec_list = ", ".join(preserved_unrecognized)
                warnings.append(f"Additional section(s) preserved: {sec_list}.")

        # 6. Candidate Name & Contact Verification
        name = profile.get("candidate_name")
        email = profile.get("email")
        phone = profile.get("phone")
        checks["contact_info"] = {
            "name_detected": bool(name and name != "Candidate"),
            "email_detected": bool(email),
            "phone_detected": bool(phone)
        }

        # 7. Disagreement & Coverage Check
        # Check if total characters in parsed sections cover a reasonable fraction of raw text
        parsed_chars = sum(len(c) for c in sections.values()) + sum(len(c) for c in unrecognized_sections.values())
        coverage_ratio = parsed_chars / max(1, text_len)
        checks["coverage_ratio"] = round(coverage_ratio, 2)

        if coverage_ratio < 0.40 and text_len > 200:
            if status != "partial":
                status = "partial"
            warnings.append("A significant portion of the resume text could not be assigned to known sections. Review extracted profile.")

        # Determine user-friendly summary message
        if status == "success":
            message = "Resume extracted successfully with complete section preservation."
        elif status == "warning":
            message = "Resume extracted successfully with non-standard sections preserved."
        elif status == "partial":
            message = "Some sections may not have been extracted correctly. Review the extracted content before matching."
        else:
            message = "Resume extraction failed or content was unreadable."

        return {
            "status": status,
            "message": message,
            "warnings": warnings,
            "checks": checks,
            "coverage_ratio": round(coverage_ratio, 2),
            "preserved_sections": identified_canonical + preserved_unrecognized
        }


# Singleton instance
integrity_service = IngestionIntegrityService()
