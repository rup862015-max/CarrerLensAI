"""
Skill Extraction & Taxonomy Service for CareerLens AI
Extracts skills, identifies taxonomy categories, and distinguishes explicit vs inferred skills.
"""

import json
import os
import re
from typing import Dict, List, Set, Any, Tuple, Optional

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
                    "related_languages": skill.get("related_languages", []),
                    "aliases": skill.get("aliases", [])
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

    def normalize_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Maps any alias or variant to its canonical taxonomy skill definition."""
        if not skill_name:
            return None
        lower = skill_name.strip().lower()
        return self.skill_lookup.get(lower)

    def normalize_skill_name(self, skill_name: str) -> str:
        """Returns the canonical name if found in taxonomy, otherwise trimmed original name."""
        info = self.normalize_skill(skill_name)
        return info["name"] if info else skill_name.strip()

    def extract_profile_skills(self, sections: Dict[str, str], raw_text: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Extracts skills from resume sections and separates explicit from inferred skills.
        Tracks evidence source locations for each skill.
        Returns:
            - all_skill_names (List[str])
            - detailed_skills (List[Dict[str, Any]])
        """
        skills_sec = sections.get("skills", "")
        projects_sec = sections.get("projects", "")
        exp_sec = sections.get("experience", "")

        skills_found_in_skills_sec = {s["name"] for s in self.extract_skills(skills_sec)}
        project_skills = {s["name"] for s in self.extract_skills(projects_sec)}
        exp_skills = {s["name"] for s in self.extract_skills(exp_sec)}
        all_found = {s["name"]: s for s in self.extract_skills(raw_text)}

        # Extract explicit skill tokens from the skills section (lines, commas, bullets, pipes)
        if skills_sec:
            raw_tokens = re.split(r'[,|•\n\t;*]', skills_sec)
            for tok in raw_tokens:
                clean_tok = re.sub(r'^[•\-*\s]+|[•\-*\s]+$', '', tok).strip()
                # Exclude long sentences, punctuation, or generic stopwords
                if 2 <= len(clean_tok) <= 35 and not re.match(r'^(and|or|the|with|in|for|to|of|etc|proficient|expert|familiar)\.?$', clean_tok, re.I):
                    norm = self.normalize_skill(clean_tok)
                    canonical_name = norm["name"] if norm else clean_tok.title()
                    if canonical_name not in all_found:
                        all_found[canonical_name] = {
                            "name": canonical_name,
                            "category": norm["category"] if norm else "domain_skills",
                            "domain": norm["domain"] if norm else "Domain Skill",
                            "aliases": []
                        }
                        skills_found_in_skills_sec.add(canonical_name)

        # Explicit skills are those directly written in the resume document
        explicit_skills = skills_found_in_skills_sec.union(project_skills).union(exp_skills)

        detailed = []
        for name, info in all_found.items():
            sources = []
            if name in skills_found_in_skills_sec:
                sources.append("Skills section")
            if name in project_skills:
                sources.append("Projects")
            if name in exp_skills:
                sources.append("Professional Experience")
            if not sources:
                sources.append("Resume Text")

            is_explicit = name in explicit_skills
            has_contextual_evidence = (name in project_skills) or (name in exp_skills)

            detailed.append({
                "name": name,
                "category": info["category"],
                "domain": info["domain"],
                "skill_type": "explicit" if is_explicit else "inferred",
                "in_skills_section": name in skills_found_in_skills_sec,
                "in_projects": name in project_skills,
                "in_experience": name in exp_skills,
                "has_contextual_evidence": has_contextual_evidence,
                "evidence_sources": sources
            })

        all_names = sorted(list(all_found.keys()))
        return all_names, detailed

    def get_related_skills(self, skill_name: str) -> List[str]:
        """Returns related taxonomy skills (e.g., React -> TypeScript, JavaScript)."""
        lower = skill_name.lower().strip()
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

    def get_explicit_prerequisites(self, skill_name: str) -> List[str]:
        """
        Returns only genuine, explicit technical prerequisites supported by the taxonomy.
        Does NOT treat general related skills as mandatory prerequisites.
        
        Sources:
        1. Framework 'parent' (e.g., Next.js requires React, Express requires Node.js, Redux requires React).
        2. Framework foundational 'related_languages' (e.g., FastAPI requires Python, Spring Boot requires Java).
        3. Core orchestration/system foundations (e.g., Kubernetes requires Docker containerization).
        """
        lower = skill_name.lower().strip()
        info = self.skill_lookup.get(lower)
        if not info:
            return []

        prereqs = []
        seen = set()

        # 1. Check parent technology (e.g., Next.js -> React)
        parent_id = info.get("parent")
        if parent_id:
            parent_info = self.skill_lookup.get(parent_id.lower())
            if parent_info and parent_info["name"].lower() != lower:
                prereqs.append(parent_info["name"])
                seen.add(parent_info["name"].lower())

        # 2. Check foundational language requirement
        rel_langs = info.get("related_languages", [])
        if rel_langs:
            # First language is the primary foundational language
            primary_lang_id = rel_langs[0]
            lang_info = self.skill_lookup.get(primary_lang_id.lower())
            if lang_info and lang_info["name"].lower() != lower and lang_info["name"].lower() not in seen:
                prereqs.append(lang_info["name"])
                seen.add(lang_info["name"].lower())

        # 3. Explicit architectural foundations from taxonomy
        skill_id = info["id"].lower()
        if skill_id == "kubernetes":
            docker_info = self.skill_lookup.get("docker")
            if docker_info and "docker" not in seen:
                prereqs.append(docker_info["name"])
                seen.add("docker")
        elif skill_id == "langchain":
            llm_info = self.skill_lookup.get("llm")
            if llm_info and "llm" not in seen:
                prereqs.append(llm_info["name"])
                seen.add("llm")
        elif skill_id in ("deep_learning", "deeplearning"):
            ml_info = self.skill_lookup.get("machine_learning")
            if ml_info and "machine_learning" not in seen:
                prereqs.append(ml_info["name"])
                seen.add("machine_learning")

        return prereqs

    def get_helpful_related_skills(self, skill_name: str) -> List[str]:
        """
        Returns related taxonomy skills that are helpful companions,
        excluding self and explicit prerequisites.
        """
        all_related = self.get_related_skills(skill_name)
        prereqs_lower = set(p.lower() for p in self.get_explicit_prerequisites(skill_name))
        self_lower = skill_name.lower().strip()

        return [
            r for r in all_related 
            if r.lower() != self_lower and r.lower() not in prereqs_lower
        ]


# Singleton instance
skill_service = SkillService()
