"""
Career Intelligence Service for CareerLens AI
Implements:
- What-If Career Simulator (re-runs matching with hypothetical skills)
- Career Path Analysis (compare against multiple roles)
- Learning Roadmap Generation (from skill gaps)
- Project Recommendations (from missing skills)

All results are dynamically computed — no hardcoded outputs.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional
from services.skill_service import skill_service
from services.matching_service import matching_service

from config import (
    HYPOTHETICAL_SKILL_CREDIT, 
    MATCHING_WEIGHTS, 
    REQUIREMENT_STATUSES,
    ROADMAP_IMPORTANCE_SCORES,
    ROADMAP_EVIDENCE_STATUS_WEIGHTS,
    ROADMAP_STEP_STATUSES
)

logger = logging.getLogger("careerlens.career")


class CareerService:
    def __init__(self):
        self.skill_svc = skill_service
        self.match_svc = matching_service

    def simulate_what_if(
        self,
        resume_profile: Dict[str, Any],
        raw_resume_text: str,
        job_data: Dict[str, Any],
        added_skills: List[str],
        original_match: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Career What-If Simulator.
        Evaluates the impact of hypothetical skill additions against target job requirements
        using the genuine matching engine and centralized scoring configuration.

        Hypothetical skills receive simulation credit (80% by default) toward requirement matching
        without fabricating project or professional experience evidence, and without altering
        the candidate's original resume or stored match history.
        """
        simulation_id = f"sim_{uuid.uuid4().hex[:8]}"

        # 1. Normalize and evaluate hypothetical skills
        validated_hypo_skills = []
        hypo_skill_evals = []
        seen_skills = set()

        for s in added_skills:
            clean_s = s.strip()
            if not clean_s or clean_s.lower() in seen_skills:
                continue
            seen_skills.add(clean_s.lower())

            norm_info = self.skill_svc.normalize_skill(clean_s)
            canonical = norm_info["name"] if norm_info else clean_s
            is_recognized = norm_info is not None
            validated_hypo_skills.append(canonical)

            hypo_skill_evals.append({
                "skill": clean_s,
                "canonical_name": canonical,
                "is_recognized": is_recognized,
                "status": "recognized" if is_recognized else "custom_unverified",
                "note": (
                    f"Recognized taxonomy skill in {norm_info['category']}" 
                    if is_recognized else 
                    "Custom skill exploration (not present in standard taxonomy; evaluated for direct requirement alignment without verified evidence)"
                ),
                "matched_requirements": []
            })

        # 2. Run baseline match (using genuine matching engine and unmodified profile/text)
        if not original_match:
            baseline_match = self.match_svc.match_resume_to_job(
                resume_profile=resume_profile,
                raw_resume_text=raw_resume_text,
                job_data=job_data
            )
        else:
            baseline_match = original_match

        # 3. Run simulated match (using genuine matching engine with hypothetical_skills parameter)
        # Unmodified profile and text are passed so that experience, education, and project
        # scores remain grounded in actual verified evidence.
        simulated_match = self.match_svc.match_resume_to_job(
            resume_profile=resume_profile,
            raw_resume_text=raw_resume_text,
            job_data=job_data,
            hypothetical_skills=validated_hypo_skills
        )

        # 4. Requirement-level delta analysis
        job_requirements = job_data.get("requirements", [])
        
        baseline_req_map = {}
        for m in baseline_match.get("matched_requirements", []):
            baseline_req_map[m["requirement"].lower().strip()] = {
                "status": m.get("status", REQUIREMENT_STATUSES["MATCHED"]),
                "confidence": m.get("confidence", 0.85),
                "evidence_type": "verified_resume",
                "resume_evidence": m.get("resume_evidence", ""),
                "scoring_contribution": m.get("scoring_contribution", ""),
                "uncertainty_note": m.get("uncertainty_note", "")
            }
        for m in baseline_match.get("missing_requirements", []):
            baseline_req_map[m["requirement"].lower().strip()] = {
                "status": REQUIREMENT_STATUSES["MISSING"],
                "confidence": 0.0,
                "evidence_type": "none",
                "resume_evidence": m.get("resume_evidence", "No supporting evidence found"),
                "scoring_contribution": m.get("scoring_contribution", "0 pts (missing requirement)"),
                "uncertainty_note": "Requirement completely missing from candidate resume."
            }

        sim_req_map = {}
        for m in simulated_match.get("matched_requirements", []):
            sim_status = m.get("status", REQUIREMENT_STATUSES["MATCHED"])
            ev_type = "hypothetical_skill" if sim_status == REQUIREMENT_STATUSES["HYPOTHETICAL"] else "verified_resume"
            sim_req_map[m["requirement"].lower().strip()] = {
                "status": sim_status,
                "confidence": m.get("confidence", 0.70 if sim_status == REQUIREMENT_STATUSES["HYPOTHETICAL"] else 0.85),
                "evidence_type": ev_type,
                "resume_evidence": m.get("resume_evidence", ""),
                "scoring_contribution": m.get("scoring_contribution", ""),
                "uncertainty_note": m.get("uncertainty_note", "")
            }
        for m in simulated_match.get("missing_requirements", []):
            sim_req_map[m["requirement"].lower().strip()] = {
                "status": REQUIREMENT_STATUSES["MISSING"],
                "confidence": 0.0,
                "evidence_type": "none",
                "resume_evidence": m.get("resume_evidence", "No supporting evidence found"),
                "scoring_contribution": m.get("scoring_contribution", "0 pts (missing requirement)"),
                "uncertainty_note": "Requirement remains missing after simulation."
            }

        requirement_deltas = []
        for req in job_requirements:
            req_name = req.get("name", "")
            req_key = req_name.lower().strip()
            base_info = baseline_req_map.get(req_key, {
                "status": REQUIREMENT_STATUSES["MISSING"],
                "confidence": 0.0,
                "evidence_type": "none",
                "scoring_contribution": "0 pts",
                "uncertainty_note": ""
            })
            sim_info = sim_req_map.get(req_key, {
                "status": REQUIREMENT_STATUSES["MISSING"],
                "confidence": 0.0,
                "evidence_type": "none",
                "scoring_contribution": "0 pts",
                "uncertainty_note": ""
            })

            status_changed = base_info["status"] != sim_info["status"]
            contributing_skill = None

            if status_changed and sim_info["status"] == REQUIREMENT_STATUSES["HYPOTHETICAL"]:
                # Match against added hypothetical skills or taxonomy relatives
                for hs in validated_hypo_skills:
                    if hs.lower() == req_key or hs.lower() in req_key or req_key in hs.lower():
                        contributing_skill = hs
                        break
                    related = self.skill_svc.get_related_skills(req_name)
                    if any(hs.lower() == r.lower() for r in related):
                        contributing_skill = hs
                        break
                if not contributing_skill and validated_hypo_skills:
                    contributing_skill = validated_hypo_skills[0]

            scoring_rule = (
                f"Baseline: {base_info['status']} ({base_info['confidence']*100:.0f}% conf). "
                f"Simulated: {sim_info['status']} ({sim_info['confidence']*100:.0f}% conf) — "
                + (f"Earned {int(HYPOTHETICAL_SKILL_CREDIT * 100)}% credit under simulation policy via hypothetical '{contributing_skill}'."
                   if status_changed else "Scoring weight unchanged.")
            )

            requirement_deltas.append({
                "requirement": req_name,
                "importance": req.get("importance", "recommended"),
                "category": req.get("category", "general"),
                "baseline_status": base_info["status"],
                "simulated_status": sim_info["status"],
                "status_changed": status_changed,
                "evidence_type": sim_info["evidence_type"],
                "baseline_confidence": base_info["confidence"],
                "simulated_confidence": sim_info["confidence"],
                "scoring_rule": scoring_rule,
                "uncertainty_note": sim_info["uncertainty_note"] or base_info["uncertainty_note"],
                "contributing_skill": contributing_skill
            })

        # Track matched requirements per hypothetical skill
        for h_eval in hypo_skill_evals:
            matched_names = [
                r["requirement"] for r in requirement_deltas 
                if (r.get("contributing_skill") or "").lower() == h_eval["canonical_name"].lower()
            ]
            h_eval["matched_requirements"] = matched_names
            if matched_names:
                h_eval["impact"] = f"Addresses {len(matched_names)} requirement(s): {', '.join(matched_names)}"
            else:
                h_eval["impact"] = "No direct or taxonomy requirement match for this role (0 score change)"

        # 5. Compute Deltas & Subscores
        score_delta = simulated_match["overall_score"] - baseline_match["overall_score"]
        skill_delta = simulated_match["skill_match"] - baseline_match["skill_match"]

        subscore_deltas = {
            "overall": {
                "baseline": baseline_match["overall_score"],
                "simulated": simulated_match["overall_score"],
                "delta": score_delta
            },
            "skill_match": {
                "baseline": baseline_match["skill_match"],
                "simulated": simulated_match["skill_match"],
                "delta": skill_delta
            },
            "experience_match": {
                "baseline": baseline_match["experience_match"],
                "simulated": simulated_match["experience_match"],
                "delta": simulated_match["experience_match"] - baseline_match["experience_match"]
            },
            "education_match": {
                "baseline": baseline_match["education_match"],
                "simulated": simulated_match["education_match"],
                "delta": simulated_match["education_match"] - baseline_match["education_match"]
            },
            "project_relevance": {
                "baseline": baseline_match["project_relevance"],
                "simulated": simulated_match["project_relevance"],
                "delta": simulated_match["project_relevance"] - baseline_match["project_relevance"]
            },
            "semantic_fit": {
                "baseline": baseline_match["semantic_fit"],
                "simulated": simulated_match["semantic_fit"],
                "delta": simulated_match["semantic_fit"] - baseline_match["semantic_fit"]
            }
        }

        # 6. Gaps Analysis
        original_gaps = [g["skill"] for g in baseline_match.get("skill_gaps", [])]
        simulated_gaps = [g["skill"] for g in simulated_match.get("skill_gaps", [])]
        closed_gaps = [s for s in original_gaps if s not in simulated_gaps]
        remaining_gaps = simulated_gaps

        simulation_policy = {
            "hypothetical_skill_credit": HYPOTHETICAL_SKILL_CREDIT,
            "policy_description": (
                f"Hypothetical skills receive {int(HYPOTHETICAL_SKILL_CREDIT * 100)}% credit toward job requirements "
                "to simulate potential capability. Resume evidence (projects and work experience) is never fabricated or bypassed. "
                "Simulations indicate potential alignment only and do not guarantee interview or hiring outcomes."
            ),
            "scoring_weights_reused": True,
            "weights_summary": MATCHING_WEIGHTS
        }

        return {
            "simulation_id": simulation_id,
            "job_title": job_data.get("title", "Target Role"),
            "baseline_score": baseline_match["overall_score"],
            "baseline_grade": baseline_match["match_grade"],
            "simulated_score": simulated_match["overall_score"],
            "simulated_grade": simulated_match["match_grade"],
            "score_delta": score_delta,
            "subscore_deltas": subscore_deltas,
            "requirement_deltas": requirement_deltas,
            "affected_requirements": [r for r in requirement_deltas if r["status_changed"]],
            "closed_gaps": closed_gaps,
            "remaining_gaps": remaining_gaps,
            "hypothetical_skills_evaluated": hypo_skill_evals,
            "simulation_policy": simulation_policy,
            "recommendation": self._generate_sim_recommendation(score_delta, closed_gaps, validated_hypo_skills)
        }

    def _generate_sim_recommendation(self, score_delta: int, closed_gaps: List[str], added_skills: List[str]) -> str:
        """Generate dynamic recommendation based on simulation results."""
        if score_delta >= 15:
            return (f"Adding {', '.join(added_skills)} would significantly improve your match. "
                    f"Consider building a project that demonstrates these skills.")
        elif score_delta >= 5:
            return (f"Learning {', '.join(added_skills)} would moderately improve your alignment. "
                    f"These skills close {len(closed_gaps)} requirement gaps.")
        elif score_delta > 0:
            return (f"Adding {', '.join(added_skills)} provides a small improvement. "
                    f"Consider combining with other missing skills for greater impact.")
        else:
            return (f"Adding {', '.join(added_skills)} does not significantly change your match. "
                    f"Focus on higher-priority gaps for maximum impact.")

    def analyze_career_paths(
        self,
        resume_profile: Dict[str, Any],
        raw_resume_text: str,
        target_roles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Career Path Analysis.
        Compares a candidate against multiple target roles using the actual matching engine.
        Returns ranked paths with gaps and transferable skills.
        """
        paths = []
        for role in target_roles:
            match_result = self.match_svc.match_resume_to_job(
                resume_profile=resume_profile,
                raw_resume_text=raw_resume_text,
                job_data=role
            )

            matched_skills = [m["requirement"] for m in match_result.get("matched_requirements", [])]
            missing_skills = [m["requirement"] for m in match_result.get("missing_requirements", [])]

            # Find transferable skills (candidate skills related to requirements)
            transferable = []
            for ms in missing_skills:
                related = self.skill_svc.get_related_skills(ms)
                candidate_skills_lower = set(s.lower() for s in resume_profile.get("skills", []))
                for r in related:
                    if r.lower() in candidate_skills_lower:
                        transferable.append({
                            "candidate_skill": r,
                            "related_to": ms,
                            "relationship": "taxonomy_related"
                        })

            paths.append({
                "role_title": role.get("title", "Unknown Role"),
                "role_id": role.get("id", ""),
                "overall_score": match_result["overall_score"],
                "match_grade": match_result["match_grade"],
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "transferable_skills": transferable,
                "skill_match": match_result["skill_match"],
                "experience_match": match_result["experience_match"],
                "gap_count": len(missing_skills),
                "readiness": match_result.get("career_preview", {}).get("readiness_level", "Unknown"),
            })

        # Sort by overall score descending
        paths.sort(key=lambda x: x["overall_score"], reverse=True)

        return {
            "analysis_id": f"path_{uuid.uuid4().hex[:8]}",
            "candidate_name": resume_profile.get("candidate_name", "Candidate"),
            "paths": paths,
            "best_fit": paths[0]["role_title"] if paths else "No roles analyzed",
        }

    def generate_learning_roadmap(
        self,
        resume_profile: Any,
        raw_resume_text: str = "",
        job_data: Optional[Dict[str, Any]] = None,
        saved_progress: Optional[Dict[str, str]] = None,
        resume_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Personalized, Dependency-Aware Skill Learning Roadmap Generator.
        
        Evaluates genuine candidate resume evidence against a target job specification
        using the matching engine. Identifies evidence gaps (missing requirements, unverified
        skills section mentions, partial matches), extracts explicit taxonomy prerequisites,
        and produces a topologically sorted, prioritized roadmap with practical exercises
        and resume-building guidance.
        
        Guarantees:
        - Decoupled from matching scores: learning priority does not predict hiring probability.
        - Prerequisite-aware: prerequisites precede dependent skills in learning sequence.
        - Cycle-safe: handles circular dependencies cleanly without crashing.
        - Honest evidence bounds: self-reported progress does not fabricate resume evidence.
        - Zero-gap transparency: returns empty roadmap with clear message if profile meets all requirements.
        """
        # Backward compatibility for legacy callers passing (skill_gaps, candidate_skills)
        if isinstance(resume_profile, list) and (job_data is None or isinstance(job_data, list)):
            return self._legacy_generate_learning_roadmap(resume_profile, raw_resume_text if isinstance(raw_resume_text, list) else [])

        roadmap_id = f"road_{uuid.uuid4().hex[:8]}"
        job_title = job_data.get("title", "Target Role") if job_data else "Target Role"
        job_id = job_data.get("id", "job_custom") if job_data else "job_custom"
        candidate_name = resume_profile.get("candidate_name", "Candidate") if isinstance(resume_profile, dict) else "Candidate"
        saved_progress = saved_progress or {}

        # 1. Run genuine match engine to evaluate requirement evidence status
        match_result = self.match_svc.match_resume_to_job(
            resume_profile=resume_profile,
            raw_resume_text=raw_resume_text,
            job_data=job_data
        )

        # 2. Extract verified candidate skills from resume profile and verified match evidence
        verified_skills_set = set()
        for s in resume_profile.get("skills", []):
            clean_s = s.strip().lower()
            if clean_s:
                verified_skills_set.add(clean_s)
                norm = self.skill_svc.normalize_skill_name(clean_s)
                if norm:
                    verified_skills_set.add(norm.lower().strip())

        # Also extract skills evidenced in projects and experience
        for proj in resume_profile.get("projects", []):
            for t in proj.get("technologies", []):
                clean_t = t.strip().lower()
                if clean_t:
                    verified_skills_set.add(clean_t)
                    norm = self.skill_svc.normalize_skill_name(clean_t)
                    if norm:
                        verified_skills_set.add(norm.lower().strip())

        for m in match_result.get("matched_requirements", []):
            if m.get("status") == REQUIREMENT_STATUSES["MATCHED"] and m.get("match_type") in ("project_evidence", "experience_evidence", "education"):
                req_clean = m.get("requirement", "").strip().lower()
                if req_clean:
                    verified_skills_set.add(req_clean)
                    norm = self.skill_svc.normalize_skill_name(req_clean)
                    if norm:
                        verified_skills_set.add(norm.lower().strip())

        # 3. Collect requirements that need learning or stronger portfolio evidence
        items_to_learn = {}

        # a) Missing requirements
        for req in match_result.get("missing_requirements", []):
            req_name = req.get("requirement", "").strip()
            if not req_name:
                continue
            importance = req.get("importance", "recommended").lower()
            norm_info = self.skill_svc.normalize_skill(req_name)
            canonical = norm_info["name"] if norm_info else req_name
            canonical_key = canonical.lower().strip()

            # Do not recommend if canonical skill is already verified with evidence
            if canonical_key in verified_skills_set:
                continue

            items_to_learn[canonical_key] = {
                "skill": canonical,
                "category": norm_info.get("category", "general") if norm_info else "general",
                "domain": norm_info.get("domain", "General") if norm_info else "General",
                "related_requirement": req_name,
                "importance": importance,
                "evidence_status": "missing",
                "why_it_matters": req.get("reason") or f"Direct {importance} requirement for {job_title} with no evidence found in candidate profile.",
            }

        # b) Unverified and Partial requirements from matched_requirements
        for req in match_result.get("matched_requirements", []):
            status = req.get("status", "")
            req_name = req.get("requirement", "").strip()
            if not req_name:
                continue
            importance = req.get("importance", "recommended").lower()
            norm_info = self.skill_svc.normalize_skill(req_name)
            canonical = norm_info["name"] if norm_info else req_name
            canonical_key = canonical.lower().strip()

            if status == REQUIREMENT_STATUSES["UNVERIFIED"]:
                if canonical_key not in items_to_learn:
                    items_to_learn[canonical_key] = {
                        "skill": canonical,
                        "category": norm_info.get("category", "general") if norm_info else "general",
                        "domain": norm_info.get("domain", "General") if norm_info else "General",
                        "related_requirement": req_name,
                        "importance": importance,
                        "evidence_status": "unverified",
                        "why_it_matters": (
                            f"Listed in resume skills section but lacks verified project deliverables or professional experience evidence. "
                            f"Demonstrating hands-on implementation will strengthen candidacy for {job_title}."
                        ),
                    }
            elif status == REQUIREMENT_STATUSES["PARTIAL"]:
                if canonical_key not in items_to_learn:
                    items_to_learn[canonical_key] = {
                        "skill": canonical,
                        "category": norm_info.get("category", "general") if norm_info else "general",
                        "domain": norm_info.get("domain", "General") if norm_info else "General",
                        "related_requirement": req_name,
                        "importance": importance,
                        "evidence_status": "partial",
                        "why_it_matters": (
                            f"Partially satisfied through related taxonomy concepts, but lacks direct hands-on project evidence for {canonical}."
                        ),
                    }

        # 4. Resolve explicit prerequisites and include missing prerequisites as foundational steps
        prereqs_to_check = list(items_to_learn.keys())
        added_prereq_keys = set()

        while prereqs_to_check:
            current_key = prereqs_to_check.pop(0)
            current_item = items_to_learn[current_key]
            current_skill_name = current_item["skill"]
            
            raw_prereqs = self.skill_svc.get_explicit_prerequisites(current_skill_name)
            
            for p in raw_prereqs:
                p_norm = self.skill_svc.normalize_skill(p)
                p_canonical = p_norm["name"] if p_norm else p
                p_key = p_canonical.lower().strip()

                if p_key in verified_skills_set:
                    # Satisfied by verified resume evidence
                    continue

                if p_key not in items_to_learn:
                    items_to_learn[p_key] = {
                        "skill": p_canonical,
                        "category": p_norm.get("category", "general") if p_norm else "general",
                        "domain": p_norm.get("domain", "General") if p_norm else "General",
                        "related_requirement": f"Prerequisite for {current_skill_name}",
                        "importance": current_item["importance"],
                        "evidence_status": "prerequisite_needed",
                        "why_it_matters": (
                            f"Foundational technical prerequisite required before acquiring {current_skill_name} "
                            f"({current_item['importance']} requirement for {job_title})."
                        ),
                    }
                    if p_key not in added_prereq_keys:
                        added_prereq_keys.add(p_key)
                        prereqs_to_check.append(p_key)

        # Handle zero-gap edge case
        if not items_to_learn:
            return {
                "roadmap_id": roadmap_id,
                "job_title": job_title,
                "job_id": job_id,
                "candidate_name": candidate_name,
                "summary": "All technical requirements for this role are currently satisfied by verified resume evidence. No learning gaps were identified.",
                "phases": [],
                "steps": [],
                "total_steps": 0,
                "completed_steps": 0,
                "in_progress_steps": 0,
                "methodology_notes": "Roadmap evaluated using genuine matching engine. Verified resume evidence fully covers all job requirements."
            }

        # 5. Build Prerequisite Relationships for each step
        for key, item in items_to_learn.items():
            skill_name = item["skill"]
            all_prereqs = self.skill_svc.get_explicit_prerequisites(skill_name)
            satisfied = []
            unmet = []

            for p in all_prereqs:
                p_norm = self.skill_svc.normalize_skill(p)
                p_canonical = p_norm["name"] if p_norm else p
                p_key = p_canonical.lower().strip()

                if p_key in verified_skills_set:
                    satisfied.append(p_canonical)
                elif p_key in items_to_learn:
                    unmet.append(p_canonical)

            item["satisfied_prerequisites"] = satisfied
            item["prerequisites"] = unmet
            item["related_skills"] = self.skill_svc.get_helpful_related_skills(skill_name)

            # Compute priority score
            base_score = ROADMAP_IMPORTANCE_SCORES.get(item["importance"], 60)
            status_weight = ROADMAP_EVIDENCE_STATUS_WEIGHTS.get(item["evidence_status"], 1.0)
            item["priority_score"] = int(base_score * status_weight)

            # Formulate explainable priority reason
            if item["evidence_status"] == "missing":
                item["priority_reason"] = f"Direct {item['importance']} job requirement with no supporting resume evidence."
            elif item["evidence_status"] == "unverified":
                item["priority_reason"] = f"Direct {item['importance']} requirement listed in skills section without project deliverables."
            elif item["evidence_status"] == "partial":
                item["priority_reason"] = f"Partially matched {item['importance']} requirement; dedicated portfolio evidence needed."
            elif item["evidence_status"] == "prerequisite_needed":
                item["priority_reason"] = f"Foundational prerequisite required by downstream role requirements."

        # Elevate prerequisite priority so prerequisites are prioritized at least as high as their dependents
        for key, item in items_to_learn.items():
            for prereq_name in item["prerequisites"]:
                prereq_key = prereq_name.lower().strip()
                if prereq_key in items_to_learn:
                    if items_to_learn[prereq_key]["priority_score"] < item["priority_score"]:
                        items_to_learn[prereq_key]["priority_score"] = item["priority_score"]
                        items_to_learn[prereq_key]["priority_reason"] += f" (Elevated to match dependent {item['skill']})"

        # Assign High / Medium / Low priority tier
        for key, item in items_to_learn.items():
            score = item["priority_score"]
            item["priority"] = "High" if score >= 75 else ("Medium" if score >= 50 else "Low")

        # 6. Topological Sort (Kahn's Algorithm) with Cycle Detection
        in_degree = {}
        dependents = {k: [] for k in items_to_learn}

        for k, item in items_to_learn.items():
            in_degree[k] = len(item["prerequisites"])
            for p_name in item["prerequisites"]:
                p_key = p_name.lower().strip()
                if p_key in dependents:
                    dependents[p_key].append(k)

        # Ready queue: nodes with in_degree == 0, sorted by priority_score descending
        ready_queue = [k for k, deg in in_degree.items() if deg == 0]
        ready_queue.sort(key=lambda k: items_to_learn[k]["priority_score"], reverse=True)

        ordered_keys = []
        cycle_detected = False

        while ready_queue:
            curr_k = ready_queue.pop(0)
            ordered_keys.append(curr_k)

            for dep_k in dependents.get(curr_k, []):
                in_degree[dep_k] -= 1
                if in_degree[dep_k] == 0:
                    ready_queue.append(dep_k)
                    ready_queue.sort(key=lambda k: items_to_learn[k]["priority_score"], reverse=True)

        # Check for cycles
        if len(ordered_keys) < len(items_to_learn):
            cycle_detected = True
            logger.warning("Dependency cycle detected in roadmap skills. Resolving safely via priority order.")
            remaining_keys = [k for k in items_to_learn if k not in ordered_keys]
            remaining_keys.sort(key=lambda k: items_to_learn[k]["priority_score"], reverse=True)
            ordered_keys.extend(remaining_keys)

        # 7. Build Step Objects with Practical Exercises and Progress
        step_objects = []
        completed_count = 0
        in_progress_count = 0

        for idx, k in enumerate(ordered_keys, start=1):
            raw_item = items_to_learn[k]
            skill_name = raw_item["skill"]
            step_id = f"step_{idx:02d}_{skill_name.lower().replace(' ', '_').replace('.', '_')}"

            # Check saved progress
            current_status = saved_progress.get(skill_name.lower(), saved_progress.get(skill_name, "not_started"))
            if current_status not in ROADMAP_STEP_STATUSES.values():
                current_status = "not_started"

            if current_status == "completed":
                completed_count += 1
            elif current_status == "in_progress":
                in_progress_count += 1

            guidance = self._generate_learning_guidance(skill_name, raw_item["category"], raw_item["domain"])

            step_obj = {
                "id": step_id,
                "skill": skill_name,
                "category": raw_item["category"],
                "domain": raw_item["domain"],
                "related_requirement": raw_item["related_requirement"],
                "importance": raw_item["importance"],
                "evidence_status": raw_item["evidence_status"],
                "priority": raw_item["priority"],
                "priority_score": raw_item["priority_score"],
                "priority_reason": raw_item["priority_reason"],
                "prerequisites": raw_item["prerequisites"],
                "satisfied_prerequisites": raw_item["satisfied_prerequisites"],
                "related_skills": raw_item["related_skills"][:5],
                "learning_objective": guidance["learning_objective"],
                "practical_exercise": guidance["practical_exercise"],
                "completion_criteria": guidance["completion_criteria"],
                "resume_evidence_guidance": guidance["resume_evidence_guidance"],
                "status": current_status
            }
            step_objects.append(step_obj)

        # 8. Group into Phases preserving topological order
        phase1_steps = []
        phase2_steps = []
        phase3_steps = []

        for step in step_objects:
            if step["evidence_status"] == "prerequisite_needed" or step["importance"] == "critical":
                phase1_steps.append(step)
            elif step["importance"] == "required":
                phase2_steps.append(step)
            else:
                phase3_steps.append(step)

        phases = []
        phase_num = 1
        if phase1_steps:
            phases.append({
                "phase_number": phase_num,
                "phase_name": "Phase 1: Foundations & Critical Requirements",
                "description": "Essential technical prerequisites and critical job requirements to establish baseline qualification.",
                "skills": phase1_steps
            })
            phase_num += 1

        if phase2_steps:
            phases.append({
                "phase_number": phase_num,
                "phase_name": "Phase 2: Core Role Requirements",
                "description": "Required core competencies directly aligned with standard job responsibilities.",
                "skills": phase2_steps
            })
            phase_num += 1

        if phase3_steps:
            phases.append({
                "phase_number": phase_num,
                "phase_name": "Phase 3: Recommended & Advanced Specializations",
                "description": "Recommended and preferred capabilities that differentiate candidacy and strengthen competitive edge.",
                "skills": phase3_steps
            })

        methodology_notes = (
            "Prerequisite ordering is derived exclusively from explicit parent frameworks and foundational language relationships "
            "in the skill taxonomy. Verified candidate resume evidence is recognized and removed from the active learning sequence. "
            "Self-reported completion of roadmap items tracks personal study progress and does not alter verified resume match scores."
        )
        if cycle_detected:
            methodology_notes += " Notice: A dependency cycle was detected and safely handled using priority-based ordering."

        summary = (
            f"Personalized roadmap containing {len(step_objects)} learning steps across {len(phases)} phases for {job_title}. "
            f"{completed_count} steps completed, {in_progress_count} in progress."
        )

        return {
            "roadmap_id": roadmap_id,
            "job_title": job_title,
            "job_id": job_id,
            "candidate_name": candidate_name,
            "summary": summary,
            "phases": phases,
            "steps": step_objects,
            "total_steps": len(step_objects),
            "completed_steps": completed_count,
            "in_progress_steps": in_progress_count,
            "methodology_notes": methodology_notes
        }

    def _generate_learning_guidance(self, skill_name: str, category: str, domain: str) -> Dict[str, str]:
        """
        Generates concrete, technically reasonable learning objectives, practical portfolio exercises,
        completion criteria, and resume evidence advice based on skill taxonomy and domain.
        No synthetic market data or guaranteed outcomes are fabricated.
        """
        s_lower = skill_name.lower().strip()
        
        # Specific high-demand skills
        if s_lower == "docker":
            return {
                "learning_objective": "Master containerization fundamentals: Dockerfile instructions, multi-stage builds, container networking, and resource constraints.",
                "practical_exercise": "Containerize a multi-service web backend and database using Dockerfile with multi-stage caching, docker-compose.yml, and environment variable configuration.",
                "completion_criteria": "Fully working Docker build producing a lightweight image (<150MB), automated container healthchecks, and non-root user execution.",
                "resume_evidence_guidance": "Containerized [Service Name] microservices using Docker multi-stage builds, reducing image size by 60% and standardizing local developer runtime."
            }
        elif s_lower == "kubernetes":
            return {
                "learning_objective": "Understand cluster architecture, pod lifecycles, Deployments, Services, ConfigMaps, Secrets, and Ingress controllers.",
                "practical_exercise": "Deploy a resilient microservice application to a local Minikube/Kind cluster with horizontal pod autoscaling (HPA), rolling update strategy, and Ingress routing.",
                "completion_criteria": "Working declarative YAML manifests or Helm chart successfully deployed to cluster with automated zero-downtime rolling updates.",
                "resume_evidence_guidance": "Orchestrated container workloads on Kubernetes with custom Deployments, Services, and HPA, ensuring high availability and zero-downtime rollouts."
            }
        elif s_lower == "react":
            return {
                "learning_objective": "Master component lifecycle, hooks (useState, useEffect, useMemo), state management, and optimized rendering.",
                "practical_exercise": "Build an interactive single-page application dashboard featuring dynamic data filtering, responsive layout, and async API integration with custom hooks.",
                "completion_criteria": "Production React app with modular components, type safety, test coverage using React Testing Library, and lighthouse performance score >90.",
                "resume_evidence_guidance": "Developed responsive frontend dashboard in React with reusable modular components and custom hooks, delivering seamless user experience."
            }
        elif s_lower in ("next.js", "nextjs"):
            return {
                "learning_objective": "Master Server-Side Rendering (SSR), Static Site Generation (SSG), React Server Components (RSC), and Next.js App Router.",
                "practical_exercise": "Build a production-grade full-stack web application with Next.js App Router, server actions, route handlers, and SEO optimization.",
                "completion_criteria": "Deployed Next.js application with fast Time to First Byte (TTFB), dynamic server rendering, and zero layout shift.",
                "resume_evidence_guidance": "Architected high-performance full-stack web application using Next.js App Router and Server Components, achieving 98+ PageSpeed rating."
            }
        elif s_lower == "fastapi":
            return {
                "learning_objective": "Master asynchronous Python backend design, Pydantic data validation, dependency injection, and OpenAPI documentation.",
                "practical_exercise": "Build a modular async REST API service with authentication (OAuth2 / JWT), background tasks, rate limiting, and automated Swagger documentation.",
                "completion_criteria": "Async FastAPI service with >85% unit test coverage using pytest-asyncio, structured error handling, and sub-50ms latency.",
                "resume_evidence_guidance": "Engineered high-throughput asynchronous REST API in FastAPI with Pydantic validation and JWT auth, serving 10,000+ daily requests."
            }
        elif s_lower == "python":
            return {
                "learning_objective": "Deepen core Python proficiency: typing, generators, context managers, async I/O, and idiomatic clean code.",
                "practical_exercise": "Develop a robust command-line utility or backend package with typing, rich logging, configuration management, and comprehensive automated test suite.",
                "completion_criteria": "Packaged Python project adhering to PEP 8, full type annotations with mypy passing, and automated test suite.",
                "resume_evidence_guidance": "Built robust Python data ingestion package with type hints and automated testing, reducing pipeline data errors by 40%."
            }
        elif s_lower in ("postgresql", "postgres", "sql"):
            return {
                "learning_objective": "Master relational schema design, query optimization, indexing strategies, transactions, and ACID guarantees.",
                "practical_exercise": "Design a normalized database schema with foreign keys, indexes, complex analytical JOIN queries, and migration scripts.",
                "completion_criteria": "Schema migration scripts with EXPLAIN ANALYZE demonstrating sub-millisecond query execution on indexed datasets.",
                "resume_evidence_guidance": "Designed normalized PostgreSQL schema and optimized complex aggregation queries, improving query latency by 50%."
            }
        elif s_lower in ("aws", "cloud", "azure", "gcp"):
            return {
                "learning_objective": "Understand core cloud primitives: compute (EC2/Lambda), storage (S3), networking (VPC), and IAM security policies.",
                "practical_exercise": "Provision cloud infrastructure for a web service using Terraform or AWS CDK with least-privilege IAM roles and automated deployment.",
                "completion_criteria": "Repeatable Infrastructure as Code (IaC) template deploying a secured web service with SSL and cloud monitoring.",
                "resume_evidence_guidance": "Provisioned and maintained secure cloud infrastructure on AWS using Terraform, automating deployment and ensuring 99.9% availability."
            }

        cat_lower = category.lower()
        dom_lower = domain.lower()
        
        if "backend" in dom_lower or cat_lower in ("databases", "frameworks", "languages"):
            return {
                "learning_objective": f"Develop production proficiency in {skill_name}, focusing on architecture, data processing, and integration patterns.",
                "practical_exercise": f"Build a tested backend module or API integration demonstrating core features, error handling, and database interaction using {skill_name}.",
                "completion_criteria": f"Working codebase with unit tests, structured logging, and clear documentation in a public repository.",
                "resume_evidence_guidance": f"Implemented backend services utilizing {skill_name}, enhancing processing efficiency and system reliability."
            }
        elif "frontend" in dom_lower or cat_lower in ("ui", "design", "frontend"):
            return {
                "learning_objective": f"Master frontend interface development, state management, and user interaction design with {skill_name}.",
                "practical_exercise": f"Create a responsive, accessible user interface feature with interactive controls and state persistence leveraging {skill_name}.",
                "completion_criteria": f"Modular component with unit tests, responsive styling, and zero console errors.",
                "resume_evidence_guidance": f"Developed interactive user interface components using {skill_name}, improving user engagement and responsiveness."
            }
        elif "devops" in dom_lower or "cloud" in dom_lower:
            return {
                "learning_objective": f"Master deployment automation, configuration management, and operational observability with {skill_name}.",
                "practical_exercise": f"Automate build, testing, and deployment pipelines incorporating {skill_name} with health monitoring and audit logging.",
                "completion_criteria": f"Automated pipeline with reproducible deployment scripts and verification tests.",
                "resume_evidence_guidance": f"Automated deployment workflows using {skill_name}, reducing release cycle time and deployment failures."
            }
        elif "data" in dom_lower or "ai" in dom_lower or "ml" in dom_lower:
            return {
                "learning_objective": f"Master data processing pipelines, modeling techniques, and performance evaluation using {skill_name}.",
                "practical_exercise": f"Build an end-to-end data pipeline or analytical model with data validation, exploratory analysis, and visualization using {skill_name}.",
                "completion_criteria": f"Reproducible Jupyter notebook or Python pipeline with data validation benchmarks and documented findings.",
                "resume_evidence_guidance": f"Engineered automated data pipelines using {skill_name}, improving processing throughput and analytical accuracy."
            }
        else:
            return {
                "learning_objective": f"Acquire practical engineering proficiency in {skill_name} aligned with target role responsibilities.",
                "practical_exercise": f"Build a concrete portfolio project or technical proof-of-concept demonstrating {skill_name} applied to realistic problem domains.",
                "completion_criteria": f"Public repository containing functional code, comprehensive README, test suite, and architectural overview.",
                "resume_evidence_guidance": f"Applied {skill_name} to develop [project/feature name], demonstrating hands-on competency and technical execution."
            }

    def _legacy_generate_learning_roadmap(
        self,
        skill_gaps: List[Dict[str, Any]],
        candidate_skills: List[str]
    ) -> Dict[str, Any]:
        """Legacy helper for backwards compatibility."""
        roadmap_id = f"road_{uuid.uuid4().hex[:8]}"
        if not skill_gaps:
            return {
                "roadmap_id": roadmap_id,
                "phases": [],
                "total_skills": 0,
                "message": "No skill gaps identified. Your profile is well-aligned."
            }
        foundation_skills = []
        for g in skill_gaps:
            s_name = g.get("skill", "")
            foundation_skills.append({
                "id": f"step_{s_name}",
                "skill": s_name,
                "category": "general",
                "domain": "General",
                "related_requirement": s_name,
                "importance": "recommended",
                "evidence_status": "missing",
                "priority": g.get("priority", "Medium"),
                "priority_score": 60,
                "priority_reason": "Identified gap",
                "prerequisites": [],
                "satisfied_prerequisites": [],
                "related_skills": [],
                "learning_objective": f"Learn {s_name}",
                "practical_exercise": f"Build a project using {s_name}",
                "completion_criteria": "Working repository",
                "resume_evidence_guidance": f"Add {s_name} project to resume",
                "status": "not_started"
            })
        return {
            "roadmap_id": roadmap_id,
            "job_title": "Target Role",
            "job_id": "job_legacy",
            "candidate_name": "Candidate",
            "summary": f"Legacy roadmap with {len(foundation_skills)} skills.",
            "phases": [{"phase_number": 1, "phase_name": "Core Skills", "description": "Core", "skills": foundation_skills}],
            "steps": foundation_skills,
            "total_steps": len(foundation_skills),
            "completed_steps": 0,
            "in_progress_steps": 0,
            "methodology_notes": "Generated via legacy interface."
        }


# Singleton instance
career_service = CareerService()
