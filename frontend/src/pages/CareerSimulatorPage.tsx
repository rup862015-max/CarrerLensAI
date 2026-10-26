import React, { useState, useEffect } from 'react';
import { 
  Compass, 
  Sparkles, 
  Plus, 
  X, 
  Play, 
  RotateCcw, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  HelpCircle, 
  TrendingUp, 
  ArrowRight, 
  Briefcase,
  Layers,
  ChevronRight,
  Info
} from 'lucide-react';
import { 
  DemoJob, 
  ResumeAnalysisResponse, 
  SimulateResponse, 
  CareerPathsResponse,
  TabType 
} from '../types';
import { apiService } from '../services/api';

interface CareerSimulatorPageProps {
  currentAnalysis: ResumeAnalysisResponse | null;
  onNavigate: (tab: TabType) => void;
}

export const CareerSimulatorPage: React.FC<CareerSimulatorPageProps> = ({
  currentAnalysis,
  onNavigate,
}) => {
  const [demoJobs, setDemoJobs] = useState<DemoJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>('job-backend-001');
  const [customJobTitle, setCustomJobTitle] = useState<string>('');
  const [customJobText, setCustomJobText] = useState<string>('');
  const [jobMode, setJobMode] = useState<'demo' | 'custom'>('demo');

  // Hypothetical Skills State
  const [hypotheticalSkills, setHypotheticalSkills] = useState<string[]>(['Docker']);
  const [newSkillInput, setNewSkillInput] = useState<string>('');

  // Simulation execution state
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<SimulateResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Alternative Career Paths State
  const [careerPaths, setCareerPaths] = useState<CareerPathsResponse | null>(null);
  const [isLoadingPaths, setIsLoadingPaths] = useState<boolean>(false);

  // Load tailored demo roles & initial baseline simulation
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const jobs = await apiService.getDemoJobs(currentAnalysis?.resume_id);
        setDemoJobs(jobs);
        if (jobs.length > 0) {
          setSelectedJobId(prev => (jobs.some(j => j.id === prev) ? prev : jobs[0].id));
        }
      } catch (err) {
        console.error('Failed to load tailored demo jobs:', err);
      }
    };
    fetchJobs();
  }, [currentAnalysis?.resume_id]);

  // Fetch career paths when current analysis changes
  useEffect(() => {
    if (!currentAnalysis) return;
    const fetchPaths = async () => {
      setIsLoadingPaths(true);
      try {
        const paths = await apiService.getCareerPaths(currentAnalysis.resume_id);
        setCareerPaths(paths);
      } catch (err) {
        console.error('Failed to fetch career paths:', err);
      } finally {
        setIsLoadingPaths(false);
      }
    };
    fetchPaths();
  }, [currentAnalysis]);

  // Selected Job Object
  const currentSelectedJob = demoJobs.find(j => j.id === selectedJobId) || demoJobs[0];

  // Helper to add skill
  const handleAddSkill = (skillToAdd: string) => {
    const clean = skillToAdd.trim();
    if (!clean) return;
    if (hypotheticalSkills.some(s => s.toLowerCase() === clean.toLowerCase())) {
      return;
    }
    // Also avoid adding if already verified in resume
    const verifiedSkills = currentAnalysis?.extracted_profile?.skills || [];
    if (verifiedSkills.some(s => s.toLowerCase() === clean.toLowerCase())) {
      setErrorMessage(`'${clean}' is already verified in candidate resume.`);
      setTimeout(() => setErrorMessage(null), 3500);
      return;
    }
    setHypotheticalSkills(prev => [...prev, clean]);
    setNewSkillInput('');
  };

  // Helper to remove skill
  const handleRemoveSkill = (skillToRemove: string) => {
    setHypotheticalSkills(prev => prev.filter(s => s.toLowerCase() !== skillToRemove.toLowerCase()));
  };

  // Execute What-If Simulation
  const handleRunSimulation = async () => {
    if (isSimulating) return; // Prevent duplicate requests
    setErrorMessage(null);
    setIsSimulating(true);

    try {
      const payload: any = {
        hypothetical_skills: hypotheticalSkills,
      };

      if (currentAnalysis?.resume_id) {
        payload.resume_id = currentAnalysis.resume_id;
      } else if (currentAnalysis?.extracted_profile) {
        payload.resume_profile = currentAnalysis.extracted_profile;
        payload.resume_text = currentAnalysis.raw_text;
      }

      if (jobMode === 'demo') {
        payload.job_id = selectedJobId;
      } else {
        if (!customJobText.trim() || customJobText.trim().length < 15) {
          throw new Error('Please enter a detailed custom job description (min 15 characters).');
        }
        payload.job_description = customJobText;
        payload.job_title = customJobTitle.trim() || 'Custom Position';
      }

      const res = await apiService.simulateCareer(payload);
      setSimulationResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Simulation execution failed. Please check your inputs.');
    } finally {
      setIsSimulating(false);
    }
  };

  // Reset Simulation
  const handleResetSimulation = () => {
    setHypotheticalSkills([]);
    setSimulationResult(null);
    setErrorMessage(null);
  };

  // Available quick gaps to add based on current job requirements
  const candidateSkills = (currentAnalysis?.extracted_profile?.skills || []).map(s => s.toLowerCase());
  const missingJobRequirements = (currentSelectedJob?.requirements || []).filter(
    r => !candidateSkills.includes(r.name.toLowerCase()) && 
         !hypotheticalSkills.some(hs => hs.toLowerCase() === r.name.toLowerCase())
  );

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-indigo-500/30 p-6 sm:p-8 shadow-xl">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-xl bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shadow-inner">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                Career What-If Simulator
              </h1>
              <p className="text-sm text-slate-400 mt-1 max-w-2xl">
                Simulate acquiring hypothetical competencies against target jobs using the genuine matching engine.
                Evidence remains transparently partitioned—hypothetical skills are never conflated with verified resume portfolio evidence.
              </p>
            </div>
          </div>

          {currentAnalysis && (
            <div className="flex items-center space-x-2 bg-slate-800/80 border border-slate-700/80 px-3.5 py-2 rounded-xl text-xs">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-slate-300">
                Active Resume: <strong className="text-white">{currentAnalysis.extracted_profile?.candidate_name || currentAnalysis.filename}</strong>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* No Resume Active Alert */}
      {!currentAnalysis && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start justify-between gap-3">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-amber-300">No Candidate Resume Loaded</p>
              <p className="text-xs text-slate-400 mt-0.5">
                The Career Simulator requires a real candidate profile to evaluate baseline suitability and score deltas.
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('resume-analysis')}
            className="text-xs px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 font-medium transition-colors shrink-0"
          >
            Upload Resume
          </button>
        </div>
      )}

      {/* Configuration Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Target Role & Skill Controls (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Target Job Selector */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Briefcase className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">1. Select Target Job</h2>
              </div>
              <div className="flex bg-slate-800 p-0.5 rounded-lg border border-slate-700 text-[11px]">
                <button
                  onClick={() => setJobMode('demo')}
                  className={`px-2.5 py-1 rounded-md transition-colors ${jobMode === 'demo' ? 'bg-indigo-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  Benchmark Jobs
                </button>
                <button
                  onClick={() => setJobMode('custom')}
                  className={`px-2.5 py-1 rounded-md transition-colors ${jobMode === 'custom' ? 'bg-indigo-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  Custom Role
                </button>
              </div>
            </div>

            {jobMode === 'demo' ? (
              <div className="space-y-2">
                {demoJobs.map(job => (
                  <div
                    key={job.id}
                    onClick={() => setSelectedJobId(job.id)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all ${
                      selectedJobId === job.id
                        ? 'bg-indigo-600/15 border-indigo-500/60 shadow-sm shadow-indigo-500/10'
                        : 'bg-slate-800/40 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-white">{job.title}</span>
                      <span className="text-[10px] text-indigo-300 font-medium px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                        {job.requirements.length} Reqs
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-1">{job.description}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Target Role Title (e.g. Senior DevOps Specialist)"
                  value={customJobTitle}
                  onChange={(e) => setCustomJobTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800/70 border border-slate-700 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <textarea
                  placeholder="Paste target job description and key requirements..."
                  rows={4}
                  value={customJobText}
                  onChange={(e) => setCustomJobText(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800/70 border border-slate-700 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}
          </div>

          {/* Hypothetical Skills Studio */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">2. Hypothetical Skills</h2>
              </div>
              <span className="text-xs text-slate-400">{hypotheticalSkills.length} added</span>
            </div>

            <p className="text-xs text-slate-400">
              Add hypothetical competencies you are exploring. The matching engine evaluates these at 80% simulation weight without fabricating portfolio experience.
            </p>

            {/* Input field */}
            <div className="flex space-x-2">
              <input
                type="text"
                placeholder="e.g. Docker, Kubernetes, AWS, GraphQL..."
                value={newSkillInput}
                onChange={(e) => setNewSkillInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddSkill(newSkillInput);
                  }
                }}
                className="flex-1 px-3 py-2 bg-slate-800/70 border border-slate-700 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={() => handleAddSkill(newSkillInput)}
                className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center space-x-1 transition-colors shadow-sm shadow-indigo-600/30"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add</span>
              </button>
            </div>

            {/* Quick Add from Missing Requirements */}
            {missingJobRequirements.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-[11px] font-semibold text-slate-400 flex items-center space-x-1">
                  <span>Quick-Add Missing Role Requirements:</span>
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {missingJobRequirements.slice(0, 6).map(req => (
                    <button
                      key={req.name}
                      onClick={() => handleAddSkill(req.name)}
                      className="group flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs bg-slate-800/80 hover:bg-amber-500/20 text-slate-300 hover:text-amber-300 border border-slate-700/80 hover:border-amber-500/40 transition-all"
                    >
                      <Plus className="w-3 h-3 text-slate-400 group-hover:text-amber-400" />
                      <span>{req.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Active Hypothetical Tags List */}
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <span className="text-xs font-semibold text-slate-400">Current Hypothetical Set:</span>
              {hypotheticalSkills.length === 0 ? (
                <div className="p-4 rounded-xl bg-slate-800/30 border border-dashed border-slate-700/60 text-center text-xs text-slate-400">
                  No hypothetical skills selected. Add skills above to test match improvements.
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {hypotheticalSkills.map(skill => (
                    <div
                      key={skill}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-indigo-950/70 border border-indigo-500/40 text-xs text-indigo-200 shadow-sm"
                    >
                      <Sparkles className="w-3 h-3 text-indigo-400" />
                      <span className="font-medium">{skill}</span>
                      <button
                        onClick={() => handleRemoveSkill(skill)}
                        className="p-0.5 hover:bg-indigo-800/50 rounded-full transition-colors text-indigo-300 hover:text-white"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Error Message Alert */}
            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2 text-xs text-rose-300">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center space-x-3 pt-2">
              <button
                onClick={handleRunSimulation}
                disabled={isSimulating || !currentAnalysis}
                className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-semibold text-xs flex items-center justify-center space-x-2 shadow-lg shadow-indigo-500/25 disabled:opacity-50 transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                {isSimulating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Executing Simulation Engine...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    <span>Simulate What-If Impact</span>
                  </>
                )}
              </button>

              <button
                onClick={handleResetSimulation}
                disabled={isSimulating}
                className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 transition-colors"
                title="Reset simulation"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Simulation Output & Diff Breakdown (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {!simulationResult && !isSimulating && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-10 text-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
                <Compass className="w-8 h-8" />
              </div>
              <div className="max-w-md mx-auto space-y-2">
                <h3 className="text-base font-bold text-white">Simulation Engine Ready</h3>
                <p className="text-xs text-slate-400">
                  Select your target job, add one or more hypothetical skills, and run the simulator to view evidence-grounded score deltas and requirement-level changes.
                </p>
              </div>
              <button
                onClick={handleRunSimulation}
                disabled={!currentAnalysis}
                className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/40 text-xs font-semibold transition-colors"
              >
                <Play className="w-3.5 h-3.5 fill-indigo-300" />
                <span>Run Initial Simulation ({hypotheticalSkills.join(', ') || 'Baseline'})</span>
              </button>
            </div>
          )}

          {isSimulating && (
            <div className="bg-slate-900/80 border border-indigo-500/30 rounded-2xl p-12 text-center space-y-4">
              <Loader2 className="w-10 h-10 text-indigo-400 animate-spin mx-auto" />
              <div>
                <h3 className="text-base font-bold text-white">Calculating Genuine Score Delta</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Re-evaluating job requirements against centralized matching weights...
                </p>
              </div>
            </div>
          )}

          {simulationResult && !isSimulating && (
            <div className="space-y-6">
              {/* Score Delta Hero Banner */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
                  {/* Baseline vs Simulated */}
                  <div className="flex items-center space-x-6">
                    <div className="text-center">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">Baseline</span>
                      <div className="text-3xl font-extrabold text-slate-300 mt-1">{simulationResult.baseline_score}%</div>
                      <span className="text-xs font-semibold text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                        Grade {simulationResult.baseline_grade}
                      </span>
                    </div>

                    <ArrowRight className="w-6 h-6 text-indigo-400" />

                    <div className="text-center">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-400 block">Simulated</span>
                      <div className="text-3xl font-extrabold text-cyan-300 mt-1">{simulationResult.simulated_score}%</div>
                      <span className="text-xs font-semibold text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/40">
                        Grade {simulationResult.simulated_grade}
                      </span>
                    </div>
                  </div>

                  {/* Delta Highlight */}
                  <div className="flex flex-col items-center sm:items-end">
                    <div className={`px-4 py-2 rounded-2xl flex items-center space-x-2 border shadow-lg ${
                      simulationResult.score_delta > 0 
                        ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 shadow-emerald-500/10'
                        : 'bg-slate-800/80 border-slate-700 text-slate-400'
                    }`}>
                      <TrendingUp className="w-5 h-5" />
                      <span className="text-xl font-bold">
                        {simulationResult.score_delta > 0 ? `+${simulationResult.score_delta}` : `${simulationResult.score_delta}`} Pts
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1.5">
                      {simulationResult.closed_gaps.length} requirement gap(s) closed
                    </span>
                  </div>
                </div>

                {/* Subscore Breakdown Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-6 pt-5 border-t border-slate-800">
                  <div className="p-2.5 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Skill Match (40%)</span>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs font-semibold text-white">
                        {simulationResult.subscore_deltas.skill_match.simulated}%
                      </span>
                      <span className={`text-[10px] font-bold ${
                        simulationResult.subscore_deltas.skill_match.delta > 0 ? 'text-emerald-400' : 'text-slate-400'
                      }`}>
                        +{simulationResult.subscore_deltas.skill_match.delta}%
                      </span>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Experience (20%)</span>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs font-semibold text-white">
                        {simulationResult.subscore_deltas.experience_match.simulated}%
                      </span>
                      <span className="text-[10px] font-bold text-slate-500">Unchanged</span>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Projects (20%)</span>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs font-semibold text-white">
                        {simulationResult.subscore_deltas.project_relevance.simulated}%
                      </span>
                      <span className="text-[10px] font-bold text-slate-500">Unchanged</span>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Education (10%)</span>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs font-semibold text-white">
                        {simulationResult.subscore_deltas.education_match.simulated}%
                      </span>
                      <span className="text-[10px] font-bold text-slate-500">Unchanged</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Simulation Policy & Grounding Notice */}
              <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/20 flex items-start space-x-3">
                <Info className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                <div className="space-y-1 text-xs">
                  <p className="font-semibold text-indigo-200">Simulation Policy & Evidence Rules</p>
                  <p className="text-slate-400 leading-relaxed">
                    {simulationResult.simulation_policy.policy_description}
                  </p>
                </div>
              </div>

              {/* Requirement-Level Diff Breakdown */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Layers className="w-4 h-4 text-cyan-400" />
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                      Requirement-Level Impact Breakdown
                    </h3>
                  </div>
                  <span className="text-xs text-slate-400">
                    {simulationResult.requirement_deltas.length} evaluated
                  </span>
                </div>

                <div className="space-y-3">
                  {simulationResult.requirement_deltas.map((req, idx) => {
                    const isChanged = req.status_changed;
                    const isHypo = req.simulated_status === 'hypothetical';
                    const isVerified = req.evidence_type === 'verified_resume';

                    return (
                      <div 
                        key={idx}
                        className={`p-3.5 rounded-xl border transition-all ${
                          isChanged 
                            ? 'bg-indigo-950/40 border-indigo-500/40 shadow-sm shadow-indigo-500/10'
                            : isVerified 
                              ? 'bg-slate-800/40 border-slate-800' 
                              : 'bg-slate-900/40 border-slate-800/60 opacity-80'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1">
                            <div className="flex items-center space-x-2">
                              <span className="text-sm font-semibold text-white">{req.requirement}</span>
                              <span className="text-[10px] uppercase font-bold text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">
                                {req.importance}
                              </span>
                            </div>

                            {/* Scoring explanation */}
                            <p className="text-xs text-slate-300 leading-relaxed">
                              {req.scoring_rule}
                            </p>

                            {/* Uncertainty note */}
                            {req.uncertainty_note && (
                              <p className="text-[11px] text-amber-400/90 italic flex items-center space-x-1">
                                <HelpCircle className="w-3 h-3 shrink-0" />
                                <span>{req.uncertainty_note}</span>
                              </p>
                            )}
                          </div>

                          {/* Status Badge */}
                          <div className="shrink-0 text-right space-y-1">
                            {isHypo && (
                              <span className="inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-300 border border-amber-500/30">
                                <Sparkles className="w-2.5 h-2.5" />
                                <span>Hypothetical</span>
                              </span>
                            )}
                            {isVerified && (
                              <span className="inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                                <CheckCircle2 className="w-2.5 h-2.5" />
                                <span>Verified Portfolio</span>
                              </span>
                            )}
                            {req.simulated_status === 'missing' && (
                              <span className="inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 border border-slate-700">
                                <span>Missing</span>
                              </span>
                            )}

                            {isChanged && (
                              <div className="text-[10px] font-bold text-cyan-400">
                                Status Changed
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Dynamic Recommendation */}
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-start space-x-3">
                <TrendingUp className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                <div className="space-y-1 text-xs">
                  <p className="font-semibold text-white">Actionable Transition Recommendation</p>
                  <p className="text-slate-300 leading-relaxed">
                    {simulationResult.recommendation}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Alternative Career Paths Exploration Section */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Compass className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-bold text-white tracking-tight">
                Alternative Career Trajectory Alignment
              </h2>
            </div>
            <p className="text-xs text-slate-400">
              Evaluated across benchmark industry roles using genuine matching logic and verified candidate taxonomy relationships.
            </p>
          </div>
          {careerPaths && (
            <span className="text-xs font-semibold text-slate-400 bg-slate-800 px-3 py-1 rounded-lg border border-slate-700">
              Best Fit: <strong className="text-indigo-300">{careerPaths.best_fit}</strong>
            </span>
          )}
        </div>

        {isLoadingPaths ? (
          <div className="py-8 text-center text-xs text-slate-400 flex items-center justify-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
            <span>Analyzing career trajectories...</span>
          </div>
        ) : !careerPaths || careerPaths.paths.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-500">
            No candidate profile loaded to generate trajectory comparisons.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {careerPaths.paths.map(path => (
              <div 
                key={path.role_id}
                className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/80 hover:border-indigo-500/40 transition-all space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-white">{path.role_title}</h3>
                    <span className="text-[11px] text-slate-400">Readiness: {path.readiness}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-lg font-black text-cyan-400">{path.overall_score}%</span>
                    <span className="block text-[10px] text-slate-500 uppercase">{path.match_grade} Grade</span>
                  </div>
                </div>

                {/* Transferable Skills */}
                <div className="space-y-1 text-xs">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">
                    Transferable Skills ({path.transferable_skills.length}):
                  </span>
                  {path.transferable_skills.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {path.transferable_skills.slice(0, 3).map((ts, i) => (
                        <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                          {ts.candidate_skill} → {ts.related_to}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-[11px] text-slate-500">None identified in taxonomy</span>
                  )}
                </div>

                {/* Gap Count */}
                <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-800 text-slate-400">
                  <span>Skill gaps: <strong className="text-slate-300">{path.gap_count}</strong></span>
                  <button 
                    onClick={() => {
                      setSelectedJobId(path.role_id);
                      setJobMode('demo');
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    className="text-indigo-400 hover:text-indigo-300 font-semibold flex items-center space-x-1"
                  >
                    <span>Simulate Role</span>
                    <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
