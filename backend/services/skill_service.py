"""
Skill Extraction & Taxonomy Service for CareerLens AI
Extracts skills, identifies taxonomy categories, and distinguishes explicit vs inferred skills.
"""

import json
import os
import re
from typing import Dict, List, Set, Any, Tuple

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TAXONOMY_PATH = os.path.join(DATA_DIR, "skills_taxonomy.json")


class SkillService:
    def __init__(self):
        self.taxonomy = self._load_taxonomy()
        self.skill_lookup = self._build_lookup()
        self.relationships = self.taxonomy.get("taxonomy_relationships", {})

    def _load_taxonomy(self) -> Dict[str, Any]:
        if os.path.exists(TAXONOMY_PATH):
            with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"categories": {}, "taxonomy_relationships": {}}

    def _build_lookup(self) -> Dict[str, Dict[str, Any]]:
        """Maps lowercase skill names and aliases to their canonical definition."""
        lookup = {}
        for category, skill_list in self.taxonomy.get("categories", {}).items():
            for skill in skill_list:
                skill_id = skill["id"]
                canonical_name = skill["name"]
                info = {
                    "id": skill_id,
                    "name": canonical_name,
                    "category": category,
                    "domain": skill.get("domain", "General"),
                    "parent": skill.get("parent"),
                    "related_languages": skill.get("related_languages", [])
                }
                lookup[canonical_name.lower()] = info
                lookup[skill_id.lower()] = info
                for alias in skill.get("aliases", []):
                    lookup[alias.lower()] = info
        return lookup

    def extract_skills(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts all canonical skills found in the text with regex word-boundary matching.
        """
        if not text:
            return []

        lower_text = text.lower()
        found_skills = {}

        # 1. Match against known lookup table
        for phrase, info in self.skill_lookup.items():
            # Escape regex special chars like ++, #, etc.
            if phrase in ["c++", "c#", ".net"]:
                pattern = r'(?:\s|^)' + re.escape(phrase) + r'(?:\s|[,.;:\/\)]|$)'
            else:
                pattern = r'\b' + re.escape(phrase) + r'\b'

            if re.search(pattern, lower_text):
                canonical_name = info["name"]
                if canonical_name not in found_skills:
                    found_skills[canonical_name] = info

        return list(found_skills.values())

    def extract_profile_skills(self, sections: Dict[str, str], raw_text: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Extracts skills from resume sections and separates explicit from inferred skills.
        Returns:
            - all_skill_names (List[str])
            - detailed_skills (List[Dict[str, Any]])
        """
        skills_sec = sections.get("skills", "")
        projects_sec = sections.get("projects", "")
        exp_sec = sections.get("experience", "")

        explicit_skills = {s["name"] for s in self.extract_skills(skills_sec)}
        project_skills = {s["name"] for s in self.extract_skills(projects_sec)}
        exp_skills = {s["name"] for s in self.extract_skills(exp_sec)}
        all_found = {s["name"]: s for s in self.extract_skills(raw_text)}

        # If no dedicated skills section was matched, top skills in exp/projects become explicit
        if not explicit_skills:
            explicit_skills = project_skills.union(exp_skills)

        detailed = []
        for name, info in all_found.items():
            is_explicit = name in explicit_skills
            detailed.append({
                "name": name,
                "category": info["category"],
                "domain": info["domain"],
                "skill_type": "explicit" if is_explicit else "inferred",
                "in_projects": name in project_skills,
                "in_experience": name in exp_skills
            })

        all_names = sorted(list(all_found.keys()))
        return all_names, detailed

    def get_related_skills(self, skill_name: str) -> List[str]:
        """Returns related taxonomy skills (e.g., React -> TypeScript, JavaScript)."""
        lower = skill_name.lower()
        info = self.skill_lookup.get(lower)
        if not info:
            return []
        
        skill_id = info["id"]
        related_ids = self.relationships.get(skill_id, [])
        names = []
        for r_id in related_ids:
            r_info = self.skill_lookup.get(r_id)
            if r_info:
                names.append(r_info["name"])
        return names


# Singleton instance
skill_service = SkillService()
