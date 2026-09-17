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
}

export interface ResumeHealthScores {
  overall: number;
  content_quality: number;
  skills_coverage: number;
  experience_clarity: number;
  project_strength: number;
  ats_readability: number;
}

export interface ResumeAnalysisResponse {
  resume_id: string;
  filename: string;
  health_scores: ResumeHealthScores;
  extracted_profile: ExtractedProfile;
  raw_text?: string;
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
  match_type: 'project_evidence' | 'experience_evidence' | 'skills_section' | 'education' | 'none';
  status: 'matched' | 'partial' | 'missing';
  confidence: number;
  importance: 'critical' | 'recommended' | 'optional';
  category?: string;
  evidence_locations: string[];
}

export interface MissingRequirement {
  requirement: string;
  importance: 'critical' | 'recommended' | 'optional';
  category: string;
  reason: string;
  market_prevalence: string;
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
