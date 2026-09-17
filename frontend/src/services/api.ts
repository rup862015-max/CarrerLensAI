/**
 * API Service for CareerLens AI Frontend
 * Interacts with FastAPI backend at http://localhost:8000
 */

import { ResumeAnalysisResponse, DemoJob, MatchResponse, ExtractedProfile } from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

export const apiService = {
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

  // Fetch 3 Demo Jobs
  async getDemoJobs(): Promise<DemoJob[]> {
    const res = await fetch(`${API_BASE_URL}/jobs/demo`);
    if (!res.ok) throw new Error('Failed to fetch demo jobs');
    return await res.json();
  },

  // Upload Resume File (PDF / DOCX)
  async uploadResume(file: File): Promise<ResumeAnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE_URL}/resume/upload`, {
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
    const res = await fetch(`${API_BASE_URL}/resume/analyze`, {
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

  // Get Latest Resume from Database
  async getLatestResume(): Promise<ResumeAnalysisResponse | null> {
    try {
      const res = await fetch(`${API_BASE_URL}/resume/latest`);
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

  // Execute Match Engine
  async matchResumeToJob(params: {
    resume_id?: string;
    resume_profile?: ExtractedProfile;
    resume_text?: string;
    job_id?: string;
    job_description?: string;
    job_title?: string;
  }): Promise<MatchResponse> {
    const res = await fetch(`${API_BASE_URL}/match`, {
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
};
