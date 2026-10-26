/**
 * API Service for CareerLens AI Frontend
 * Interacts with FastAPI backend at http://localhost:8000
 * Manages JWT tokens, session lifecycle, and automatic authorization headers (Stage 3.1).
 */

import { 
  ResumeAnalysisResponse, 
  DemoJob, 
  MatchResponse, 
  ExtractedProfile,
  SimulateRequest,
  SimulateResponse,
  CareerPathsResponse,
  RoadmapResponse,
  RoadmapProgressUpdateRequest,
  RoadmapProgressUpdateResponse,
  SecurityAuditReport,
  SecurityAuditRequest,
  User,
  AuthResponse,
  InterviewSessionResponse,
  InterviewSessionSummary,
  CreateInterviewSessionRequest,
  SubmitAnswerRequest,
  AnswerEvaluationResponse,
  FairnessAuditReport,
  FairnessAuditSummary,
  ScoringPolicySummary
} from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8001/api';
const TOKEN_KEY = 'careerlens_auth_token';
const USER_KEY = 'careerlens_auth_user';

// Session change / Unauthorized event listeners
type AuthListener = (user: User | null) => void;
type UnauthorizedListener = () => void;

const authListeners: Set<AuthListener> = new Set();
const unauthorizedListeners: Set<UnauthorizedListener> = new Set();

export function humanizeErrorMessage(detail: string): string {
  if (!detail) return 'Something went wrong. Please try again.';
  const lower = detail.toLowerCase();
  if (
    lower.includes('bearer') ||
    lower.includes('token') ||
    lower.includes('authentication required') ||
    lower.includes('not authenticated') ||
    lower.includes('unauthorized') ||
    lower.includes('credentials')
  ) {
    return 'You need to sign in to use this feature.';
  }
  return detail;
}

