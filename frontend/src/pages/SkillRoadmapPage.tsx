import React, { useState, useEffect } from 'react';
import { 
  ResumeAnalysisResponse, 
  DemoJob, 
  TabType, 
  RoadmapResponse 
} from '../types';
import { apiService } from '../services/api';
import { 
  MapPin, 
  Target, 
  Compass, 
  CheckCircle2, 
  AlertCircle, 
  Code2, 
  FileText, 
  Sparkles, 
  ChevronDown, 
  ChevronUp, 
  GitBranch, 
  ShieldCheck, 
  BookOpen, 
  FolderCheck,
  Check
} from 'lucide-react';

interface SkillRoadmapPageProps {
  currentAnalysis: ResumeAnalysisResponse | null;
  onNavigate: (tab: TabType) => void;
}

export const SkillRoadmapPage: React.FC<SkillRoadmapPageProps> = ({
  currentAnalysis,
  onNavigate
}) => {
  const [demoJobs, setDemoJobs] = useState<DemoJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>('');
  const [loadingJobs, setLoadingJobs] = useState<boolean>(true);

  // Roadmap State
  const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);
  const [loadingRoadmap, setLoadingRoadmap] = useState<boolean>(false);
  const [roadmapError, setRoadmapError] = useState<string | null>(null);

  // Step expansion state
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});

  // Updating progress state
  const [updatingSkill, setUpdatingSkill] = useState<string | null>(null);

  // Load tailored benchmark roles
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        setLoadingJobs(true);
        const jobs = await apiService.getDemoJobs(currentAnalysis?.resume_id);
        setDemoJobs(jobs);
        if (jobs.length > 0) {
          setSelectedJobId(prev => (jobs.some(j => j.id === prev) ? prev : jobs[0].id));
        }
      } catch (err: any) {
        console.error('Failed to load tailored demo jobs:', err);
      } finally {
        setLoadingJobs(false);
      }
    };
    fetchJobs();
  }, [currentAnalysis?.resume_id]);

  // Fetch roadmap when resume and job are selected
  const handleGenerateRoadmap = async () => {
    if (!currentAnalysis?.resume_id) {
      setRoadmapError('Please upload or analyze a resume first before generating a roadmap.');
      return;
    }
    if (!selectedJobId) {
      setRoadmapError('Please select a target job position.');
      return;
    }

    try {
      setLoadingRoadmap(true);
      setRoadmapError(null);
      const res = await apiService.getSkillRoadmap({
        resume_id: currentAnalysis.resume_id,
        job_id: selectedJobId
      });
      setRoadmap(res);

      // Expand first 2 steps by default
      const initialExpanded: Record<string, boolean> = {};
      res.steps.slice(0, 2).forEach(s => {
        initialExpanded[s.id] = true;
      });
      setExpandedSteps(initialExpanded);
    } catch (err: any) {
      setRoadmapError(err.message || 'Failed to generate learning roadmap.');
      setRoadmap(null);
    } finally {
      setLoadingRoadmap(false);
    }
  };

  // Auto-generate on initial load if resume and job are ready
  useEffect(() => {
    if (currentAnalysis?.resume_id && selectedJobId && !roadmap && !loadingRoadmap) {
      handleGenerateRoadmap();
    }
  }, [currentAnalysis?.resume_id, selectedJobId]);

  const toggleStep = (stepId: string) => {
    setExpandedSteps(prev => ({
      ...prev,
      [stepId]: !prev[stepId]
    }));
  };

  const handleUpdateStatus = async (skillName: string, newStatus: 'not_started' | 'in_progress' | 'completed') => {
    if (!currentAnalysis?.resume_id || !roadmap) return;

    try {
      setUpdatingSkill(skillName);
      await apiService.updateRoadmapProgress({
        resume_id: currentAnalysis.resume_id,
        job_id: roadmap.job_id,
        skill_name: skillName,
        status: newStatus
      });

      // Update state locally
      setRoadmap(prev => {
        if (!prev) return null;
        let compCount = 0;
        let inProgCount = 0;

        const updatedSteps = prev.steps.map(s => {
          const status = s.skill.toLowerCase() === skillName.toLowerCase() ? newStatus : s.status;
          if (status === 'completed') compCount++;
          if (status === 'in_progress') inProgCount++;
          return { ...s, status };
        });

        const updatedPhases = prev.phases.map(p => ({
          ...p,
          skills: p.skills.map(s => {
            const status = s.skill.toLowerCase() === skillName.toLowerCase() ? newStatus : s.status;
            return { ...s, status };
          })
        }));

        return {
          ...prev,
          steps: updatedSteps,
          phases: updatedPhases,
          completed_steps: compCount,
          in_progress_steps: inProgCount
        };
      });
    } catch (err: any) {
      console.error('Failed to update step status:', err);
    } finally {
      setUpdatingSkill(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 p-5 rounded-2xl border border-slate-800 backdrop-blur-sm">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <MapPin className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">
                Skill Learning Roadmap
              </h1>
              <p className="text-xs text-slate-400">
                Personalized, dependency-aware learning sequence based on verified resume evidence and target job requirements.
              </p>
            </div>
          </div>
        </div>

        {/* Quick Nav Links */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onNavigate('job-matching')}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700/80 border border-slate-700 transition"
          >
            <Target className="w-3.5 h-3.5 text-indigo-400" />
            <span>Job Matching</span>
          </button>
          <button
            onClick={() => onNavigate('career-simulator')}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700/80 border border-slate-700 transition"
          >
            <Compass className="w-3.5 h-3.5 text-cyan-400" />
            <span>Career Simulator</span>
          </button>
        </div>
      </div>

      {/* Target Job & Resume Selector Bar */}
      <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800/80 grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
        {/* Active Candidate */}
        <div className="md:col-span-4">
          <label className="block text-[11px] font-medium text-slate-400 mb-1">Active Candidate Profile</label>
          <div className="flex items-center space-x-2 bg-slate-950/60 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200">
            <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
            <span className="truncate">
              {currentAnalysis ? (
                <>
                  <strong className="text-white">{currentAnalysis.extracted_profile?.candidate_name || 'Uploaded Candidate'}</strong>
                  <span className="text-xs text-slate-400 ml-1.5">({currentAnalysis.filename})</span>
                </>
              ) : (
                <span className="text-amber-400 text-xs">No active resume — upload one in Resume Analysis</span>
              )}
            </span>
          </div>
        </div>

        {/* Target Job Selector */}
        <div className="md:col-span-5">
          <label className="block text-[11px] font-medium text-slate-400 mb-1">Target Job Position</label>
          <select
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
            disabled={loadingJobs}
            className="w-full bg-slate-950/60 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            {demoJobs.map(job => (
              <option key={job.id} value={job.id}>
                {job.title} — {job.department} ({job.location})
              </option>
            ))}
          </select>
        </div>

        {/* Action Button */}
        <div className="md:col-span-3 flex items-end">
          <button
            onClick={handleGenerateRoadmap}
            disabled={loadingRoadmap || !currentAnalysis?.resume_id}
            className={`w-full py-2 px-4 rounded-lg text-sm font-semibold flex items-center justify-center space-x-2 transition shadow-lg ${
              loadingRoadmap || !currentAnalysis?.resume_id
                ? 'bg-indigo-600/40 text-indigo-300 cursor-not-allowed border border-indigo-500/20'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/25 border border-indigo-400/30'
            }`}
          >
            {loadingRoadmap ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Computing Roadmap...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Generate Roadmap</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {roadmapError && (
        <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-xl flex items-start space-x-3 text-red-200">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold text-red-300">Unable to generate roadmap</p>
            <p className="text-xs text-red-400/90 mt-0.5">{roadmapError}</p>
          </div>
        </div>
      )}

      {/* Honest Boundary Notice */}
      <div className="bg-slate-900/30 border border-slate-800/60 rounded-xl p-3 flex items-start space-x-3 text-xs text-slate-400">
        <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
        <p>
          <strong className="text-slate-300">Evidence Integrity Policy:</strong> Prerequisite ordering is derived exclusively from explicit taxonomy parent frameworks and foundational languages. Self-reported progress tracks personal study and does not alter verified resume match scores without an updated resume containing documented project deliverables.
        </p>
      </div>

      {/* Main Roadmap Display */}
      {roadmap && (
        <div className="space-y-6">
          {/* Roadmap Overview Bar */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Roadmap Summary</span>
                <h2 className="text-lg font-bold text-white mt-0.5">{roadmap.summary}</h2>
                <p className="text-xs text-slate-400 mt-1 max-w-2xl">{roadmap.methodology_notes}</p>
              </div>

              {/* Progress Counters */}
              <div className="flex items-center space-x-3 shrink-0">
                <div className="bg-slate-950/80 border border-slate-800 px-3.5 py-2 rounded-xl text-center">
                  <div className="text-lg font-bold text-white">{roadmap.total_steps}</div>
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Total Steps</div>
                </div>
                <div className="bg-slate-950/80 border border-slate-800 px-3.5 py-2 rounded-xl text-center">
                  <div className="text-lg font-bold text-emerald-400">{roadmap.completed_steps}</div>
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Completed</div>
                </div>
                <div className="bg-slate-950/80 border border-slate-800 px-3.5 py-2 rounded-xl text-center">
                  <div className="text-lg font-bold text-amber-400">{roadmap.in_progress_steps}</div>
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">In Progress</div>
                </div>
              </div>
            </div>

            {/* Progress Bar */}
            {roadmap.total_steps > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-800/80">
                <div className="flex justify-between text-xs text-slate-400 mb-1.5">
                  <span>Learning Journey Completion</span>
                  <span>{Math.round((roadmap.completed_steps / roadmap.total_steps) * 100)}%</span>
                </div>
                <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden flex">
                  <div 
                    className="h-full bg-emerald-500 transition-all duration-300" 
                    style={{ width: `${(roadmap.completed_steps / roadmap.total_steps) * 100}%` }}
                  />
                  <div 
                    className="h-full bg-amber-500 transition-all duration-300" 
                    style={{ width: `${(roadmap.in_progress_steps / roadmap.total_steps) * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Zero Gap State */}
          {roadmap.total_steps === 0 && (
            <div className="bg-slate-900/30 border border-slate-800 rounded-2xl p-8 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto text-emerald-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white">Full Requirement Coverage</h3>
              <p className="text-sm text-slate-400 max-w-lg mx-auto">
                All technical requirements for <strong className="text-slate-200">{roadmap.job_title}</strong> are satisfied by verified evidence in your resume. No mandatory learning gaps were detected.
              </p>
              <button
                onClick={() => onNavigate('job-matching')}
                className="mt-2 inline-flex items-center space-x-2 text-xs font-medium text-indigo-400 hover:text-indigo-300 transition"
              >
                <span>View matching score breakdown</span>
                <Target className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Phases and Steps */}
          {roadmap.phases.map(phase => (
            <div key={phase.phase_number} className="space-y-3">
              {/* Phase Header */}
              <div className="flex items-center space-x-3 px-1">
                <div className="w-6 h-6 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-xs font-bold flex items-center justify-center shrink-0">
                  {phase.phase_number}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white tracking-wide">{phase.phase_name}</h3>
                  <p className="text-xs text-slate-400">{phase.description}</p>
                </div>
              </div>

              {/* Step Cards */}
              <div className="space-y-3">
                {phase.skills.map((step) => {
                  const isExpanded = expandedSteps[step.id] ?? false;
                  const isUpdating = updatingSkill === step.skill;

                  return (
                    <div 
                      key={step.id} 
                      className={`bg-slate-900/60 rounded-xl border transition-all duration-200 overflow-hidden ${
                        step.status === 'completed' 
                          ? 'border-emerald-500/30 bg-emerald-950/10' 
                          : step.status === 'in_progress'
                            ? 'border-amber-500/30 bg-amber-950/10'
                            : 'border-slate-800 hover:border-slate-700/80'
                      }`}
                    >
                      {/* Card Header */}
                      <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="flex items-start sm:items-center space-x-3 cursor-pointer flex-1" onClick={() => toggleStep(step.id)}>
                          {/* Priority Indicator */}
                          <div className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider shrink-0 ${
                            step.priority === 'High' 
                              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' 
                              : step.priority === 'Medium'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}>
                            {step.priority} Priority
                          </div>

                          {/* Skill Name & Gap Status */}
                          <div>
                            <div className="flex items-center space-x-2">
                              <h4 className="text-sm font-bold text-white">{step.skill}</h4>
                              <span className="text-[11px] text-slate-400">({step.category})</span>
                              {step.evidence_status === 'prerequisite_needed' && (
                                <span className="text-[10px] font-semibold text-purple-300 bg-purple-500/20 border border-purple-500/30 px-1.5 py-0.2 rounded">
                                  Prerequisite
                                </span>
                              )}
                              {step.evidence_status === 'unverified' && (
                                <span className="text-[10px] font-semibold text-yellow-300 bg-yellow-500/20 border border-yellow-500/30 px-1.5 py-0.2 rounded">
                                  Resume Claim Only
                                </span>
                              )}
                              {step.evidence_status === 'partial' && (
                                <span className="text-[10px] font-semibold text-cyan-300 bg-cyan-500/20 border border-cyan-500/30 px-1.5 py-0.2 rounded">
                                  Partial Match
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-400 mt-0.5">{step.priority_reason}</p>
                          </div>
                        </div>

                        {/* Status Toggle Buttons */}
                        <div className="flex items-center space-x-2 shrink-0">
                          <div className="inline-flex rounded-lg bg-slate-950/80 p-0.5 border border-slate-800 text-xs">
                            <button
                              onClick={() => handleUpdateStatus(step.skill, 'not_started')}
                              disabled={isUpdating}
                              className={`px-2 py-1 rounded-md transition ${
                                step.status === 'not_started' 
                                  ? 'bg-slate-800 text-slate-200 font-semibold' 
                                  : 'text-slate-400 hover:text-slate-200'
                              }`}
                            >
                              Not Started
                            </button>
                            <button
                              onClick={() => handleUpdateStatus(step.skill, 'in_progress')}
                              disabled={isUpdating}
                              className={`px-2 py-1 rounded-md transition ${
                                step.status === 'in_progress' 
                                  ? 'bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/30' 
                                  : 'text-slate-400 hover:text-slate-200'
                              }`}
                            >
                              In Progress
                            </button>
                            <button
                              onClick={() => handleUpdateStatus(step.skill, 'completed')}
                              disabled={isUpdating}
                              className={`px-2 py-1 rounded-md flex items-center space-x-1 transition ${
                                step.status === 'completed' 
                                  ? 'bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30' 
                                  : 'text-slate-400 hover:text-slate-200'
                              }`}
                            >
                              <Check className="w-3 h-3" />
                              <span>Done</span>
                            </button>
                          </div>

                          <button 
                            onClick={() => toggleStep(step.id)} 
                            className="p-1 text-slate-400 hover:text-white"
                          >
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>

                      {/* Satisfied Prerequisites Strip */}
                      {step.satisfied_prerequisites.length > 0 && (
                        <div className="px-4 py-2 bg-emerald-950/20 border-t border-emerald-500/10 flex items-center space-x-2 text-xs">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span className="text-emerald-300 font-medium">Satisfied Prerequisites in your resume:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {step.satisfied_prerequisites.map(p => (
                              <span key={p} className="bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2 py-0.5 rounded text-[11px]">
                                {p}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Unmet Prerequisites Warning Strip */}
                      {step.prerequisites.length > 0 && (
                        <div className="px-4 py-2 bg-purple-950/20 border-t border-purple-500/10 flex items-center space-x-2 text-xs">
                          <GitBranch className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                          <span className="text-purple-300 font-medium">Learn first (Foundational Prerequisites):</span>
                          <div className="flex flex-wrap gap-1.5">
                            {step.prerequisites.map(p => (
                              <span key={p} className="bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2 py-0.5 rounded text-[11px]">
                                {p}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Expanded Details */}
                      {isExpanded && (
                        <div className="p-4 pt-3 border-t border-slate-800/80 space-y-4 bg-slate-950/40 text-xs">
                          {/* Learning Objective */}
                          <div>
                            <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px] flex items-center gap-1.5 mb-1">
                              <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                              Recommended Learning Objective
                            </span>
                            <p className="text-slate-300 leading-relaxed bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                              {step.learning_objective}
                            </p>
                          </div>

                          {/* Practical Exercise & Completion Criteria */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                              <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px] flex items-center gap-1.5 mb-1">
                                <Code2 className="w-3.5 h-3.5 text-cyan-400" />
                                Practical Portfolio Exercise
                              </span>
                              <p className="text-slate-300 leading-relaxed mt-1">
                                {step.practical_exercise}
                              </p>
                            </div>

                            <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                              <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px] flex items-center gap-1.5 mb-1">
                                <FolderCheck className="w-3.5 h-3.5 text-emerald-400" />
                                Completion & Evidence Criteria
                              </span>
                              <p className="text-slate-300 leading-relaxed mt-1">
                                {step.completion_criteria}
                              </p>
                            </div>
                          </div>

                          {/* Resume Evidence Guidance */}
                          <div className="bg-indigo-950/20 border border-indigo-500/20 p-3 rounded-lg">
                            <span className="font-semibold text-indigo-300 uppercase tracking-wider text-[10px] flex items-center gap-1.5 mb-1">
                              <FileText className="w-3.5 h-3.5 text-indigo-400" />
                              Resume Evidence Guidance (What to Add After Project Completion)
                            </span>
                            <p className="text-slate-300 font-mono text-[11px] mt-1 bg-slate-950/80 p-2 rounded border border-indigo-500/20">
                              • {step.resume_evidence_guidance}
                            </p>
                          </div>

                          {/* Companion Related Skills */}
                          {step.related_skills.length > 0 && (
                            <div className="flex items-center space-x-2 pt-1 text-slate-400">
                              <span className="text-[11px] font-medium text-slate-400">Helpful Companion Technologies:</span>
                              <div className="flex flex-wrap gap-1">
                                {step.related_skills.map(rel => (
                                  <span key={rel} className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-[10px]">
                                    {rel}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
