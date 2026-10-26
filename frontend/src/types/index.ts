export type TabType = 
  | 'dashboard'
  | 'resume-analysis'
  | 'job-matching'
  | 'career-simulator'
  | 'skill-roadmap'
  | 'interview'
  | 'security-audit'
  | 'fairness-audit';

export interface ExtractedProject {
  title: string;
  technologies: string[];
  evidence: string[];
  inferred_skills: string[];
}

export interface DetailedSkill {
  name: string;
  category: string;
  domain: string;
  skill_type: 'explicit' | 'inferred';
  in_projects: boolean;
  in_experience: boolean;
}

export interface ExtractedProfile {
  candidate_name?: string;
  email?: string;
  phone?: string;
  education: string[];
  experience: string[];
  years_of_experience: number;
  skills: string[];
  detailed_skills?: DetailedSkill[];
  projects: ExtractedProject[];
  unrecognized_sections?: Record<string, string>;
}

export interface ResumeHealthScores {
  overall: number;
  content_quality: number;
  skills_coverage: number;
  experience_clarity: number;
  project_strength: number;
  ats_readability: number;
}

export interface IntegrityReport {
  status: 'success' | 'warning' | 'partial' | 'failed';
  message: string;
  warnings: string[];
  checks: Record<string, any>;
  coverage_ratio: number;
  preserved_sections: string[];
}

export interface SecurityFinding {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  category: string;
  title: string;
  description: string;
  evidence_snippet: string;
  start_offset?: number | null;
  end_offset?: number | null;
  line_number?: number | null;
  remediation: string;
  false_positive_note?: string | null;
}

export interface HiddenCharOccurrence {
  codepoint: string;
  name: string;
  category: string;
  count: number;
  first_offset: number;
  first_line: number;
  registered_severity: string;
  risk: string;
}

export interface HiddenCharSummary {
  total_hidden_chars: number;
  categories: Record<string, number>;
  characters_detected: HiddenCharOccurrence[];
  bidi_overrides_detected: number;
  zero_width_detected: number;
}

export interface SecurityAuditReport {
  audit_id: string;
  resume_id?: string | null;
  filename?: string | null;
  status: 'passed' | 'warning' | 'blocked' | 'error';
  action_taken: 'allowed' | 'warned' | 'blocked';
  risk_score: number;
  findings_count: {
    critical: number;
    warning: number;
    info: number;
    total: number;
  };
  findings: SecurityFinding[];
  hidden_characters_summary: HiddenCharSummary;
  explanation: string;
  recommendations: string[];
  scanner_limitations: string[];
  scan_metadata: {
    characters_scanned?: number;
    total_lines?: number;
    scan_duration_ms?: number;
    source_type?: string;
    is_truncated?: boolean;
  };
  is_safe_for_llm: boolean;
}

export interface SecurityAuditRequest {
  resume_id?: string;
  resume_text?: string;
  job_description?: string;
  filename?: string;
}

export interface ResumeAnalysisResponse {
  resume_id: string;
  filename: string;
  health_scores: ResumeHealthScores;
  extracted_profile: ExtractedProfile;
  raw_text?: string;
  extraction_status?: 'success' | 'warning' | 'partial' | 'failed';
  warnings?: string[];
  integrity_report?: IntegrityReport;
  security_audit?: SecurityAuditReport;
  message?: string;
}

export interface JobRequirement {
  name: string;
  importance: 'critical' | 'recommended' | 'optional';
  category?: string;
}

export interface DemoJob {
  id: string;
  title: string;
  department: string;
  location: string;
  experience_level: string;
  description: string;
  requirements: JobRequirement[];
  education_requirement: string;
  responsibilities: string[];
}

export interface MatchedRequirement {
  requirement: string;
  resume_evidence: string;
  match_type: 'project_evidence' | 'experience_evidence' | 'skills_section' | 'education' | 'taxonomy' | 'none';
  status: 'matched' | 'partial' | 'unverified' | 'missing';
  confidence: number;
  importance: 'critical' | 'required' | 'recommended' | 'preferred' | 'optional';
  category?: string;
  evidence_locations: string[];
  scoring_contribution?: string;
  uncertainty_note?: string;
}

export interface MissingRequirement {
  requirement: string;
  importance: 'critical' | 'required' | 'recommended' | 'preferred' | 'optional';
  category: string;
  reason: string;
  status?: 'missing';
  confidence?: number;
  resume_evidence?: string;
  market_prevalence: string;
  scoring_contribution?: string;
  uncertainty_note?: string;
}

export interface SkillGap {
  skill: string;
  priority: 'High' | 'Medium' | 'Low';
  why_it_matters: string;
  current_evidence: string;
  market_prevalence: string;
}

export interface CareerPreview {
  current_strongest_path: string;
  match_percentage: number;
  potential_next_step: string;
  skills_to_add: string[];
  readiness_level: string;
}

