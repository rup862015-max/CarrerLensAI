import React from 'react';
import { 
  FileSearch, 
  ArrowRight, 
  CheckCircle2, 
  Sparkles,
  AlertTriangle,
  AlertCircle,
  ShieldCheck
} from 'lucide-react';
import { ResumeAnalysisResponse, TabType } from '../types';
import { ResumeUpload } from '../components/ResumeUpload';
import { ScoreRadial } from '../components/ScoreRadial';
import { ExtractedProfileView } from '../components/ExtractedProfileView';

interface ResumeAnalysisPageProps {
  analysisResult: ResumeAnalysisResponse | null;
  onAnalysisComplete: (result: ResumeAnalysisResponse) => void;
  onNavigate: (tab: TabType) => void;
}

export const ResumeAnalysisPage: React.FC<ResumeAnalysisPageProps> = ({
  analysisResult,
  onAnalysisComplete,
  onNavigate,
}) => {
  const healthScores = analysisResult?.health_scores;
  const profile = analysisResult?.extracted_profile;
  const status = analysisResult?.extraction_status || 'success';
  const warnings = analysisResult?.warnings || [];

  const healthBreakdown = healthScores ? [
    { label: 'Content Quality', score: healthScores.content_quality, color: 'bg-indigo-500' },
    { label: 'Skills Coverage', score: healthScores.skills_coverage, color: 'bg-cyan-500' },
    { label: 'Experience Clarity', score: healthScores.experience_clarity, color: 'bg-emerald-500' },
    { label: 'Project Strength', score: healthScores.project_strength, color: 'bg-amber-500' },
    { label: 'ATS Readability', score: healthScores.ats_readability, color: 'bg-purple-500' },
  ] : [];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 text-xs font-semibold mb-2">
            <FileSearch className="w-3.5 h-3.5" />
            <span>AI Parser & Resume Health Audit</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Resume Analysis & Candidate Profiling
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Deep structural analysis, ATS compatibility scoring, and skill entity extraction.
          </p>
        </div>

        {analysisResult && (
          <div className="flex items-center space-x-2.5">
            <button
              type="button"
              onClick={() => onNavigate('security-audit')}
              className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold border border-slate-700 transition-all flex items-center space-x-2"
            >
              <ShieldCheck className="w-4 h-4 text-rose-400" />
              <span>Security Audit</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('job-matching')}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/25 transition-all flex items-center space-x-2"
            >
              <span>Match with Job Openings</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Upload Zone */}
      <div className="p-6 sm:p-8 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-4">
        <ResumeUpload onAnalysisComplete={onAnalysisComplete} />
      </div>

      {/* Analysis Results Display */}
      {analysisResult && profile && (
        <div className="space-y-8 animate-in fade-in duration-300">
          {/* Warnings Banner if present */}
          {warnings.length > 0 && (
            <div className={`p-4 rounded-2xl border flex items-start space-x-3 text-xs ${
              status === 'partial' 
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-300' 
                : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
            }`}>
              {status === 'partial' ? (
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              )}
              <div className="space-y-1">
                <span className="font-bold text-white block">
                  {status === 'partial' ? 'Partial Extraction Notice' : 'Ingestion Notice'}
                </span>
                <ul className="space-y-0.5 list-disc list-inside">
                  {warnings.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Resume Health Section */}
          <div className="p-6 sm:p-8 rounded-3xl bg-slate-900/80 border border-slate-800 shadow-2xl space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400">Analysis Summary for</span>
                <h3 className="text-base font-bold text-white font-mono">{analysisResult.filename}</h3>
              </div>
              
              {status === 'success' && (
                <div className="flex items-center space-x-2 text-emerald-400 text-xs font-bold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Resume Extracted Successfully</span>
                </div>
              )}
              {status === 'warning' && (
                <div className="flex items-center space-x-2 text-amber-400 text-xs font-bold">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Extracted with Warnings</span>
                </div>
              )}
              {status === 'partial' && (
                <div className="flex items-center space-x-2 text-rose-400 text-xs font-bold">
                  <AlertCircle className="w-4 h-4" />
                  <span>Partial Extraction</span>
                </div>
              )}
            </div>

            <ScoreRadial
              score={healthScores?.overall || 82}
              label="Resume Health"
              size="lg"
              subscores={healthBreakdown}
            />
          </div>

          {/* Extracted Profile (Education, Experience, Skills, Projects) */}
          <ExtractedProfileView profile={profile} />

          {/* Bottom Action */}
          <div className="p-6 rounded-2xl bg-gradient-to-r from-indigo-950/40 via-slate-900/60 to-cyan-950/40 border border-indigo-500/30 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="space-y-1 text-center sm:text-left">
              <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Ready for Explainable Job Matching</span>
              </h4>
              <p className="text-xs text-slate-400">
                Compare this candidate profile against backend, frontend, or custom job descriptions.
              </p>
            </div>

            <button
              type="button"
              onClick={() => onNavigate('job-matching')}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/25 transition-all flex items-center space-x-2"
            >
              <span>Launch Matching Engine</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
