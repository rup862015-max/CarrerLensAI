"""
Pydantic Schemas for CareerLens AI Phase 1
Defines request and response data contracts for type safety.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ProjectSkill(BaseModel):
    name: str = Field(..., alias="name")
    skill_type: str = Field(default="explicit", description="'explicit' or 'inferred'")


class ExtractedProject(BaseModel):
    title: str
    technologies: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    inferred_skills: List[str] = Field(default_factory=list)


class ExtractedProfile(BaseModel):
    candidate_name: Optional[str] = "Candidate"
    email: Optional[str] = None
    phone: Optional[str] = None
    education: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    years_of_experience: float = 0.0
    skills: List[str] = Field(default_factory=list)
    detailed_skills: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[ExtractedProject] = Field(default_factory=list)
    unrecognized_sections: Dict[str, str] = Field(default_factory=dict)


class ResumeHealthScores(BaseModel):
    overall: int = Field(..., ge=0, le=100)
    content_quality: int = Field(..., ge=0, le=100)
    skills_coverage: int = Field(..., ge=0, le=100)
    experience_clarity: int = Field(..., ge=0, le=100)
    project_strength: int = Field(..., ge=0, le=100)
    ats_readability: int = Field(..., ge=0, le=100)


class IntegrityReport(BaseModel):
    status: str = "success"  # success | warning | partial | failed
    message: str = "Resume extracted successfully"
    warnings: List[str] = Field(default_factory=list)
    checks: Dict[str, Any] = Field(default_factory=dict)
    coverage_ratio: float = 1.0
    preserved_sections: List[str] = Field(default_factory=list)


# ─── Security Audit Schemas ───

class SecurityFinding(BaseModel):
    id: str
    severity: str  # critical | warning | info
    category: str  # prompt_injection | hidden_characters | obfuscation | data_exfiltration | malicious_links | code_injection | scanner_notice
    title: str
    description: str
    evidence_snippet: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    line_number: Optional[int] = None
    remediation: str
    false_positive_note: Optional[str] = None


class HiddenCharSummary(BaseModel):
    total_hidden_chars: int = 0
    categories: Dict[str, int] = Field(default_factory=dict)
    characters_detected: List[Dict[str, Any]] = Field(default_factory=list)
    bidi_overrides_detected: int = 0
    zero_width_detected: int = 0


class SecurityAuditReport(BaseModel):
    audit_id: str
    filename: Optional[str] = None
    status: str  # passed | warning | blocked | error
    action_taken: str  # allowed | warned | blocked
    risk_score: int  # 0 to 100
    findings_count: Dict[str, int]
    findings: List[SecurityFinding] = Field(default_factory=list)
    hidden_characters_summary: HiddenCharSummary
    explanation: str
    recommendations: List[str] = Field(default_factory=list)
    scanner_limitations: List[str] = Field(default_factory=list)
    scan_metadata: Dict[str, Any] = Field(default_factory=dict)
    is_safe_for_llm: bool = True


class SecurityAuditRequest(BaseModel):
    resume_id: Optional[str] = None
    resume_text: Optional[str] = None
    job_description: Optional[str] = None
    filename: Optional[str] = None


class ResumeAnalysisResponse(BaseModel):
    resume_id: str
    filename: str
    health_scores: ResumeHealthScores
    extracted_profile: ExtractedProfile
    raw_text: Optional[str] = None
    extraction_status: str = "success"
    warnings: List[str] = Field(default_factory=list)
    integrity_report: Optional[IntegrityReport] = None
    security_audit: Optional[SecurityAuditReport] = None
    message: str = "Analysis completed successfully"


class ResumeAnalyzeRequest(BaseModel):
    resume_text: str = Field(..., min_length=10, description="Raw text of the resume to analyze")
    filename: Optional[str] = "Pasted_Resume.txt"


class JobRequirement(BaseModel):
    name: str
    importance: str = "recommended" # critical | recommended | optional
    category: Optional[str] = "general"


class JobAnalyzeRequest(BaseModel):
    job_text: str = Field(..., min_length=10, description="Raw text of the job description")
    title: Optional[str] = "Custom Job Opening"


class DemoJob(BaseModel):
    id: str
    title: str
    department: str
    location: str
    experience_level: str
    description: str
    requirements: List[JobRequirement]
    education_requirement: str
    responsibilities: List[str]


class MatchedRequirement(BaseModel):
    requirement: str
    resume_evidence: str
    match_type: str # project_evidence | experience_evidence | skills_section | education | taxonomy | none
    status: str = "matched" # matched | partial | unverified | missing
    confidence: float # 0.0 to 1.0
    importance: str = "recommended" # critical | required | recommended | preferred | optional
    category: Optional[str] = "general"
    evidence_locations: List[str] = Field(default_factory=list)
    scoring_contribution: Optional[str] = None
    uncertainty_note: Optional[str] = None


class MissingRequirement(BaseModel):
    requirement: str
    importance: str # critical | required | recommended | preferred | optional
    category: str
    reason: str
    status: str = "missing"
    confidence: float = 0.0
    resume_evidence: Optional[str] = "No supporting evidence found in candidate profile."
    market_prevalence: str = "Requirement in target job description"
    scoring_contribution: Optional[str] = None
    uncertainty_note: Optional[str] = None


class SkillGap(BaseModel):
    skill: str
    priority: str # High | Medium | Low
    why_it_matters: str
    current_evidence: str = "No supporting evidence found"
    market_prevalence: str = "Requirement in target job description"


class CareerPreview(BaseModel):
    current_strongest_path: str
    match_percentage: int
    potential_next_step: str
    skills_to_add: List[str]
    readiness_level: str


class MatchRequest(BaseModel):
    resume_id: Optional[str] = None
    resume_profile: Optional[ExtractedProfile] = None
    resume_text: Optional[str] = None
    job_id: Optional[str] = None
    job_description: Optional[str] = None
    job_title: Optional[str] = None


class MatchResponse(BaseModel):
    match_id: str
    job_title: str
    overall_score: int
    match_grade: str # A+ | A | B+ | B | C | Needs Work
    skill_match: int
    experience_match: int
    education_match: int
    project_relevance: int
    semantic_fit: int
    matched_requirements: List[MatchedRequirement]
    missing_requirements: List[MissingRequirement]
    skill_gaps: List[SkillGap]
    side_by_side: Dict[str, Any]
    career_preview: CareerPreview
    recommendations: List[str]


# ─── Career Simulator Schemas ───

class HypotheticalSkillEval(BaseModel):
    skill: str
    canonical_name: str
    is_recognized: bool
    status: str  # recognized | custom_unverified
    note: str
    matched_requirements: List[str] = Field(default_factory=list)
    impact: Optional[str] = None


class RequirementDelta(BaseModel):
    requirement: str
    importance: str = "recommended"
    category: str = "general"
    baseline_status: str
    simulated_status: str
    status_changed: bool
    evidence_type: str  # verified_resume | hypothetical_skill | none
    baseline_confidence: float
    simulated_confidence: float
    scoring_rule: str
    uncertainty_note: Optional[str] = None
    contributing_skill: Optional[str] = None


class SubscoreDeltaDetail(BaseModel):
    baseline: int
    simulated: int
    delta: int


class SubscoreDeltas(BaseModel):
    overall: SubscoreDeltaDetail
    skill_match: SubscoreDeltaDetail
    experience_match: SubscoreDeltaDetail
    education_match: SubscoreDeltaDetail
    project_relevance: SubscoreDeltaDetail
    semantic_fit: SubscoreDeltaDetail


class SimulationPolicy(BaseModel):
    hypothetical_skill_credit: float = 0.80
    policy_description: str
    scoring_weights_reused: bool = True
    weights_summary: Dict[str, float] = Field(default_factory=dict)


class SimulateRequest(BaseModel):
    resume_id: Optional[str] = None
    resume_profile: Optional[ExtractedProfile] = None
    resume_text: Optional[str] = None
    job_id: Optional[str] = None
    job_description: Optional[str] = None
    job_title: Optional[str] = None
    hypothetical_skills: List[str] = Field(default_factory=list, description="List of hypothetical skills to simulate")


class SimulateResponse(BaseModel):
    simulation_id: str
    job_title: str
    baseline_score: int
    baseline_grade: str
    simulated_score: int
    simulated_grade: str
    score_delta: int
    subscore_deltas: SubscoreDeltas
    requirement_deltas: List[RequirementDelta]
    affected_requirements: List[RequirementDelta]
    closed_gaps: List[str]
    remaining_gaps: List[str]
    hypothetical_skills_evaluated: List[HypotheticalSkillEval]
    simulation_policy: SimulationPolicy
    recommendation: str


# ─── Career Paths Schemas ───

class TransferableSkill(BaseModel):
    candidate_skill: str
    related_to: str
    relationship: str = "taxonomy_related"


class CareerPathItem(BaseModel):
    role_title: str
    role_id: str
    overall_score: int
    match_grade: str
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    transferable_skills: List[TransferableSkill] = Field(default_factory=list)
    skill_match: int
    experience_match: int
    gap_count: int
    readiness: str


class CareerPathsResponse(BaseModel):
    analysis_id: str
    candidate_name: str
    paths: List[CareerPathItem]
    best_fit: str


# ─── Skill Learning Roadmap Schemas ───

class RoadmapStep(BaseModel):
    id: str
    skill: str
    category: str = "general"
    domain: str = "General"
    related_requirement: str
    importance: str = "recommended"
    evidence_status: str  # missing | unverified | partial | prerequisite_needed
    priority: str  # High | Medium | Low
    priority_score: int
    priority_reason: str
    prerequisites: List[str] = Field(default_factory=list)
    satisfied_prerequisites: List[str] = Field(default_factory=list)
    related_skills: List[str] = Field(default_factory=list)
    learning_objective: str
    practical_exercise: str
    completion_criteria: str
    resume_evidence_guidance: str
    status: str = "not_started"  # not_started | in_progress | completed


class RoadmapPhase(BaseModel):
    phase_number: int
    phase_name: str
    description: str
    skills: List[RoadmapStep] = Field(default_factory=list)


class RoadmapResponse(BaseModel):
    roadmap_id: str
    job_title: str
    job_id: str
    candidate_name: str
    summary: str
    phases: List[RoadmapPhase] = Field(default_factory=list)
    steps: List[RoadmapStep] = Field(default_factory=list)
    total_steps: int
    completed_steps: int
    in_progress_steps: int
    methodology_notes: str


class RoadmapProgressUpdateRequest(BaseModel):
    resume_id: str
    job_id: str
    skill_name: str
    status: str  # not_started | in_progress | completed


class RoadmapProgressUpdateResponse(BaseModel):
    status: str = "success"
    message: str
    updated_progress: Dict[str, Any]


# ─── Authentication & User Schemas (Stage 3.1) ───

class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Strong user password (minimum 8 characters)")
    name: Optional[str] = Field(default=None, description="User full name")
    username: Optional[str] = Field(default=None, description="User display username")
    full_name: Optional[str] = Field(default=None, description="User full name alias")


class UserLoginRequest(BaseModel):
    email: Optional[str] = Field(default=None, description="User email address")
    username_or_email: Optional[str] = Field(default=None, description="User email or username")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class AuthStatusResponse(BaseModel):
    authenticated: bool
    user: Optional[UserResponse] = None


class ForgotPasswordRequest(BaseModel):
    email_or_username: str = Field(..., description="Registered email address or username")


class ResetPasswordRequest(BaseModel):
    email_or_username: str = Field(..., description="Registered email address or username")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")
    reset_token: Optional[str] = Field(default=None, description="Optional reset verification code")


class PasswordResetResponse(BaseModel):
    success: bool = True
    message: str
    email: Optional[str] = None
    reset_token: Optional[str] = None


# ─── Stage 4: Interview Preparation Schemas ───

class InterviewRubricCriterion(BaseModel):
    name: str = Field(..., description="Name of the evaluation criterion")
    description: str = Field(..., description="Description of what constitutes strong performance for this criterion")
    focus: str = Field(default="core", description="Criterion weight/focus: core | secondary | differentiator")


class InterviewQuestion(BaseModel):
    id: str = Field(..., description="Unique question identifier")
    category: str = Field(..., description="Category: technical | project | behavioral | problem-solving | skill-gap")
    question_text: str = Field(..., description="Interview question prompt")
    related_requirement: Optional[str] = Field(default=None, description="Associated job requirement or skill")
    difficulty_level: str = Field(..., description="Difficulty: entry | mid-level | senior | principal")
    difficulty_rationale: str = Field(..., description="Why this difficulty level was selected")
    what_interviewer_is_evaluating: str = Field(..., description="Key competencies and depth assessed")
    rubric: List[InterviewRubricCriterion] = Field(..., description="Evaluation rubric criteria")
    source_reference: str = Field(..., description="Reference to job requirement or resume evidence")
    is_generic_fallback: bool = Field(default=False, description="True if generated from general fallback due to data limits")
    order_index: int = Field(default=0, description="Order index in the session")
    answer: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None


class CreateInterviewSessionRequest(BaseModel):
    resume_id: Optional[str] = None
    resume_profile: Optional[ExtractedProfile] = None
    resume_text: Optional[str] = None
    job_id: Optional[str] = None
    job_description: Optional[str] = None
    job_title: Optional[str] = None
    categories: Optional[List[str]] = Field(default=None, description="Optional categories filter")
    num_questions: int = Field(default=5, ge=1, le=10, description="Number of questions to generate (1-10)")


class InterviewSessionSummary(BaseModel):
    id: str
    user_id: str
    resume_id: Optional[str] = None
    job_id: Optional[str] = None
    job_title: str
    candidate_name: str
    status: str
    total_questions: int
    completed_questions: int
    average_score: float
    created_at: str
    data_limitation_note: Optional[str] = None


class InterviewSessionResponse(BaseModel):
    session_id: str
    user_id: str
    resume_id: Optional[str] = None
    job_id: Optional[str] = None
    job_title: str
    candidate_name: str
    status: str
    total_questions: int
    completed_questions: int
    average_score: float
    created_at: str
    data_limitation_note: Optional[str] = None
    questions: List[InterviewQuestion]


class CriterionEvaluation(BaseModel):
    criterion: str
    rating: str = Field(..., description="Rating: strong | adequate | needs_work")
    score: int = Field(..., ge=0, le=100, description="Criterion score out of 100")
    feedback: str = Field(..., description="Detailed criterion evaluation")


class SubmitAnswerRequest(BaseModel):
    question_id: str
    answer_text: str = Field(..., min_length=10, description="Candidate response text")


class AnswerEvaluationResponse(BaseModel):
    answer_id: str
    session_id: str
    question_id: str
    word_count: int
    overall_score: int = Field(..., ge=0, le=100, description="Practice answer score (0-100)")
    criterion_feedback: List[CriterionEvaluation]
    strengths: List[str]
    improvement_areas: List[str]
    missing_concepts: List[str]
    suggested_structure: str
    sample_answer: Optional[str] = None
    disclaimer: str
    created_at: str
    is_fallback_eval: bool = False


# ─── Stage 5: Fairness Audit & Scoring Consistency Schemas ───

class FairnessFinding(BaseModel):
    id: str = Field(..., description="Unique finding ID e.g. FAIR-001")
    severity: str = Field(..., description="Severity: critical | warning | info")
    category: str = Field(..., description="Category: alias_normalization | null_safety | semantic_sensitivity | demographic_invariance | boundary_case | unassessed_dimension")
    title: str
    description: str
    expected_behavior: str
    observed_behavior: str
    scoring_components_affected: List[str] = Field(default_factory=list)
    reproducible_test_case: str
    remediation: str
    status: str = Field(..., description="Status: confirmed_defect | remediated | documented_limitation | unassessed_risk")


class FairnessMetricItem(BaseModel):
    name: str
    formula: str
    value: float
    tolerance: float
    sample_size: int
    status: str = Field(..., description="Status: passed | flagged | informational")
    description: str
    limitations: str


class FairnessComponentDelta(BaseModel):
    component: str
    baseline: int
    variant: int
    delta: int


class FairnessTestResult(BaseModel):
    test_id: str
    category: str
    description: str
    baseline_name: str
    variant_name: str
    attribute_manipulated: str
    baseline_score: int
    variant_score: int
    score_delta: int
    component_deltas: Dict[str, FairnessComponentDelta] = Field(default_factory=dict)
    status: str = Field(..., description="passed | discrepancy")
    explanation: str


class UnassessedDimension(BaseModel):
    dimension: str
    status: str = "Unassessed"
    reason: str
    ethical_boundary: str
    generalization_risk: str


class FairnessAuditReport(BaseModel):
    audit_id: str
    user_id: str
    policy_version: str = "v1.2.0"
    timestamp: str
    total_tests: int
    passed_tests: int
    discrepancy_count: int
    discrepancy_rate: float
    max_absolute_delta: int
    avg_absolute_delta: float
    metrics: List[FairnessMetricItem] = Field(default_factory=list)
    findings: List[FairnessFinding] = Field(default_factory=list)
    test_results: List[FairnessTestResult] = Field(default_factory=list)
    unassessed_dimensions: List[UnassessedDimension] = Field(default_factory=list)
    scoring_policy_summary: Dict[str, Any] = Field(default_factory=dict)


class FairnessAuditSummary(BaseModel):
    id: str
    user_id: str
    policy_version: str
    total_tests: int
    passed_tests: int
    discrepancy_rate: float
    max_absolute_delta: int
    avg_absolute_delta: float
    created_at: str



