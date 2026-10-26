import React from 'react';
import { 
  FileText, 
  Sparkles, 
  CheckCircle2, 
  ArrowRight, 
  Code2, 
  FolderGit2, 
  Briefcase, 
  GraduationCap, 
  Target, 
  Compass, 
  TrendingUp,
  ShieldCheck,
  MessageSquare
} from 'lucide-react';
import { ResumeAnalysisResponse, TabType } from '../types';
import { ScoreRadial } from '../components/ScoreRadial';

interface DashboardPageProps {
  currentAnalysis: ResumeAnalysisResponse | null;
  onNavigate: (tab: TabType) => void;
  onOpenPhase2?: (title: string, desc: string, items: string[]) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  currentAnalysis,
  onNavigate,
}) => {
  const profile = currentAnalysis?.extracted_profile;
  const healthScores = currentAnalysis?.health_scores;

  const healthBreakdown = healthScores ? [
    { label: 'Content Quality', score: healthScores.content_quality, color: 'bg-indigo-500' },
    { label: 'Skills Coverage', score: healthScores.skills_coverage, color: 'bg-cyan-500' },
    { label: 'Experience Clarity', score: healthScores.experience_clarity, color: 'bg-emerald-500' },
    { label: 'Project Strength', score: healthScores.project_strength, color: 'bg-amber-500' },
    { label: 'ATS Readability', score: healthScores.ats_readability, color: 'bg-purple-500' },
  ] : [];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Welcome Section */}
      <div className="p-8 rounded-3xl bg-gradient-to-r from-indigo-950/60 via-slate-900/80 to-slate-900/60 border border-slate-800 shadow-2xl space-y-3 relative overflow-hidden">
        <div className="absolute -top-10 right-0 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
          <span>Explainable Career Intelligence</span>
        </div>

        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
          Your Career Intelligence Dashboard
        </h1>
        <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
          Understand your strengths, identify skill gaps, and discover where your profile fits in the technical job market with explainable AI evidence.
        </p>
      </div>

      {/* Empty State: No Resume Analyzed */}
      {!currentAnalysis && (
        <div className="p-10 rounded-3xl bg-slate-900/60 border border-dashed border-slate-700 text-center space-y-5">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
            <FileText className="w-8 h-8" />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-white">No Resume Analyzed Yet</h2>
            <p className="text-sm text-slate-400 max-w-md mx-auto">
              Upload or paste your resume to get started with AI-powered career intelligence, health scoring, and job matching.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate('resume-analysis')}
            className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors shadow-lg shadow-indigo-500/20"
          >
            <span>Upload Your Resume</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Data-Driven Content: Only shown when analysis exists */}
      {currentAnalysis && (
        <>
          {/* Profile Overview Metrics Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-bold uppercase tracking-wider">Skills</span>
                <Code2 className="w-4 h-4 text-indigo-400" />
              </div>
              <p className="text-2xl font-black text-white">{profile?.skills?.length ?? 0}</p>
              <p className="text-[11px] text-slate-400">Categorized in taxonomy</p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-bold uppercase tracking-wider">Projects</span>
                <FolderGit2 className="w-4 h-4 text-cyan-400" />
              </div>
              <p className="text-2xl font-black text-white">{profile?.projects?.length ?? 0}</p>
              <p className="text-[11px] text-slate-400">With verified deliverables</p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-bold uppercase tracking-wider">Experience</span>
                <Briefcase className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-2xl font-black text-white">{profile?.years_of_experience ?? 0} Years</p>
              <p className="text-[11px] text-slate-400">Professional timeline</p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-bold uppercase tracking-wider">Education</span>
                <GraduationCap className="w-4 h-4 text-amber-400" />
              </div>
              <p className="text-base font-bold text-white truncate">
                {profile?.education && profile.education.length > 0 ? profile.education[0].split('|')[0].trim() : 'N/A'}
              </p>
              <p className="text-[11px] text-slate-400">Accredited degree</p>
            </div>
          </div>

          {/* Main Grid: Status Card & Resume Health */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Active Resume Status */}
            <div className="lg:col-span-5 space-y-6">
              <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <FileText className="w-5 h-5 text-indigo-400" />
                    <h3 className="text-base font-bold text-white">Active Resume</h3>
                  </div>
                  <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center space-x-1">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>Analyzed</span>
                  </span>
                </div>

                <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-700/60 space-y-3">
                  <p className="text-xs font-mono font-bold text-indigo-300 break-all">
                    {currentAnalysis.filename}
                  </p>
                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>Status: <strong>Analyzed & Indexed</strong></span>
                    <span>Last analyzed: <strong>Today</strong></span>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => onNavigate('resume-analysis')}
                    className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors flex items-center justify-center space-x-2"
                  >
                    <span>Upload or Re-scan Resume</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Recommended Actions */}
              <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">
                  Recommended Next Steps
                </h3>

                <div className="space-y-2.5">
                  <button
                    onClick={() => onNavigate('job-matching')}
                    className="w-full p-3.5 rounded-2xl bg-slate-800/50 hover:bg-indigo-600/15 border border-slate-700/80 hover:border-indigo-500/40 text-left transition-all flex items-center justify-between group"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                        <Target className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-white group-hover:text-indigo-300 block">
                          Analyze a Job Description
                        </span>
                        <span className="text-[11px] text-slate-400">Compare against Backend, Frontend, or Data roles</span>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
                  </button>

                  <button
                    onClick={() => onNavigate('job-matching')}
                    className="w-full p-3.5 rounded-2xl bg-slate-800/50 hover:bg-indigo-600/15 border border-slate-700/80 hover:border-indigo-500/40 text-left transition-all flex items-center justify-between group"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
                        <TrendingUp className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-white group-hover:text-cyan-300 block">
                          Review Skill Gaps & Explainability
                        </span>
                        <span className="text-[11px] text-slate-400">Inspect verified evidence from projects & experience</span>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 group-hover:translate-x-1 transition-all" />
                  </button>

                  <button
                    onClick={() => onNavigate('career-simulator')}
                    className="w-full p-3.5 rounded-2xl bg-slate-800/50 hover:bg-indigo-600/15 border border-slate-700/80 hover:border-indigo-500/40 text-left transition-all flex items-center justify-between group"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
                        <Compass className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-white group-hover:text-amber-300 block">
                          Explore Career Simulation
                        </span>
                        <span className="text-[11px] text-slate-400">Forecast path evolution & skill additions</span>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-amber-400 group-hover:translate-x-1 transition-all" />
                  </button>

                  <button
                    onClick={() => onNavigate('security-audit')}
                    className="w-full p-3.5 rounded-2xl bg-slate-800/50 hover:bg-indigo-600/15 border border-slate-700/80 hover:border-indigo-500/40 text-left transition-all flex items-center justify-between group"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-xl bg-rose-500/10 text-rose-400 flex items-center justify-center">
                        <ShieldCheck className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-white group-hover:text-rose-300 block">
                          Resume Security & Injection Audit
                        </span>
                        <span className="text-[11px] text-slate-400">Inspect for prompt injection & hidden characters</span>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-rose-400 group-hover:translate-x-1 transition-all" />
                  </button>

                  <button
                    onClick={() => onNavigate('interview')}
                    className="w-full p-3.5 rounded-2xl bg-slate-800/50 hover:bg-indigo-600/15 border border-slate-700/80 hover:border-indigo-500/40 text-left transition-all flex items-center justify-between group"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                        <MessageSquare className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-white group-hover:text-indigo-300 block">
                          Personalized Interview Preparation
                        </span>
                        <span className="text-[11px] text-slate-400">Practice questions grounded in your resume & job gaps</span>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
                  </button>
                </div>
              </div>
            </div>

            {/* Right Column: Resume Health Score Radial & Breakdown */}
            <div className="lg:col-span-7 space-y-6">
              <div className="p-6 sm:p-8 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-white">Current Profile Health</h3>
                    <p className="text-xs text-slate-400">Calculated from structural and semantic analysis</p>
                  </div>
                  <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full">
                    ATS Optimized
                  </span>
                </div>

                <ScoreRadial
                  score={healthScores?.overall ?? 0}
                  label="Resume Health"
                  size="lg"
                  subscores={healthBreakdown}
                />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
