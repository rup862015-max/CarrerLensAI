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
    projects: List[ExtractedProject] = Field(default_factory=list)


class ResumeHealthScores(BaseModel):
    overall: int = Field(..., ge=0, le=100)
    content_quality: int = Field(..., ge=0, le=100)
    skills_coverage: int = Field(..., ge=0, le=100)
    experience_clarity: int = Field(..., ge=0, le=100)
    project_strength: int = Field(..., ge=0, le=100)
    ats_readability: int = Field(..., ge=0, le=100)


class ResumeAnalysisResponse(BaseModel):
    resume_id: str
    filename: str
    health_scores: ResumeHealthScores
    extracted_profile: ExtractedProfile
    raw_text: Optional[str] = None
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
    match_type: str # project_evidence | experience_evidence | skills_section | education
    status: str = "matched" # matched | partial | missing
    confidence: float # 0.0 to 1.0
    importance: str = "recommended" # critical | recommended | optional
    category: Optional[str] = "general"
    evidence_locations: List[str] = Field(default_factory=list)


class MissingRequirement(BaseModel):
    requirement: str
    importance: str # critical | recommended | optional
    category: str
    reason: str
    market_prevalence: str = "Found in 65% of similar roles"


class SkillGap(BaseModel):
    skill: str
    priority: str # High | Medium | Low
    why_it_matters: str
    current_evidence: str = "No supporting evidence found"
    market_prevalence: str


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
