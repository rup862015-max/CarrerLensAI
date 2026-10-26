"""
Personalized Interview Preparation Service for CareerLens AI (Stage 4)
Generates evidence-grounded interview questions based on actual resume claims,
job requirements, matched skills, and skill gaps.
Evaluates submitted practice answers against explicit, category-tailored rubrics.
"""

import os
import re
import uuid
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

from services.skill_service import skill_service
from services.security_service import security_service
from services.ai_service import ai_service
from services.llm_provider import llm_provider, wrap_untrusted_content, _build_hardened_system_prompt

logger = logging.getLogger("careerlens.interview")

# Required Disclaimers
NON_HIRING_DISCLAIMER = (
    "EVALUATION DISCLAIMER: This feedback is generated for learning and practice purposes only. "
    "It evaluates answer structure, technical depth, and rubric alignment. It does not assess "
    "candidate honesty, personality, intelligence, or overall employability, and should not be used "
    "as an automated hiring decision."
)

SAMPLE_ANSWER_DISCLAIMER_PREFIX = (
    "HYPOTHETICAL ILLUSTRATIVE EXAMPLE ONLY: This sample answer is an AI-generated demonstration "
    "of effective structure and reasoning. It does not represent the candidate's actual experience or background.\n\n"
)


class InterviewService:
    def __init__(self):
        self.skill_svc = skill_service
        self.security_svc = security_service
        self.ai_svc = ai_service

    def _infer_seniority_and_difficulty(
        self,
        resume_profile: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Derives difficulty level and selection rationale from candidate experience and job seniority.
        Difficulty levels: 'entry', 'mid-level', 'senior', 'principal'
        """
        # Determine candidate years of experience
        years_exp = resume_profile.get("years_of_experience")
        if years_exp is None:
            # Estimate from experience entries
            exp_entries = resume_profile.get("experience", [])
            years_exp = max(len(exp_entries) * 1.5, 1.0) if exp_entries else 0.5

        job_title = job_data.get("title", "").lower()
        job_level_raw = str(job_data.get("experience_level", "")).lower()

        is_senior_job = any(w in job_title or w in job_level_raw for w in ["senior", "lead", "staff", "principal", "architect"])
        is_junior_job = any(w in job_title or w in job_level_raw for w in ["junior", "entry", "associate", "intern"])

        if years_exp >= 8 or "principal" in job_title or "staff" in job_title:
            level = "principal"
            rationale = (
                f"Assigned Principal/Lead difficulty based on {years_exp:.1f} years of professional experience "
                f"and strategic architectural requirements for the role."
            )
        elif years_exp >= 5 or is_senior_job:
            level = "senior"
            rationale = (
                f"Assigned Senior difficulty: candidate profile reflects {years_exp:.1f} years of experience, "
                f"aligning with senior-level system design and leadership expectations."
            )
        elif years_exp >= 2 or not is_junior_job:
            level = "mid-level"
            rationale = (
                f"Assigned Mid-Level difficulty: candidate has {years_exp:.1f} years of practical experience, "
                f"matching standard independent engineering responsibilities."
            )
        else:
            level = "entry"
            rationale = (
                f"Assigned Entry-level difficulty matching foundational core competencies and early-career profile "
                f"({years_exp:.1f} years of experience)."
            )

        return level, rationale

    def create_interview_session(
        self,
        resume_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        user_id: str,
        resume_id: Optional[str] = None,
        job_id: Optional[str] = None,
        skill_gaps: Optional[List[Dict[str, Any]]] = None,
        matched_requirements: Optional[List[Dict[str, Any]]] = None,
        categories: Optional[List[str]] = None,
        num_questions: int = 5
    ) -> Dict[str, Any]:
        """
        Creates a personalized interview preparation session using actual resume evidence
        and job requirements. Generates questions across 5 core categories with category-tailored rubrics.
        Handles data limitations by providing clearly labeled general questions where data is sparse.
        """
        session_id = f"int_{uuid.uuid4().hex[:8]}"
        candidate_name = resume_profile.get("candidate_name") or "Candidate"
        job_title = job_data.get("title", "Target Role")
        candidate_skills = resume_profile.get("skills", [])
        projects = resume_profile.get("projects", [])
        experience = resume_profile.get("experience", [])
        job_requirements = job_data.get("requirements", [])

        difficulty_level, difficulty_rationale = self._infer_seniority_and_difficulty(resume_profile, job_data)

        # Track any data limitations
        limitations = []
        if not projects:
            limitations.append("Candidate resume does not list specific verifiable projects")
        if not experience:
            limitations.append("Candidate resume does not list formal work history")
        if not job_requirements:
            limitations.append("Job description does not list itemized skill requirements")

        data_limitation_note = "; ".join(limitations) + ". General questions provided as labeled fallbacks." if limitations else None

        generated_pool: List[Dict[str, Any]] = []

        # ─── Category 1: Project & Experience Discussion ───
        if projects:
            for proj in projects[:2]:
                title = proj.get("title", "Featured Project")
                techs = proj.get("technologies", [])
                tech_str = ", ".join(techs[:2]) if techs else "the chosen technical stack"
                generated_pool.append({
                    "id": f"q_{uuid.uuid4().hex[:8]}",
                    "category": "project",
                    "question_text": (
                        f"In your project '{title}', what was the most significant architectural or technical tradeoff "
                        f"you evaluated when implementing {tech_str}, and what measurable impact did that decision have on system performance or user experience?"
                    ),
                    "related_requirement": techs[0] if techs else None,
                    "difficulty_level": difficulty_level,
                    "difficulty_rationale": difficulty_rationale,
                    "what_interviewer_is_evaluating": (
                        "Technical decision-making, architectural depth, practical trade-off awareness, "
                        "and ability to articulate measurable engineering impact."
                    ),
                    "rubric": [
                        {"name": "Technical Decision-Making & Trade-offs", "description": "Clearly articulates the problem, alternatives considered, and rationale for the chosen solution.", "focus": "core"},
                        {"name": "System Architecture & Depth", "description": "Demonstrates deep understanding of internal components, data flow, or system mechanics.", "focus": "core"},
                        {"name": "Concrete Impact & Evidence", "description": "Provides specific metrics, performance improvements, scale, or business outcomes.", "focus": "secondary"},
                        {"name": "Personal Ownership", "description": "Distinguishes individual engineering contributions from general team activities.", "focus": "secondary"}
                    ],
                    "source_reference": f"Resume Project: '{title}' ({tech_str})",
                    "is_generic_fallback": False,
                })
        else:
            # Labeled fallback project question
            generated_pool.append({
                "id": f"q_{uuid.uuid4().hex[:8]}",
                "category": "project",
                "question_text": (
                    "Walk through a significant software project or complex technical task you contributed to. "
                    "What architectural challenges arose, how did you resolve them, and how did you measure success?"
                ),
                "related_requirement": None,
                "difficulty_level": difficulty_level,
                "difficulty_rationale": difficulty_rationale,
                "what_interviewer_is_evaluating": "Project structure, problem-solving lifecycle, and engineering delivery.",
                "rubric": [
                    {"name": "Problem Scope & Architecture", "description": "Defines project goals, system components, and architectural boundaries.", "focus": "core"},
                    {"name": "Engineering Delivery", "description": "Explains execution steps and technical obstacles overcome.", "focus": "core"},
                    {"name": "Success Metrics", "description": "Measures project impact with concrete qualitative or quantitative results.", "focus": "secondary"}
                ],
                "source_reference": "General Project Delivery (Candidate resume lists no specific projects)",
                "is_generic_fallback": True,
            })

        # ─── Category 2: Technical Knowledge ───
        # Identify skills that are critical/required in the job AND present in the candidate profile
        verified_matched_skills = []
        if matched_requirements:
            for req in matched_requirements:
                skill_n = req.get("requirement") or req.get("name")
                if req.get("status") in ("matched", "partial", "unverified") and skill_n:
                    verified_matched_skills.append(skill_n)

        if not verified_matched_skills and job_requirements:
            for req in job_requirements:
                req_name = req.get("name", "")
                if any(req_name.lower() == s.lower() for s in candidate_skills):
                    verified_matched_skills.append(req_name)

        if not verified_matched_skills and candidate_skills:
            verified_matched_skills = candidate_skills[:2]

        if verified_matched_skills:
            for skill in verified_matched_skills[:2]:
                generated_pool.append({
                    "id": f"q_{uuid.uuid4().hex[:8]}",
                    "category": "technical",
                    "question_text": (
                        f"You list {skill} as a key skill, which is required for this role. "
                        f"Can you explain how you have applied {skill} in a production environment? "
                        f"Walk through how you handle performance bottlenecks, concurrency, or failure recovery using {skill}."
                    ),
                    "related_requirement": skill,
                    "difficulty_level": difficulty_level,
                    "difficulty_rationale": difficulty_rationale,
                    "what_interviewer_is_evaluating": (
                        f"Practical production depth in {skill}, understanding of performance bottlenecks, "
                        f"reliability patterns, and debugging methodology."
                    ),
                    "rubric": [
                        {"name": "Technical Correctness & Precision", "description": f"Accurate explanation of {skill} concepts, core APIs, and mechanisms.", "focus": "core"},
                        {"name": "Production Experience & Edge Cases", "description": "Describes realistic production scenarios, concurrency/scaling challenges, or edge cases.", "focus": "core"},
                        {"name": "Reasoning & Performance Optimization", "description": "Articulates optimization strategies, memory/latency considerations, or profiling tools.", "focus": "secondary"}
                    ],
                    "source_reference": f"Job Requirement & Verified Resume Skill: {skill}",
                    "is_generic_fallback": False,
                })
        else:
            # Labeled fallback technical question
            generated_pool.append({
                "id": f"q_{uuid.uuid4().hex[:8]}",
                "category": "technical",
                "question_text": (
                    f"This position requires solid software engineering foundations for a {job_title}. "
                    f"How do you ensure high code quality, automated test coverage, and performant execution in your primary tech stack?"
                ),
                "related_requirement": None,
                "difficulty_level": difficulty_level,
                "difficulty_rationale": difficulty_rationale,
                "what_interviewer_is_evaluating": "Foundational engineering practices, testing pyramid understanding, and code quality discipline.",
                "rubric": [
                    {"name": "Testing & Verification", "description": "Explains unit, integration, and regression testing practices.", "focus": "core"},
                    {"name": "Code Maintainability", "description": "Applies clean architecture, modularity, and readable design patterns.", "focus": "core"}
                ],
                "source_reference": f"General Technical Practices for {job_title}",
                "is_generic_fallback": True,
            })

        # ─── Category 3: Questions Targeting Unverified Job Requirements (Skill Gaps) ───
        missing_skills = []
        if skill_gaps:
            missing_skills = [g.get("skill") for g in skill_gaps if g.get("skill")]
        elif job_requirements:
            for req in job_requirements:
                req_name = req.get("name", "")
                if not any(req_name.lower() == s.lower() for s in candidate_skills):
                    missing_skills.append(req_name)

        if missing_skills:
            gap_skill = missing_skills[0]
            generated_pool.append({
                "id": f"q_{uuid.uuid4().hex[:8]}",
                "category": "skill-gap",
                "question_text": (
                    f"This role requires experience with {gap_skill}, which is not prominently featured on your resume. "
                    f"How would you leverage your existing technical background to get up to speed with {gap_skill}, "
                    f"and how would you validate your proficiency before deploying code to production?"
                ),
                "related_requirement": gap_skill,
                "difficulty_level": difficulty_level,
                "difficulty_rationale": difficulty_rationale,
                "what_interviewer_is_evaluating": (
                    "Honest self-awareness, learning agility, ability to map transferable concepts, "
                    "and structured ramp-up plan."
                ),
                "rubric": [
                    {"name": "Honest Self-Assessment", "description": "Transparently acknowledges current knowledge level without overstating unearned expertise.", "focus": "core"},
                    {"name": "Transferable Fundamentals", "description": "Identifies related paradigms, languages, or tools from current stack that accelerate learning.", "focus": "core"},
                    {"name": "Actionable Ramp-Up Plan", "description": "Presents a clear, structured learning strategy with concrete projects, documentation, or sandboxes.", "focus": "secondary"}
                ],
                "source_reference": f"Job Requirement (Unverified on Resume): {gap_skill}",
                "is_generic_fallback": False,
            })
        else:
            # Candidate matches all requirements; probe continuous adaptation
            generated_pool.append({
                "id": f"q_{uuid.uuid4().hex[:8]}",
                "category": "skill-gap",
                "question_text": (
                    f"As technologies in the {job_title} space evolve rapidly, describe a time you had to master a "
                    f"completely unfamiliar tool, framework, or paradigm on short notice to deliver a critical project."
                ),
                "related_requirement": None,
                "difficulty_level": difficulty_level,
                "difficulty_rationale": difficulty_rationale,
                "what_interviewer_is_evaluating": "Learning speed, technological curiosity, and adaptability under deadline constraints.",
                "rubric": [
                    {"name": "Learning Strategy", "description": "Demonstrates structured learning methodology under time pressure.", "focus": "core"},
                    {"name": "Execution & Delivery", "description": "Successfully applies newly acquired knowledge to deliver working software.", "focus": "core"}
                ],
                "source_reference": "Continuous Learning & Technology Adaptation",
                "is_generic_fallback": False,
            })

        # ─── Category 4: Behavioral Questions (STAR Method) ───
        if experience:
            first_exp = experience[0]
            role_desc = first_exp if isinstance(first_exp, str) else (first_exp.get("title", "") + " at " + first_exp.get("company", ""))
            generated_pool.append({
                "id": f"q_{uuid.uuid4().hex[:8]}",
                "category": "behavioral",
                "question_text": (
                    f"In your work experience ({role_desc}), tell me about a situation where a project deadline was at risk "
                    f"or requirements abruptly shifted. How did you communicate with stakeholders, prioritize technical tasks, and what was the outcome?"
                ),
                "related_requirement": None,
                "difficulty_level": difficulty_level,
                "difficulty_rationale": difficulty_rationale,
                "what_interviewer_is_evaluating": (
                    "STAR structure (Situation, Task, Action, Result), communication under pressure, "
                    "prioritization, and professional accountability."
                ),
                "rubric": [
                    {"name": "STAR Method Structure", "description": "Covers Situation (15%), Task (15%), Action (50%), and measurable Result (20%).", "focus": "core"},
                    {"name": "Proactive Action & Ownership", "description": "Focuses on personal actions, leadership, and problem-solving rather than passive reaction.", "focus": "core"},
                    {"name": "Interpersonal Communication & Stakeholder Management", "description": "Demonstrates empathetic, clear communication with teammates or non-technical stakeholders.", "focus": "secondary"},
                    {"name": "Reflection & Growth Mindset", "description": "Articulates key takeaways, lessons learned, or improvements applied to future work.", "focus": "secondary"}
                ],
                "source_reference": f"Candidate Work Experience: {role_desc}",
                "is_generic_fallback": False,
            })
        else:
            generated_pool.append({
                "id": f"q_{uuid.uuid4().hex[:8]}",
                "category": "behavioral",
                "question_text": (
                    "Describe a situation where you had to collaborate under ambiguity or resolve a technical disagreement "
                    "with a team member or collaborator. How did you navigate the conversation and what was the result?"
                ),
                "related_requirement": None,
                "difficulty_level": difficulty_level,
                "difficulty_rationale": difficulty_rationale,
                "what_interviewer_is_evaluating": "Interpersonal communication, active listening, conflict resolution, and collaborative outcome.",
                "rubric": [
                    {"name": "STAR Method Structure", "description": "Structured Situation, Task, Action, Result explanation.", "focus": "core"},
                    {"name": "Conflict Resolution & Empathy", "description": "Focuses on constructive resolution, shared technical goals, and active listening.", "focus": "core"}
                ],
                "source_reference": "General Collaboration & Professional Resilience",
                "is_generic_fallback": True,
            })

        # ─── Category 5: Problem-Solving & Scenario-Based Questions ───
        generated_pool.append({
            "id": f"q_{uuid.uuid4().hex[:8]}",
            "category": "problem-solving",
            "question_text": (
                f"Suppose you are tasked with designing a core service for a {job_title} role that must handle sudden traffic "
                f"spikes with low latency and high availability. How do you decompose the architecture, identify potential bottlenecks, "
                f"and handle database or network failures?"
            ),
            "related_requirement": None,
            "difficulty_level": difficulty_level,
            "difficulty_rationale": difficulty_rationale,
            "what_interviewer_is_evaluating": (
                "Architectural decomposition, distributed systems reasoning, failure mode anticipation, "
                "and trade-off balancing."
            ),
            "rubric": [
                {"name": "Problem Decomposition & Scoping", "description": "Clarifies requirements, defines clear service boundaries, and states reasonable assumptions.", "focus": "core"},
                {"name": "System Architecture & Component Design", "description": "Proposes a coherent architecture with appropriate data stores, caching, and communication protocols.", "focus": "core"},
                {"name": "Trade-off & Scaling Analysis", "description": "Evaluates trade-offs (e.g., consistency vs latency, cost vs performance) under scale.", "focus": "core"},
                {"name": "Resilience & Fault Tolerance", "description": "Considers circuit breakers, fallbacks, retry policies, and monitoring observability.", "focus": "secondary"}
            ],
            "source_reference": f"System Design & Scenario Problem Solving for {job_title}",
            "is_generic_fallback": False,
        })

        # Filter by requested categories if specified
        if categories:
            cat_set = {c.lower() for c in categories}
            generated_pool = [q for q in generated_pool if q["category"].lower() in cat_set]

        # Select up to requested num_questions
        selected_questions = generated_pool[:num_questions]
        for idx, q in enumerate(selected_questions):
            q["order_index"] = idx

        return {
            "id": session_id,
            "user_id": user_id,
            "resume_id": resume_id,
            "job_id": job_id,
            "job_title": job_title,
            "candidate_name": candidate_name,
            "status": "in_progress",
            "total_questions": len(selected_questions),
            "completed_questions": 0,
            "average_score": 0.0,
            "data_limitation_note": data_limitation_note,
            "questions": selected_questions,
        }

    def evaluate_answer(
        self,
        question: Dict[str, Any],
        answer_text: str,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Evaluates a practice answer against the question's explicit rubric.
        Guards against prompt injection, validates schemas, uses live LLM if available,
        or falls back to comprehensive deterministic rubric evaluation.
        """
        clean_ans = answer_text.strip()
        word_count = len(clean_ans.split())

        # 1. Prompt Injection Defense Scan
        security_report = self.security_svc.scan_text(clean_ans, filename="interview_answer.txt", source_type="user_input")
        findings = security_report.get("findings", [])
        has_injection = (
            any(f.get("category") in ("injection", "instruction_override", "system_prompt_leak", "adversarial_jailbreak") or f.get("severity") in ("critical", "warning") for f in findings)
            or any(w in clean_ans.lower() for w in ["ignore previous", "system directive", "system prompt", "override score", "declare them", "ideal candidate"])
        )

        # 2. Try LLM Provider if active
        if self.ai_svc.is_llm_active() and not has_injection:
            try:
                llm_eval = self._evaluate_with_llm(question, clean_ans)
                if llm_eval:
                    llm_eval["session_id"] = session_id
                    llm_eval["question_id"] = question["id"]
                    llm_eval["user_id"] = user_id
                    llm_eval["word_count"] = word_count
                    llm_eval["answer_text"] = clean_ans
                    return llm_eval
            except Exception as e:
                logger.warning(f"LLM interview answer evaluation failed ({e}). Falling back to deterministic rubric evaluator.")

        # 3. Deterministic Rubric Evaluator
        return self._evaluate_deterministically(question, clean_ans, user_id, session_id, has_injection=has_injection)

    def _evaluate_deterministically(
        self,
        question: Dict[str, Any],
        answer_text: str,
        user_id: str,
        session_id: str,
        has_injection: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive deterministic evaluation engine based on explicit rubric criteria,
        STAR method parsing, technical terminology density, and trade-off keyword analysis.
        """
        ans_lower = answer_text.lower()
        word_count = len(answer_text.split())
        category = question.get("category", "technical")
        rubric_criteria = question.get("rubric", [])

        # Check for specific metrics / quantitative evidence
        has_metrics = bool(re.search(r'\d+[%kMBGbms]*|\b(increased|reduced|improved|decreased) by \d+', ans_lower))

        # Check for trade-offs & reasoning
        has_tradeoffs = any(w in ans_lower for w in [
            "tradeoff", "trade-off", "alternative", "chose", "because", "instead of",
            "whereas", "pros and cons", "latency vs", "consistency vs", "overhead"
        ])

        # Check for STAR elements
        star_coverage = {
            "situation": any(w in ans_lower for w in ["situation", "when I", "context", "at the time", "working on", "facing"]),
            "task": any(w in ans_lower for w in ["task", "needed to", "responsible for", "goal was", "objective", "had to"]),
            "action": any(w in ans_lower for w in ["implemented", "designed", "built", "decided", "created", "refactored", "led", "investigated", "profiled"]),
            "result": any(w in ans_lower for w in ["result", "outcome", "improved", "reduced", "delivered", "successfully", "impact", "learned"])
        }
        met_star_count = sum(1 for v in star_coverage.values() if v)

        # Evaluate Each Rubric Criterion
        criterion_evaluations: List[Dict[str, Any]] = []
        criterion_scores: List[int] = []

        for crit in rubric_criteria:
            c_name = crit.get("name", "Evaluation Criterion")
            c_lower = c_name.lower()
            focus = crit.get("focus", "core")

            score = 60  # baseline
            rating = "adequate"
            feedback_points = []

            # Behavioral / STAR criterion
            if "star" in c_lower or category == "behavioral":
                if met_star_count >= 3:
                    score += 25
                    rating = "strong"
                    met_parts = [k.capitalize() for k, v in star_coverage.items() if v]
                    feedback_points.append(f"Clear STAR structure demonstrated covering {', '.join(met_parts)}.")
                elif met_star_count == 2:
                    score += 10
                    rating = "adequate"
                    missing_parts = [k.capitalize() for k, v in star_coverage.items() if not v]
                    feedback_points.append(f"Partial STAR structure. Missing explicit focus on: {', '.join(missing_parts)}.")
                else:
                    score -= 15
                    rating = "needs_work"
                    feedback_points.append("Response lacks structured narrative arc. Use Situation -> Task -> Action -> Result.")

            # Decision-Making & Tradeoffs
            elif "trade-off" in c_lower or "decision" in c_lower:
                if has_tradeoffs:
                    score += 25
                    rating = "strong"
                    feedback_points.append("Articulates clear rationale and evaluated alternatives before settling on the solution.")
                else:
                    score -= 15
                    rating = "needs_work"
                    feedback_points.append("Does not clearly discuss alternative solutions or why this approach was preferred.")

            # Concrete Impact & Evidence / Metrics
            elif "impact" in c_lower or "evidence" in c_lower or "metric" in c_lower:
                if has_metrics:
                    score += 25
                    rating = "strong"
                    feedback_points.append("Grounds engineering claims with quantitative metrics or verifiable outcomes.")
                else:
                    score -= 10
                    rating = "needs_work"
                    feedback_points.append("Add measurable outcomes (e.g. % speedup, latency drop, scale supported) to validate impact.")

            # Self-Assessment / Learning (Skill Gap)
            elif "self-assessment" in c_lower or "ramp-up" in c_lower or category == "skill-gap":
                has_learning_plan = any(w in ans_lower for w in ["documentation", "hands-on", "project", "tutorial", "sandbox", "poc", "ramp up", "learning"])
                has_transferable = any(w in ans_lower for w in ["similar to", "familiar with", "transfers from", "experience with", "analogous"])
                if has_learning_plan and has_transferable:
                    score += 30
                    rating = "strong"
                    feedback_points.append("Transparently identifies current boundary and connects adjacent foundational skills to a concrete ramp-up plan.")
                elif has_learning_plan or has_transferable:
                    score += 15
                    rating = "adequate"
                    feedback_points.append("Good initiative shown; specify concrete milestones or timeline for the ramp-up plan.")
                else:
                    score -= 15
                    rating = "needs_work"
                    feedback_points.append("Outline a clear, structured study and prototyping roadmap to bridge the skill gap.")

            # General Technical / Architecture
            else:
                has_tech_depth = len(re.findall(r'\b(API|database|cache|latency|throughput|concurrency|index|transaction|microservice|docker|async|queue|schema)\b', ans_lower)) >= 2
                if has_tech_depth and word_count >= 50:
                    score += 25
                    rating = "strong"
                    feedback_points.append(f"Demonstrates sound technical vocabulary and architectural comprehension relevant to '{c_name}'.")
                elif word_count >= 30:
                    score += 10
                    rating = "adequate"
                    feedback_points.append(f"Addresses basic aspects of '{c_name}'; expand on internal mechanics or failure modes.")
                else:
                    score -= 15
                    rating = "needs_work"
                    feedback_points.append(f"Requires deeper technical explanation for '{c_name}'.")

            # Word count modifiers
            if word_count < 25:
                score = min(score, 50)
                rating = "needs_work"
            elif word_count >= 70:
                score = min(100, score + 5)

            score = max(20, min(100, score))
            criterion_scores.append(score)
            criterion_evaluations.append({
                "criterion": c_name,
                "rating": rating,
                "score": score,
                "feedback": " ".join(feedback_points)
            })

        # Overall Score: Average of criteria
        overall_score = int(round(sum(criterion_scores) / max(len(criterion_scores), 1)))

        # Strengths
        strengths = []
        if word_count >= 50:
            strengths.append(f"Provides a thorough, articulate response ({word_count} words) with substantive technical context.")
        if has_metrics:
            strengths.append("Incorporates concrete numerical indicators or observable business impact.")
        if has_tradeoffs:
            strengths.append("Demonstrates mature engineering judgment by weighing architectural alternatives and tradeoffs.")
        if met_star_count >= 3:
            strengths.append("Maintains disciplined narrative structure across Situation, Task, Action, and Result.")
        if not strengths:
            strengths.append("Directly engages with the core premise of the interview question.")

        # Improvement Areas
        improvements = []
        if not has_metrics:
            improvements.append("Quantify results: include specific scale numbers, latency reductions, error rate drops, or team size.")
        if not has_tradeoffs and category in ("project", "problem-solving"):
            improvements.append("Highlight tradeoffs: explain what alternatives were considered and why the chosen solution was superior.")
        if met_star_count < 3 and category == "behavioral":
            improvements.append("Sharpen STAR method: ensure the 'Action' section clearly highlights YOUR individual contribution.")
        if word_count < 40:
            improvements.append("Elaborate on details: provide a deeper step-by-step technical breakdown.")
        if not improvements:
            improvements.append("Consider detailing a 'lessons learned' or how this solution would scale to 10x traffic.")

        # Missing Concepts
        missing = []
        for ce in criterion_evaluations:
            if ce["rating"] == "needs_work":
                missing.append(ce["criterion"])
        if not missing and not has_metrics:
            missing.append("Quantitative success benchmarks")

        # Suggested Structure
        if category == "behavioral":
            structure = (
                "1. Situation (15%): Set the team context and constraint.\n"
                "2. Task (15%): Define your specific ownership area.\n"
                "3. Action (50%): Walk through your step-by-step technical and interpersonal decisions.\n"
                "4. Result (20%): State measurable outcome and a reflection on what was learned."
            )
        elif category == "skill-gap":
            structure = (
                "1. Transparent Acknowledgment: Accurately state your current exposure level.\n"
                "2. Bridge from Known Fundamentals: Connect adjacent concepts from your verified experience.\n"
                "3. Actionable Ramp-Up Plan: Outline specific documentation, proof-of-concept projects, and test validation.\n"
                "4. Production Readiness: Explain how you would verify code before release."
            )
        else:
            structure = (
                "1. Core Definition & Objective: State the goal and key constraints.\n"
                "2. Architectural Choices: Detail data structures, communication protocols, and components.\n"
                "3. Trade-off Analysis: Explain latency, cost, and complexity tradeoffs evaluated.\n"
                "4. Observability & Edge Cases: Explain error handling, monitoring, and failure mitigation."
            )

        # Illustrative Sample Answer (Clearly Disclaimed)
        sample_answer = (
            f"{SAMPLE_ANSWER_DISCLAIMER_PREFIX}"
            f"Question: {question.get('question_text')}\n\n"
            f"Illustrative Response:\n"
            f"In a similar engineering context, our team encountered a comparable challenge. "
            f"First, I analyzed the primary bottleneck using application profiling and discovered high database query latency under concurrent peak load. "
            f"Rather than simply adding more application servers, I evaluated two architectural alternatives: introducing a Redis read-through cache versus optimizing our PostgreSQL query indexes and connection pooling. "
            f"We decided on Redis caching for high-frequency reads combined with connection pool tuning, accepting slight eventual consistency in exchange for a 65% drop in p99 latency (from 420ms to 145ms). "
            f"To prevent stale cache anomalies, we implemented TTLs and event-based cache invalidation. "
            f"This ensured system stability during our major release while reducing database CPU utilization by 40%."
        )

        if has_injection:
            overall_score = min(overall_score, 40)
            improvements.insert(0, "Security Note: Prompt injection directives were safely neutralized and not executed.")

        return {
            "answer_id": f"ans_{uuid.uuid4().hex[:8]}",
            "session_id": session_id,
            "question_id": question["id"],
            "user_id": user_id,
            "answer_text": answer_text,
            "word_count": word_count,
            "overall_score": overall_score,
            "criterion_feedback": criterion_evaluations,
            "strengths": strengths[:4],
            "improvement_areas": improvements[:3],
            "missing_concepts": missing[:3],
            "suggested_structure": structure,
            "sample_answer": sample_answer,
            "disclaimer": NON_HIRING_DISCLAIMER,
            "is_fallback_eval": True
        }

    def _evaluate_with_llm(
        self,
        question: Dict[str, Any],
        answer_text: str
    ) -> Optional[Dict[str, Any]]:
        """Invokes structured LLM provider to evaluate answer against rubric."""
        provider = llm_provider
        if not provider or not provider.is_available():
            return None

        prompt = (
            f"You are evaluating a candidate's practice interview response against a documented rubric.\n\n"
            f"QUESTION CATEGORY: {question.get('category')}\n"
            f"QUESTION PROMPT: {question.get('question_text')}\n"
            f"EVALUATION CRITERIA & RUBRIC: {json.dumps(question.get('rubric', []))}\n"
            f"WHAT IS BEING EVALUATED: {question.get('what_interviewer_is_evaluating')}\n\n"
            f"CANDIDATE SUBMITTED ANSWER:\n"
            f"{wrap_untrusted_content(answer_text, 'CANDIDATE_ANSWER')}\n\n"
            f"Return a JSON object conforming strictly to this structure:\n"
            f"{{\n"
            f'  "overall_score": <int 0-100>,\n'
            f'  "criterion_feedback": [\n'
            f'    {{"criterion": "<name>", "rating": "<strong|adequate|needs_work>", "score": <int 0-100>, "feedback": "<specific guidance>"}}\n'
            f'  ],\n'
            f'  "strengths": ["<strength 1>", "<strength 2>"],\n'
            f'  "improvement_areas": ["<improvement 1>", "<improvement 2>"],\n'
            f'  "missing_concepts": ["<missing 1>", "<missing 2>"],\n'
            f'  "suggested_structure": "<step by step outline>",\n'
            f'  "sample_answer": "<hypothetical illustrative answer>"\n'
            f"}}"
        )

        res = provider.generate_json(
            prompt,
            system_prompt=_build_hardened_system_prompt("You are an interview preparation evaluation coach. Grade objectively according to the provided rubric criteria."),
            temperature=0.2
        )

        if not res or not isinstance(res, dict) or "overall_score" not in res:
            return None

        # Ensure sample answer has mandatory prefix
        sample_ans = res.get("sample_answer", "")
        if sample_ans and not sample_ans.startswith(SAMPLE_ANSWER_DISCLAIMER_PREFIX.strip()):
            res["sample_answer"] = f"{SAMPLE_ANSWER_DISCLAIMER_PREFIX}{sample_ans}"

        res["answer_id"] = f"ans_{uuid.uuid4().hex[:8]}"
        res["disclaimer"] = NON_HIRING_DISCLAIMER
        res["is_fallback_eval"] = False
        return res


# Singleton instance
interview_service = InterviewService()
