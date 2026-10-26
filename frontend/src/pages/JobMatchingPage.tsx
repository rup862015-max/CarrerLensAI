import React, { useState, useEffect } from 'react';
import { 
  Target, 
  Sparkles, 
  Loader2, 
  AlertCircle, 
  CheckCircle2 
} from 'lucide-react';
import { DemoJob, MatchResponse, ResumeAnalysisResponse, TabType } from '../types';
import { apiService } from '../services/api';
import { MatchResultView } from '../components/MatchResultView';

interface JobMatchingPageProps {
  currentAnalysis: ResumeAnalysisResponse | null;
  onOpenPhase2: (title: string, desc: string, items: string[]) => void;
  onNavigate?: (tab: TabType) => void;
}

export const JobMatchingPage: React.FC<JobMatchingPageProps> = ({
  currentAnalysis,
  onOpenPhase2,
  onNavigate,
}) => {
  const [demoJobs, setDemoJobs] = useState<DemoJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>('');
  const [customJobTitle, setCustomJobTitle] = useState<string>('');
  const [customJobText, setCustomJobText] = useState<string>('');
  const [matchingMode, setMatchingMode] = useState<'demo' | 'custom'>('demo');
  
  const [isMatching, setIsMatching] = useState<boolean>(false);
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch tailored demo roles generated on basis of active resume
  useEffect(() => {
    const fetchDemoJobs = async () => {
      try {
        const jobs = await apiService.getDemoJobs(currentAnalysis?.resume_id);
        setDemoJobs(jobs);
        if (jobs.length > 0) {
          setSelectedJobId(prev => (jobs.some(j => j.id === prev) ? prev : jobs[0].id));
        } else {
          setSelectedJobId('');
        }
      } catch (err) {
        console.error('Failed to load tailored demo jobs:', err);
        setDemoJobs([]);
      }
    };
    fetchDemoJobs();
  }, [currentAnalysis?.resume_id]);

  const handleRunMatch = async (jobIdToUse?: string) => {
    if (!currentAnalysis) {
      setErrorMessage('No resume analyzed yet. Please upload or analyze your resume before running job matching.');
      return;
    }

    setIsMatching(true);
    setErrorMessage(null);

    try {
      const params: any = {
        resume_id: currentAnalysis.resume_id,
        resume_profile: currentAnalysis.extracted_profile,
        resume_text: currentAnalysis.raw_text,
      };

      if (matchingMode === 'demo') {
        const targetId = jobIdToUse || selectedJobId || (demoJobs[0] ? demoJobs[0].id : undefined);
        if (!targetId) {
          setErrorMessage('Please select a target role or paste a custom job description.');
          setIsMatching(false);
          return;
        }
        params.job_id = targetId;
      } else {
        if (!customJobText.trim()) {
          setErrorMessage('Please paste a job description text to run matching.');
          setIsMatching(false);
          return;
        }
        params.job_description = customJobText;
        params.job_title = customJobTitle.trim() || 'Custom Job Position';
      }

      const result = await apiService.matchResumeToJob(params);
      setMatchResult(result);
    } catch (err: any) {
      setErrorMessage(err.message || 'Matching engine failed.');
    } finally {
      setIsMatching(false);
    }
  };

  // Run initial match on page load ONLY if tailored demo jobs and genuine analyzed resume are available
  useEffect(() => {
    if (demoJobs.length > 0 && currentAnalysis && !matchResult) {
      handleRunMatch(demoJobs[0].id);
    }
  }, [demoJobs, currentAnalysis]);

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Page Header */}
      <div>
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 text-xs font-semibold mb-2">
          <Target className="w-3.5 h-3.5" />
          <span>Explainable AI Matching Engine</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
          Job Matching & Explainability Audit
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Evaluate multi-layer alignment between your verified profile and target technical requirements.
        </p>
      </div>

      {/* Extraction Warning Banner if resume had extraction issues */}
      {currentAnalysis && currentAnalysis.warnings && currentAnalysis.warnings.length > 0 && (
        <div className={`p-4 rounded-2xl border flex items-start space-x-3 text-xs ${
          currentAnalysis.extraction_status === 'partial'
            ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
        }`}>
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-bold text-white block">Ingestion Integrity Notice</span>
            <span>Some sections in this resume may not have been fully extracted. Matching evaluates verified source evidence.</span>
          </div>
        </div>
      )}

      {/* No Resume Notice */}
      {!currentAnalysis && (
        <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-between text-xs text-indigo-300">
          <div className="flex items-center space-x-3">
            <AlertCircle className="w-4 h-4 shrink-0 text-indigo-400" />
            <span>No active resume loaded. Please upload or analyze your resume in the Resume Analysis tab before matching against roles.</span>
          </div>
        </div>
      )}

      {/* Mode Switcher & Job Selector */}
      <div className="p-6 sm:p-8 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Select Matching Source:
            </span>
          </div>

          <div className="flex items-center space-x-2 bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              type="button"
              onClick={() => setMatchingMode('demo')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                matchingMode === 'demo'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Roles Generated for Your Resume
            </button>
            <button
              type="button"
              onClick={() => setMatchingMode('custom')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                matchingMode === 'custom'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Paste Custom Job Description
            </button>
          </div>
        </div>

        {matchingMode === 'demo' ? (
          /* Option: Tailored Demo Roles */
          <div className="space-y-4">
            <span className="text-xs font-semibold text-slate-300">
              Select one of the tailored benchmark roles generated on the basis of your resume:
            </span>

            {demoJobs.length === 0 ? (
              <div className="p-8 text-center rounded-2xl bg-slate-950/40 border border-dashed border-slate-800 space-y-3">
                <Sparkles className="w-8 h-8 text-indigo-400 mx-auto" />
                <h4 className="text-sm font-semibold text-white">No Resume Provided Yet</h4>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Upload or analyze your resume in the Resume Analysis tab. We will dynamically generate tailored demo roles specifically suited to your background, skills, and experience level.
                </p>
                {onNavigate && (
                  <button
                    onClick={() => onNavigate('resume-analysis')}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition-colors"
                  >
                    Go to Resume Analysis
                  </button>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {demoJobs.map((job) => {
                  const isSelected = selectedJobId === job.id;
                  return (
                    <div
                      key={job.id}
                      onClick={() => {
                        setSelectedJobId(job.id);
                        handleRunMatch(job.id);
                      }}
                      className={`p-5 rounded-2xl border cursor-pointer transition-all space-y-3 relative group ${
                        isSelected
                          ? 'bg-indigo-600/15 border-indigo-500 shadow-lg shadow-indigo-500/10'
                          : 'bg-slate-800/40 border-slate-700/60 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                          {job.department}
                        </span>
                        {isSelected && (
                          <span className="flex items-center space-x-1 text-indigo-400 text-xs font-bold">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Active Target</span>
                          </span>
                        )}
                      </div>

                      <div>
                        <h4 className="font-bold text-sm text-white group-hover:text-indigo-300 transition-colors">
                          {job.title}
                        </h4>
                        <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{job.description}</p>
                      </div>

                      <div className="pt-2 border-t border-slate-700/40 flex flex-wrap gap-1">
                        {job.requirements.slice(0, 3).map((r, rIdx) => (
                          <span
                            key={rIdx}
                            className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700"
                          >
                            {r.name}
                          </span>
                        ))}
                        {job.requirements.length > 3 && (
                          <span className="px-1.5 py-0.5 text-[10px] text-slate-400">
                            +{job.requirements.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          /* Option 1: Large Textarea for Custom Job Description */
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Job Title (Optional)
              </label>
              <input
                type="text"
                value={customJobTitle}
                onChange={(e) => setCustomJobTitle(e.target.value)}
                placeholder="e.g. Senior Full-Stack AI Engineer"
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Paste Job Description
              </label>
              <textarea
                rows={6}
                value={customJobText}
                onChange={(e) => setCustomJobText(e.target.value)}
                placeholder="Paste the target job description, responsibilities, and requirements here..."
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-4 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono leading-relaxed"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => handleRunMatch()}
                disabled={isMatching || !customJobText.trim()}
                className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-indigo-600/25 transition-all flex items-center space-x-2"
              >
                {isMatching ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Computing Match...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Analyze & Match Custom JD</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center space-x-3 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Matching Progress Spinner */}
      {isMatching && (
        <div className="p-12 rounded-3xl bg-slate-900/40 border border-slate-800 flex flex-col items-center justify-center space-y-4 text-center">
          <Loader2 className="w-10 h-10 text-indigo-400 animate-spin" />
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-white">Running 3-Layer Hybrid Match Engine</h4>
            <p className="text-xs text-slate-400">
              Evaluating exact skills, taxonomy graph, and TF-IDF semantic fit...
            </p>
          </div>
        </div>
      )}

      {/* Explainable Match Results View */}
      {!isMatching && matchResult && (
        <MatchResultView
          matchResult={matchResult}
          onExploreSimulation={() => {
            if (onNavigate) {
              onNavigate('career-simulator');
            } else {
              onOpenPhase2(
                'Career Simulator',
                'Simulate adding new technical competencies to forecast job match improvements.',
                ['Dynamic skill impact simulation', 'Transition trajectory mapping', 'Projected readiness score']
              );
            }
          }}
        />
      )}
    </div>
  );
};