export const apiService = {
  // ─── Token & Session Management ───

  getAuthToken(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },

  getUser(): User | null {
    try {
      const data = localStorage.getItem(USER_KEY);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },

  setAuth(token: string, user: User) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      authListeners.forEach(fn => fn(user));
    } catch (e) {
      console.error('Failed to save auth to localStorage:', e);
    }
  },

  clearAuth() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      authListeners.forEach(fn => fn(null));
    } catch (e) {
      console.error('Failed to clear auth from localStorage:', e);
    }
  },

  isAuthenticated(): boolean {
    return !!this.getAuthToken();
  },

  onAuthChange(callback: AuthListener): () => void {
    authListeners.add(callback);
    return () => authListeners.delete(callback);
  },

  onUnauthorized(callback: UnauthorizedListener): () => void {
    unauthorizedListeners.add(callback);
    return () => unauthorizedListeners.delete(callback);
  },

  // ─── Authenticated Fetch Wrapper ───

  async fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
    const token = this.getAuthToken();
    const headers = new Headers(options.headers || {});

    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const mergedOptions: RequestInit = {
      ...options,
      headers,
    };

    const res = await fetch(url, mergedOptions);

    if (res.status === 401) {
      // Invalidate session immediately on 401 Unauthorized
      this.clearAuth();
      unauthorizedListeners.forEach(fn => fn());
    }

    return res;
  },

  // ─── Authentication API (Stage 3.1) ───

  async register(params: { username: string; email: string; password: string; full_name?: string }): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(errorData.detail || 'Registration failed');
    }

    const data: AuthResponse = await res.json();
    this.setAuth(data.access_token, data.user);
    return data;
  },

  async login(params: { username_or_email: string; password: string }): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Invalid credentials' }));
      throw new Error(errorData.detail || 'Sign in failed');
    }

    const data: AuthResponse = await res.json();
    this.setAuth(data.access_token, data.user);
    return data;
  },

  async getMe(): Promise<User> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/auth/me`);
    if (!res.ok) {
      throw new Error('Failed to retrieve user profile');
    }
    const user: User = await res.json();
    // Update cached user
    const token = this.getAuthToken();
    if (token) this.setAuth(token, user);
    return user;
  },

  async logout(): Promise<void> {
    try {
      await this.fetchWithAuth(`${API_BASE_URL}/auth/logout`, { method: 'POST' });
    } finally {
      this.clearAuth();
    }
  },

  async forgotPassword(emailOrUsername: string): Promise<{ success: boolean; message: string; reset_token?: string }> {
    const res = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email_or_username: emailOrUsername }),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to request password reset' }));
      throw new Error(errorData.detail || 'Password reset request failed');
    }

    return await res.json();
  },

  async resetPassword(params: { email_or_username: string; new_password: string; reset_token?: string }): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to reset password' }));
      throw new Error(errorData.detail || 'Password reset failed');
    }

    return await res.json();
  },

  // ─── System & Job Reference Endpoints ───

  // Check Backend Health
  async checkHealth(): Promise<{ status: string; llm_active: boolean }> {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (!res.ok) throw new Error('Health check failed');
      return await res.json();
    } catch {
      return { status: 'offline', llm_active: false };
    }
  },

  // Fetch Tailored Demo Roles Generated on Basis of Resume
  async getDemoJobs(resumeId?: string): Promise<DemoJob[]> {
    const url = resumeId
      ? `${API_BASE_URL}/jobs/demo?resume_id=${encodeURIComponent(resumeId)}`
      : `${API_BASE_URL}/jobs/demo`;
    const res = await this.fetchWithAuth(url);
    if (!res.ok) {
      if (res.status === 404) return [];
      throw new Error('Failed to fetch demo jobs');
    }
    return await res.json();
  },

  // Analyze Custom Job Description
  async analyzeJobDescription(jobText: string, title = 'Custom Job'): Promise<DemoJob> {
    const res = await fetch(`${API_BASE_URL}/job/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_text: jobText, title }),
    });

    if (!res.ok) {
      throw new Error('Failed to analyze job description');
    }

    return await res.json();
  },

  // ─── Protected Resume Operations ───

  // Upload Resume File (PDF / DOCX)
  async uploadResume(file: File): Promise<ResumeAnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await this.fetchWithAuth(`${API_BASE_URL}/resume/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(errorData.detail || 'Resume upload failed');
    }

    return await res.json();
  },

  // Analyze Pasted Resume Text or Load Demo Resume
  async analyzeResumeText(text: string, filename = 'Pasted_Resume.txt'): Promise<ResumeAnalysisResponse> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/resume/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: text, filename }),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Analysis failed' }));
      throw new Error(errorData.detail || 'Resume text analysis failed');
    }

    return await res.json();
  },

  // Get Latest Resume from Database (Scoped to Current User)
  async getLatestResume(): Promise<ResumeAnalysisResponse | null> {
    if (!this.isAuthenticated()) return null;
    try {
      const res = await this.fetchWithAuth(`${API_BASE_URL}/resume/latest`);
      if (!res.ok) return null;
      const data = await res.json();
      return {
        resume_id: data.resume_id,
        filename: data.filename,
        health_scores: {
          overall: data.overall_health_score,
          content_quality: data.content_quality_score,
          skills_coverage: data.skills_coverage_score,
          experience_clarity: data.experience_clarity_score,
          project_strength: data.project_strength_score,
          ats_readability: data.ats_readability_score,
        },
        extracted_profile: data.extracted_profile,
        raw_text: data.raw_text,
      };
    } catch {
      return null;
    }
  },

  // Get Resume by ID from Database (Scoped to Current User)
  async getResumeById(resumeId: string): Promise<ResumeAnalysisResponse | null> {
    try {
      const res = await this.fetchWithAuth(`${API_BASE_URL}/resume/${encodeURIComponent(resumeId)}`);
      if (!res.ok) return null;
      const data = await res.json();
      return {
        resume_id: data.resume_id,
        filename: data.filename,
        health_scores: {
          overall: data.overall_health_score,
          content_quality: data.content_quality_score,
          skills_coverage: data.skills_coverage_score,
          experience_clarity: data.experience_clarity_score,
          project_strength: data.project_strength_score,
          ats_readability: data.ats_readability_score,
        },
        extracted_profile: data.extracted_profile,
        raw_text: data.raw_text,
      };
    } catch {
      return null;
    }
  },

  // List All User Resumes
  async getUserResumes(): Promise<any[]> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/resumes`);
    if (!res.ok) return [];
    return await res.json();
  },

  // ─── Protected Matching, Simulation, & Roadmap ───

  // Execute Match Engine
  async matchResumeToJob(params: {
    resume_id?: string;
    resume_profile?: ExtractedProfile;
    resume_text?: string;
    job_id?: string;
    job_description?: string;
    job_title?: string;
  }): Promise<MatchResponse> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Matching engine failed' }));
      throw new Error(errorData.detail || 'Match computation failed');
    }

    return await res.json();
  },

  // Execute Career What-If Simulation
  async simulateCareer(params: SimulateRequest): Promise<SimulateResponse> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/career/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Simulation failed' }));
      throw new Error(errorData.detail || 'Career simulation failed');
    }

    return await res.json();
  },

  // Fetch Data-Driven Career Paths
  async getCareerPaths(resumeId?: string): Promise<CareerPathsResponse> {
    const url = resumeId 
      ? `${API_BASE_URL}/career/paths?resume_id=${encodeURIComponent(resumeId)}`
      : `${API_BASE_URL}/career/paths`;

    const res = await this.fetchWithAuth(url);
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to fetch career paths' }));
      throw new Error(errorData.detail || 'Career paths retrieval failed');
    }

    return await res.json();
  },

  // Fetch Personalized Skill Learning Roadmap
  async getSkillRoadmap(params: {
    resume_id: string;
    job_id?: string;
    job_description?: string;
    job_title?: string;
  }): Promise<RoadmapResponse> {
    const searchParams = new URLSearchParams();
    searchParams.append('resume_id', params.resume_id);
    if (params.job_id) searchParams.append('job_id', params.job_id);
    if (params.job_description) searchParams.append('job_description', params.job_description);
    if (params.job_title) searchParams.append('job_title', params.job_title);

    const res = await this.fetchWithAuth(`${API_BASE_URL}/career/roadmap?${searchParams.toString()}`);
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to generate roadmap' }));
      throw new Error(errorData.detail || 'Skill roadmap retrieval failed');
    }

    return await res.json();
  },

  // Update Skill Roadmap Progress
  async updateRoadmapProgress(params: RoadmapProgressUpdateRequest): Promise<RoadmapProgressUpdateResponse> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/career/roadmap/progress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to update progress' }));
      throw new Error(errorData.detail || 'Progress update failed');
    }

    return await res.json();
  },

  // ─── Protected Security Audit Endpoints ───

  // Audit Resume Text or Stored Resume ID
  async auditSecurity(params: SecurityAuditRequest): Promise<SecurityAuditReport> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/security/audit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Security audit request failed' }));
      throw new Error(errorData.detail || 'Security audit failed');
    }

    return await res.json();
  },

  // Direct Document Security Audit (PDF / DOCX / TXT)
  async auditFileUpload(file: File): Promise<SecurityAuditReport> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await this.fetchWithAuth(`${API_BASE_URL}/security/audit/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Document security audit failed' }));
      throw new Error(errorData.detail || 'Document security audit failed');
    }

    return await res.json();
  },

  // Fetch Latest Security Audit
  async getLatestSecurityAudit(): Promise<SecurityAuditReport | null> {
    if (!this.isAuthenticated()) return null;
    try {
      const res = await this.fetchWithAuth(`${API_BASE_URL}/security/audit/latest`);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },

  // Fetch Security Audit by Resume ID
  async getSecurityAuditByResumeId(resumeId: string): Promise<SecurityAuditReport> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/security/audit/${encodeURIComponent(resumeId)}`);
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to fetch security audit' }));
      throw new Error(errorData.detail || 'Security audit retrieval failed');
    }
    return await res.json();
  },

  // ─── Stage 4: Interview Preparation Endpoints ───

  // Create Personalized Interview Session
  async createInterviewSession(params: CreateInterviewSessionRequest): Promise<InterviewSessionResponse> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/interview/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to create interview session' }));
      throw new Error(errorData.detail || 'Session creation failed');
    }

    return await res.json();
  },

  // List User's Interview Sessions
  async listInterviewSessions(): Promise<InterviewSessionSummary[]> {
    if (!this.isAuthenticated()) return [];
    const res = await this.fetchWithAuth(`${API_BASE_URL}/interview/sessions`);
    if (!res.ok) {
      if (res.status === 401) return [];
      const errorData = await res.json().catch(() => ({ detail: 'Failed to fetch interview sessions' }));
      throw new Error(humanizeErrorMessage(errorData.detail || 'Session list retrieval failed'));
    }
    return await res.json();
  },

  // Get Single Interview Session with Questions & Answers
  async getInterviewSession(sessionId: string): Promise<InterviewSessionResponse> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/interview/session/${encodeURIComponent(sessionId)}`);
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to fetch interview session' }));
      throw new Error(errorData.detail || 'Session retrieval failed');
    }
    return await res.json();
  },

  // Delete Interview Session
  async deleteInterviewSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/interview/session/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to delete interview session' }));
      throw new Error(errorData.detail || 'Session deletion failed');
    }
    return await res.json();
  },

  // Submit Practice Answer & Receive Rubric-Grounded Evaluation
  async submitInterviewAnswer(sessionId: string, params: SubmitAnswerRequest): Promise<AnswerEvaluationResponse> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/interview/session/${encodeURIComponent(sessionId)}/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to evaluate answer' }));
      throw new Error(errorData.detail || 'Answer evaluation failed');
    }

    return await res.json();
  },

  // Get Saved Answer Evaluation for Question
  async getInterviewAnswer(sessionId: string, questionId: string): Promise<AnswerEvaluationResponse | null> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/interview/session/${encodeURIComponent(sessionId)}/question/${encodeURIComponent(questionId)}/answer`);
    if (!res.ok) {
      return null;
    }
    return await res.json();
  },

  // ─── Stage 5: Fairness Audit Endpoints ───

  // Execute Counterfactual Fairness Audit Suite
  async runFairnessAudit(): Promise<FairnessAuditReport> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/fairness/audit`, {
      method: 'POST',
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Fairness audit execution failed' }));
      throw new Error(humanizeErrorMessage(errorData.detail || 'Fairness audit failed'));
    }

    return await res.json();
  },

  // List Saved Fairness Audits for Current User
  async listFairnessAudits(): Promise<FairnessAuditSummary[]> {
    if (!this.isAuthenticated()) return [];
    const res = await this.fetchWithAuth(`${API_BASE_URL}/fairness/audits`);
    if (!res.ok) {
      if (res.status === 401) return [];
      const errorData = await res.json().catch(() => ({ detail: 'Failed to retrieve fairness audits' }));
      throw new Error(humanizeErrorMessage(errorData.detail || 'Fairness audits retrieval failed'));
    }
    return await res.json();
  },

  // Fetch Latest Fairness Audit
  async getLatestFairnessAudit(): Promise<FairnessAuditReport | null> {
    if (!this.isAuthenticated()) return null;
    try {
      const res = await this.fetchWithAuth(`${API_BASE_URL}/fairness/audit/latest`);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },

  // Get Specific Fairness Audit by ID
  async getFairnessAudit(auditId: string): Promise<FairnessAuditReport> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/fairness/audit/${encodeURIComponent(auditId)}`);
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to retrieve fairness audit' }));
      throw new Error(errorData.detail || 'Fairness audit retrieval failed');
    }
    return await res.json();
  },

  // Delete Fairness Audit Record
  async deleteFairnessAudit(auditId: string): Promise<{ status: string; message: string }> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/fairness/audit/${encodeURIComponent(auditId)}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to delete fairness audit' }));
      throw new Error(errorData.detail || 'Fairness audit deletion failed');
    }
    return await res.json();
  },

  // Get Scoring Policy, Weights, & Documented Tolerances
  async getFairnessPolicy(): Promise<ScoringPolicySummary> {
    const res = await this.fetchWithAuth(`${API_BASE_URL}/fairness/policy`);
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Failed to retrieve scoring policy' }));
      throw new Error(errorData.detail || 'Scoring policy retrieval failed');
    }
    return await res.json();
  },
};