export interface MatchResponse {
  match_id: string;
  job_title: string;
  overall_score: number;
  match_grade: 'A+' | 'A' | 'B+' | 'B' | 'C' | 'Needs Work';
  skill_match: number;
  experience_match: number;
  education_match: number;
  project_relevance: number;
  semantic_fit: number;
  matched_requirements: MatchedRequirement[];
  missing_requirements: MissingRequirement[];
  skill_gaps: SkillGap[];
  side_by_side: {
    profile_skills: { name: string; has_match: boolean }[];
    job_requirements: { name: string; matched: boolean; importance: string }[];
  };
  career_preview: CareerPreview;
  recommendations: string[];
}

export interface HypotheticalSkillEval {
  skill: string;
  canonical_name: string;
  is_recognized: boolean;
  status: 'recognized' | 'custom_unverified';
  note: string;
  matched_requirements: string[];
  impact?: string;
}

export interface RequirementDelta {
  requirement: string;
  importance: 'critical' | 'required' | 'recommended' | 'preferred' | 'optional';
  category: string;
  baseline_status: 'matched' | 'partial' | 'unverified' | 'missing' | 'hypothetical';
  simulated_status: 'matched' | 'partial' | 'unverified' | 'missing' | 'hypothetical';
  status_changed: boolean;
  evidence_type: 'verified_resume' | 'hypothetical_skill' | 'none';
  baseline_confidence: number;
  simulated_confidence: number;
  scoring_rule: string;
  uncertainty_note?: string;
  contributing_skill?: string;
}

export interface SubscoreDeltaDetail {
  baseline: number;
  simulated: number;
  delta: number;
}

export interface SubscoreDeltas {
  overall: SubscoreDeltaDetail;
  skill_match: SubscoreDeltaDetail;
  experience_match: SubscoreDeltaDetail;
  education_match: SubscoreDeltaDetail;
  project_relevance: SubscoreDeltaDetail;
  semantic_fit: SubscoreDeltaDetail;
}

export interface SimulationPolicy {
  hypothetical_skill_credit: number;
  policy_description: string;
  scoring_weights_reused: boolean;
  weights_summary: Record<string, number>;
}

export interface SimulateRequest {
  resume_id?: string;
  resume_profile?: ExtractedProfile;
  resume_text?: string;
  job_id?: string;
  job_description?: string;
  job_title?: string;
  hypothetical_skills: string[];
}

export interface SimulateResponse {
  simulation_id: string;
  job_title: string;
  baseline_score: number;
  baseline_grade: string;
  simulated_score: number;
  simulated_grade: string;
  score_delta: number;
  subscore_deltas: SubscoreDeltas;
  requirement_deltas: RequirementDelta[];
  affected_requirements: RequirementDelta[];
  closed_gaps: string[];
  remaining_gaps: string[];
  hypothetical_skills_evaluated: HypotheticalSkillEval[];
  simulation_policy: SimulationPolicy;
  recommendation: string;
}

export interface TransferableSkill {
  candidate_skill: string;
  related_to: string;
  relationship: string;
}

export interface CareerPathItem {
  role_title: string;
  role_id: string;
  overall_score: number;
  match_grade: string;
  matched_skills: string[];
  missing_skills: string[];
  transferable_skills: TransferableSkill[];
  skill_match: number;
  experience_match: number;
  gap_count: number;
  readiness: string;
}

export interface CareerPathsResponse {
  analysis_id: string;
  candidate_name: string;
  paths: CareerPathItem[];
  best_fit: string;
}

export interface RoadmapStep {
  id: string;
  skill: string;
  category: string;
  domain: string;
  related_requirement: string;
  importance: string;
  evidence_status: 'missing' | 'unverified' | 'partial' | 'prerequisite_needed';
  priority: 'High' | 'Medium' | 'Low';
  priority_score: number;
  priority_reason: string;
  prerequisites: string[];
  satisfied_prerequisites: string[];
  related_skills: string[];
  learning_objective: string;
  practical_exercise: string;
  completion_criteria: string;
  resume_evidence_guidance: string;
  status: 'not_started' | 'in_progress' | 'completed';
}

export interface RoadmapPhase {
  phase_number: number;
  phase_name: string;
  description: string;
  skills: RoadmapStep[];
}

export interface RoadmapResponse {
  roadmap_id: string;
  job_title: string;
  job_id: string;
  candidate_name: string;
  summary: string;
  phases: RoadmapPhase[];
  steps: RoadmapStep[];
  total_steps: number;
  completed_steps: number;
  in_progress_steps: number;
  methodology_notes: string;
}

export interface RoadmapProgressUpdateRequest {
  resume_id: string;
  job_id: string;
  skill_name: string;
  status: 'not_started' | 'in_progress' | 'completed';
}

export interface RoadmapProgressUpdateResponse {
  status: string;
  message: string;
  updated_progress: Record<string, string>;
}

// ─── Authentication Types (Stage 3.1) ───

export interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// ─── Stage 4: Interview Preparation Types ───

