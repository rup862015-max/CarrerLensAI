import React, { useState, useEffect } from 'react';
import { 
  Target, 
  Sparkles, 
  Loader2, 
  AlertCircle, 
  CheckCircle2 
} from 'lucide-react';
import { DemoJob, MatchResponse, ResumeAnalysisResponse } from '../types';
import { apiService } from '../services/api';
import { MatchResultView } from '../components/MatchResultView';

interface JobMatchingPageProps {
  currentAnalysis: ResumeAnalysisResponse | null;
  onOpenPhase2: (title: string, desc: string, items: string[]) => void;
}

export const JobMatchingPage: React.FC<JobMatchingPageProps> = ({
  currentAnalysis,
  onOpenPhase2,
}) => {
  const [demoJobs, setDemoJobs] = useState<DemoJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>('job-backend-001');
  const [customJobTitle, setCustomJobTitle] = useState<string>('');
  const [customJobText, setCustomJobText] = useState<string>('');
  const [matchingMode, setMatchingMode] = useState<'demo' | 'custom'>('demo');
  
  const [isMatching, setIsMatching] = useState<boolean>(false);
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load demo jobs on mount
  useEffect(() => {
    const fetchDemoJobs = async () => {
      try {
        const jobs = await apiService.getDemoJobs();
        setDemoJobs(jobs);
      } catch {
        // Fallback default demo jobs
        setDemoJobs([
          {
            id: 'job-backend-001',
            title: 'Junior Backend Developer',
            department: 'Engineering',
            location: 'Remote / San Francisco, CA',
            experience_level: 'Entry to Mid',
            description: 'Design and build scalable server-side REST APIs with Python, SQL, and Docker.',
            requirements: [
              { name: 'Python', importance: 'critical', category: 'languages' },
              { name: 'REST APIs', importance: 'critical', category: 'practices' },
              { name: 'SQL', importance: 'critical', category: 'databases' },
              { name: 'Docker', importance: 'critical', category: 'cloud_devops' },
            ],
            education_requirement: "Bachelor's degree in CS/IT",
            responsibilities: ['Develop REST APIs', 'Manage databases'],
          },
          {
            id: 'job-frontend-002',
            title: 'Frontend Developer',
            department: 'UI/UX Engineering',
            location: 'Hybrid / New York, NY',
            experience_level: 'Mid-Level',
            description: 'Build fast, accessible React and TypeScript client applications.',
            requirements: [
              { name: 'React', importance: 'critical', category: 'frameworks' },
              { name: 'TypeScript', importance: 'critical', category: 'languages' },
              { name: 'Tailwind CSS', importance: 'recommended', category: 'frameworks' },
            ],
            education_requirement: "Bachelor's degree in CS",
            responsibilities: ['Build UI components', 'Integrate APIs'],
          },
          {
            id: 'job-data-003',
            title: 'Data Analyst',
            department: 'BI & Analytics',
            location: 'San Francisco, CA',
            experience_level: 'Entry-Level',
            description: 'Extract business insights using SQL, Python, Pandas, and Tableau.',
            requirements: [
              { name: 'SQL', importance: 'critical', category: 'databases' },
              { name: 'Python', importance: 'critical', category: 'languages' },
              { name: 'Tableau', importance: 'critical', category: 'ai_data' },
              { name: 'Pandas', importance: 'critical', category: 'ai_data' },
            ],
            education_requirement: "Bachelor's degree in Statistics/Data Science",
            responsibilities: ['SQL ETL pipelines', 'Tableau dashboards'],
          },
        ]);
      }
    };
    fetchDemoJobs();
  }, []);

  const handleRunMatch = async (jobIdToUse?: string) => {
    setIsMatching(true);
    setErrorMessage(null);

    try {
      let params: any = {};

      if (currentAnalysis) {
        params.resume_id = currentAnalysis.resume_id;
        params.resume_profile = currentAnalysis.extracted_profile;
        params.resume_text = currentAnalysis.raw_text;
      }

      if (matchingMode === 'demo') {
        params.job_id = jobIdToUse || selectedJobId;
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

  // Run initial match on page load if demo jobs available
  useEffect(() => {
    if (demoJobs.length > 0 && !matchResult) {
      handleRunMatch('job-backend-001');
    }
  }, [demoJobs]);

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
              Pre-configured Demo Roles
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
          /* Option 2: 3 Demo Job Cards */
          <div className="space-y-4">
            <span className="text-xs font-semibold text-slate-300">
              Select one of the benchmark roles to compare alignment:
            </span>
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
          onExploreSimulation={() => onOpenPhase2(
            'Career Simulator',
            'Simulate adding new technical competencies to forecast job match improvements.',
            ['Dynamic skill impact simulation', 'Transition trajectory mapping', 'Projected readiness score']
          )}
        />
      )}
    </div>
  );
};