export interface InterviewRubricCriterion {
  name: string;
  description: string;
  focus: 'core' | 'secondary' | 'differentiator';
}

export interface CriterionEvaluation {
  criterion: string;
  rating: 'strong' | 'adequate' | 'needs_work';
  score: number;
  feedback: string;
}

export interface AnswerEvaluationResponse {
  answer_id: string;
  session_id: string;
  question_id: string;
  word_count: number;
  overall_score: number;
  criterion_feedback: CriterionEvaluation[];
  strengths: string[];
  improvement_areas: string[];
  missing_concepts: string[];
  suggested_structure: string;
  sample_answer?: string;
  disclaimer: string;
  created_at: string;
  is_fallback_eval?: boolean;
}

export interface InterviewQuestion {
  id: string;
  category: 'technical' | 'project' | 'behavioral' | 'problem-solving' | 'skill-gap';
  question_text: string;
  related_requirement?: string;
  difficulty_level: 'entry' | 'mid-level' | 'senior' | 'principal';
  difficulty_rationale: string;
  what_interviewer_is_evaluating: string;
  rubric: InterviewRubricCriterion[];
  source_reference: string;
  is_generic_fallback: boolean;
  order_index: number;
  answer?: string | null;
  evaluation?: AnswerEvaluationResponse | null;
}

export interface InterviewSessionSummary {
  id: string;
  user_id: string;
  resume_id?: string;
  job_id?: string;
  job_title: string;
  candidate_name: string;
  status: string;
  total_questions: number;
  completed_questions: number;
  average_score: number;
  created_at: string;
  data_limitation_note?: string;
}

export interface InterviewSessionResponse {
  session_id: string;
  user_id: string;
  resume_id?: string;
  job_id?: string;
  job_title: string;
  candidate_name: string;
  status: string;
  total_questions: number;
  completed_questions: number;
  average_score: number;
  created_at: string;
  data_limitation_note?: string;
  questions: InterviewQuestion[];
}

export interface CreateInterviewSessionRequest {
  resume_id?: string;
  resume_profile?: ExtractedProfile;
  resume_text?: string;
  job_id?: string;
  job_description?: string;
  job_title?: string;
  categories?: string[];
  num_questions?: number;
}

export interface SubmitAnswerRequest {
  question_id: string;
  answer_text: string;
}

// ─── Stage 5: Fairness Audit & Scoring Consistency Types ───

export interface FairnessFinding {
  id: string;
  severity: 'high' | 'medium' | 'low' | 'informational';
  title: string;
  description: string;
  condition: string;
  observed_behavior: string;
  expected_behavior: string;
  reproducible_test_case: string;
  affected_components: string[];
  remediation: string;
  status: 'remediated' | 'active_risk' | 'monitored' | 'unassessed_risk';
}

export interface FairnessMetricItem {
  name: string;
  formula: string;
  value: number;
  tolerance: number;
  sample_size: number;
  status: 'passed' | 'flagged';
  description: string;
  limitations: string;
}

export interface FairnessComponentDelta {
  component: string;
  baseline: number;
  variant: number;
  delta: number;
}

export interface FairnessTestResult {
  test_id: string;
  category: string;
  description: string;
  baseline_name: string;
  variant_name: string;
  attribute_manipulated: string;
  baseline_score: number;
  variant_score: number;
  score_delta: number;
  component_deltas: Record<string, FairnessComponentDelta>;
  status: 'passed' | 'discrepancy';
  explanation: string;
}

export interface UnassessedDimension {
  dimension: string;
  status: string;
  reason: string;
  ethical_boundary: string;
  generalization_risk: string;
}

export interface ScoringPolicyComponent {
  name: string;
  weight: number;
  description: string;
}

export interface ScoringPolicySummary {
  policy_version: string;
  formula_definition?: string;
  weights: Record<string, number>;
  importance_multipliers?: Record<string, number>;
  tolerances: Record<string, number>;
  relevant_input_fields?: string[];
  irrelevant_attributes_policy?: string[];
  components?: ScoringPolicyComponent[];
  irrelevant_attributes?: string[];
}

export interface FairnessAuditReport {
  audit_id: string;
  user_id: string;
  policy_version: string;
  timestamp: string;
  total_tests: number;
  passed_tests: number;
  discrepancy_count: number;
  discrepancy_rate: number;
  max_absolute_delta: number;
  avg_absolute_delta: number;
  metrics: FairnessMetricItem[];
  findings: FairnessFinding[];
  test_results: FairnessTestResult[];
  unassessed_dimensions: UnassessedDimension[];
  scoring_policy_summary: ScoringPolicySummary;
}

export interface FairnessAuditSummary {
  audit_id: string;
  user_id: string;
  policy_version: string;
  timestamp: string;
  total_tests: number;
  passed_tests: number;
  discrepancy_count: number;
  discrepancy_rate: number;
  max_absolute_delta: number;
}



