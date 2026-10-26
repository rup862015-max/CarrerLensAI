import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, 
  Sparkles, 
  Plus, 
  Trash2, 
  RotateCcw, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  HelpCircle, 
  ArrowRight, 
  BookOpen, 
  Send, 
  History, 
  ShieldAlert, 
  Award, 
  AlertTriangle,
  Lightbulb,
  Check,
  Target,
  Compass,
  FileText,
  Layers
} from 'lucide-react';
import { 
  DemoJob, 
  ResumeAnalysisResponse, 
  TabType,
  InterviewSessionResponse,
  InterviewSessionSummary,
  InterviewQuestion,
  AnswerEvaluationResponse
} from '../types';
import { apiService } from '../services/api';

interface InterviewPageProps {
  currentAnalysis: ResumeAnalysisResponse | null;
  onNavigate: (tab: TabType) => void;
  onOpenAuth?: () => void;
}

export const InterviewPage: React.FC<InterviewPageProps> = ({
  currentAnalysis,
  onNavigate,
  onOpenAuth,
}) => {
  // Session list & active session
  const [sessions, setSessions] = useState<InterviewSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<InterviewSessionResponse | null>(null);
  const [selectedQuestionIndex, setSelectedQuestionIndex] = useState<number>(0);

  // Loading & error states
  const [isLoadingSessions, setIsLoadingSessions] = useState<boolean>(false);
  const [isCreatingSession, setIsCreatingSession] = useState<boolean>(false);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showHistoryModal, setShowHistoryModal] = useState<boolean>(false);

  // Session Creation Configuration
  const [demoJobs, setDemoJobs] = useState<DemoJob[]>([]);
  const [jobMode, setJobMode] = useState<'demo' | 'custom'>('demo');
  const [selectedDemoJobId, setSelectedDemoJobId] = useState<string>('job-backend-001');
  const [customJobTitle, setCustomJobTitle] = useState<string>('');
  const [customJobDescription, setCustomJobDescription] = useState<string>('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([
    'technical',
    'project',
    'behavioral',
    'problem-solving',
    'skill-gap'
  ]);
  const [numQuestions, setNumQuestions] = useState<number>(5);

  // Active question answer state
  const [answerText, setAnswerText] = useState<string>('');
  const [currentEval, setCurrentEval] = useState<AnswerEvaluationResponse | null>(null);

  // Check auth
  const isAuthenticated = apiService.isAuthenticated();

  // Load tailored demo roles & user's sessions on mount
  useEffect(() => {
    if (isAuthenticated) {
      loadSessions();
    }
    loadDemoJobs();
  }, [isAuthenticated, currentAnalysis?.resume_id]);

  const loadDemoJobs = async () => {
    try {
      const jobs = await apiService.getDemoJobs(currentAnalysis?.resume_id);
      setDemoJobs(jobs);
      if (jobs.length > 0) {
        setSelectedDemoJobId(prev => (jobs.some(j => j.id === prev) ? prev : jobs[0].id));
      }
    } catch (err) {
      console.error('Failed to load tailored demo jobs:', err);
    }
  };

  const loadSessions = async () => {
    setIsLoadingSessions(true);
    try {
      const list = await apiService.listInterviewSessions();
      setSessions(list);
    } catch (err: any) {
      console.error('Failed to load interview sessions:', err);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  // Sync answer text and evaluation when active question changes
  useEffect(() => {
    if (activeSession && activeSession.questions && activeSession.questions[selectedQuestionIndex]) {
      const q = activeSession.questions[selectedQuestionIndex];
      setAnswerText(q.answer || '');
      setCurrentEval(q.evaluation || null);
    } else {
      setAnswerText('');
      setCurrentEval(null);
    }
  }, [selectedQuestionIndex, activeSession]);

  const handleCreateSession = async () => {
    setErrorMessage(null);
    setIsCreatingSession(true);

    try {
      const payload: any = {
        categories: selectedCategories.length > 0 ? selectedCategories : ['technical', 'behavioral'],
        num_questions: numQuestions,
      };

      if (currentAnalysis) {
        payload.resume_id = currentAnalysis.resume_id;
        payload.resume_profile = currentAnalysis.extracted_profile;
      }

      if (jobMode === 'demo') {
        const found = demoJobs.find(j => j.id === selectedDemoJobId);
        payload.job_id = selectedDemoJobId;
        payload.job_title = found ? found.title : 'Target Software Role';
        payload.job_description = found ? found.description : '';
      } else {
        if (!customJobTitle.trim()) {
          throw new Error('Please enter a target job title.');
        }
        if (!customJobDescription.trim()) {
          throw new Error('Please paste a job description or key requirements.');
        }
        payload.job_title = customJobTitle;
        payload.job_description = customJobDescription;
      }

      const newSession = await apiService.createInterviewSession(payload);
      setActiveSession(newSession);
      setSelectedQuestionIndex(0);
      loadSessions(); // refresh history in background
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to generate interview session. Please check your inputs.');
    } finally {
      setIsCreatingSession(false);
    }
  };

  const handleResumeSession = async (sessionId: string) => {
    setIsLoadingSessions(true);
    setErrorMessage(null);
    try {
      const session = await apiService.getInterviewSession(sessionId);
      setActiveSession(session);
      setSelectedQuestionIndex(0);
      setShowHistoryModal(false);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to retrieve session.');
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this interview session and all practice answers?')) return;

    try {
      await apiService.deleteInterviewSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSession && activeSession.session_id === sessionId) {
        setActiveSession(null);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to delete session.');
    }
  };

  const handleSubmitAnswer = async () => {
    if (!activeSession || !activeSession.questions[selectedQuestionIndex]) return;
    const currentQ = activeSession.questions[selectedQuestionIndex];

    if (!answerText.trim() || answerText.trim().length < 10) {
      setErrorMessage('Please type a more comprehensive answer before requesting evaluation (at least 10 characters).');
      return;
    }

    setErrorMessage(null);
    setIsSubmittingAnswer(true);

    try {
      const evaluation = await apiService.submitInterviewAnswer(activeSession.session_id, {
        question_id: currentQ.id,
        answer_text: answerText,
      });

      setCurrentEval(evaluation);

      // Update question in activeSession state
      const updatedQuestions = [...activeSession.questions];
      updatedQuestions[selectedQuestionIndex] = {
        ...currentQ,
        answer: answerText,
        evaluation: evaluation,
      };

      const completedCount = updatedQuestions.filter(q => !!q.evaluation).length;
      const scores = updatedQuestions
        .filter(q => q.evaluation && typeof q.evaluation.overall_score === 'number')
        .map(q => q.evaluation!.overall_score);
      const avgScore = scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;

      setActiveSession({
        ...activeSession,
        questions: updatedQuestions,
        completed_questions: completedCount,
        average_score: avgScore,
      });

      // Update session in list
      setSessions(prev => prev.map(s => {
        if (s.id === activeSession.session_id) {
          return {
            ...s,
            completed_questions: completedCount,
            average_score: avgScore,
          };
        }
        return s;
      }));
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to evaluate answer. Please try again.');
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const toggleCategory = (cat: string) => {
    setSelectedCategories(prev => {
      if (prev.includes(cat)) {
        if (prev.length === 1) return prev; // keep at least 1
        return prev.filter(c => c !== cat);
      }
      return [...prev, cat];
    });
  };

  const currentQ: InterviewQuestion | undefined = activeSession?.questions[selectedQuestionIndex];

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'technical':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'project':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'behavioral':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'problem-solving':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
      case 'skill-gap':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  const getDifficultyColor = (diff: string) => {
    switch (diff) {
      case 'entry':
        return 'bg-green-500/10 text-green-400 border-green-500/30';
      case 'mid-level':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'senior':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'principal':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  const getScoreBadge = (score: number) => {
    if (score >= 80) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    if (score >= 65) return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
    if (score >= 50) return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
  };

  // If not authenticated, prompt sign in
  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-6 shadow-lg shadow-indigo-500/10">
          <MessageSquare className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-3">Sign in to Practice Personalized Interviews</h2>
        <p className="text-slate-400 max-w-lg mx-auto mb-8 text-sm leading-relaxed">
          Personalized Interview Preparation uses your verified resume evidence, matched job skills, and identified skill gaps to tailor real technical and behavioral interview questions.
        </p>
        <button
          onClick={() => {
            window.dispatchEvent(new Event('auth:expired'));
          }}
          className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/30"
        >
          <span>Sign In or Register</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-500/20 to-cyan-500/20 border border-indigo-500/30 text-indigo-400">
              <MessageSquare className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Personalized Interview Preparation</h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Evidence-grounded mock interview coach with transparent evaluation rubrics and sample answers
              </p>
            </div>
          </div>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowHistoryModal(true)}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 text-xs font-medium transition-all"
          >
            <History className="w-4 h-4 text-slate-400" />
            <span>Session History ({sessions.length})</span>
          </button>

          {activeSession && (
            <button
              onClick={() => {
                setActiveSession(null);
                setErrorMessage(null);
              }}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-all shadow-md shadow-indigo-600/20"
            >
              <Plus className="w-4 h-4" />
              <span>New Session</span>
            </button>
          )}
        </div>
      </div>

      {/* Error Message Alert */}
      {errorMessage && (
        <div className="mb-6 p-4 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-200 text-sm flex items-start justify-between gap-3">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <p className="font-semibold text-amber-100">
                {errorMessage.toLowerCase().includes('sign in') || errorMessage.toLowerCase().includes('auth') || errorMessage.toLowerCase().includes('bearer')
                  ? 'Please Sign In'
                  : 'Action Required'}
              </p>
              <p className="text-xs text-amber-300/90 mt-0.5 leading-relaxed">
                {errorMessage.toLowerCase().includes('sign in') || errorMessage.toLowerCase().includes('auth') || errorMessage.toLowerCase().includes('bearer')
                  ? 'You need to sign in to use this feature.'
                  : errorMessage}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            {(errorMessage.toLowerCase().includes('sign in') || errorMessage.toLowerCase().includes('auth') || errorMessage.toLowerCase().includes('bearer')) && onOpenAuth && (
              <button
                type="button"
                onClick={onOpenAuth}
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow cursor-pointer"
              >
                Sign In / Register
              </button>
            )}
            <button
              type="button"
              onClick={() => setErrorMessage(null)}
              className="px-2 py-1 text-xs text-amber-400/80 hover:text-white transition-colors cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* VIEW A: NO ACTIVE SESSION -> CONFIGURATION & LAUNCH */}
      {!activeSession ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Session Builder */}
          <div className="lg:col-span-8 space-y-6">
            <div className="bg-slate-900/60 backdrop-blur-sm border border-slate-800/80 rounded-2xl p-6 shadow-xl">
              <div className="flex items-center space-x-2 pb-4 mb-6 border-b border-slate-800">
                <Target className="w-5 h-5 text-indigo-400" />
                <h2 className="text-base font-semibold text-white">Configure Your Interview Preparation Session</h2>
              </div>

              {/* Step 1: Candidate Evidence Base */}
              <div className="mb-6">
                <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-2">
                  1. Candidate Resume Evidence
                </label>
                {currentAnalysis ? (
                  <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex items-start justify-between">
                    <div className="flex items-start space-x-3">
                      <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mt-0.5">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-semibold text-white">
                            {currentAnalysis.extracted_profile.candidate_name || 'Active Candidate Profile'}
                          </span>
                          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                            Verified
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">
                          {currentAnalysis.extracted_profile.skills?.length || 0} extracted skills •{' '}
                          {currentAnalysis.extracted_profile.projects?.length || 0} verified projects
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => onNavigate('resume-analysis')}
                      className="text-xs text-indigo-400 hover:text-indigo-300 font-medium underline"
                    >
                      Change Resume
                    </button>
                  </div>
                ) : (
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start justify-between">
                    <div className="flex items-start space-x-3">
                      <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-xs font-semibold text-amber-300">No Resume Analyzed in Current Session</p>
                        <p className="text-xs text-amber-400/80 mt-0.5">
                          Questions will default to standard role questions. For hyper-personalized project & skill-gap questions, analyze your resume first.
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => onNavigate('resume-analysis')}
                      className="text-xs font-semibold text-amber-300 underline shrink-0 ml-4"
                    >
                      Upload Resume
                    </button>
                  </div>
                )}
              </div>

              {/* Step 2: Target Job Selection */}
              <div className="mb-6">
                <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-2">
                  2. Target Role & Job Requirements
                </label>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <button
                    type="button"
                    onClick={() => setJobMode('demo')}
                    className={`py-2 px-3 rounded-lg text-xs font-medium transition-all text-center ${
                      jobMode === 'demo'
                        ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                        : 'bg-slate-950 text-slate-400 border border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    Select Curated Job Role
                  </button>
                  <button
                    type="button"
                    onClick={() => setJobMode('custom')}
                    className={`py-2 px-3 rounded-lg text-xs font-medium transition-all text-center ${
                      jobMode === 'custom'
                        ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                        : 'bg-slate-950 text-slate-400 border border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    Custom Job Description
                  </button>
                </div>

                {jobMode === 'demo' ? (
                  <div className="space-y-2">
                    {demoJobs.map(job => (
                      <label
                        key={job.id}
                        className={`flex items-start justify-between p-3 rounded-xl border cursor-pointer transition-all ${
                          selectedDemoJobId === job.id
                            ? 'bg-indigo-950/30 border-indigo-500/40 text-white'
                            : 'bg-slate-950/60 border-slate-800/80 text-slate-300 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-start space-x-3">
                          <input
                            type="radio"
                            name="demoJob"
                            checked={selectedDemoJobId === job.id}
                            onChange={() => setSelectedDemoJobId(job.id)}
                            className="mt-1 accent-indigo-500"
                          />
                          <div>
                            <p className="text-xs font-semibold text-slate-100">{job.title}</p>
                            <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">{job.description}</p>
                          </div>
                        </div>
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 shrink-0">
                          {job.requirements?.length || 0} reqs
                        </span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div>
                      <input
                        type="text"
                        placeholder="e.g. Senior Backend Engineer (Distributed Systems)"
                        value={customJobTitle}
                        onChange={(e) => setCustomJobTitle(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <textarea
                        rows={4}
                        placeholder="Paste job description text, required skills, or tech stack requirements..."
                        value={customJobDescription}
                        onChange={(e) => setCustomJobDescription(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Step 3: Question Categories */}
              <div className="mb-6">
                <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-2">
                  3. Question Categories to Practice
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {[
                    { id: 'technical', label: 'Technical Architecture & Fundamentals', desc: 'Core languages, systems, and job requirements' },
                    { id: 'project', label: 'Project & Experience Deep Dive', desc: 'Tradeoffs, metrics, and architecture from your resume' },
                    { id: 'behavioral', label: 'Behavioral & Leadership (STAR)', desc: 'Conflict resolution, ownership, and team dynamics' },
                    { id: 'problem-solving', label: 'Problem Solving & Scenarios', desc: 'Outages, debugging, and live system tradeoffs' },
                    { id: 'skill-gap', label: 'Skill Gap & Ramp-up Assessment', desc: 'Job requirements not yet demonstrated on your resume' },
                  ].map(cat => {
                    const isSelected = selectedCategories.includes(cat.id);
                    return (
                      <div
                        key={cat.id}
                        onClick={() => toggleCategory(cat.id)}
                        className={`p-3 rounded-xl border cursor-pointer select-none transition-all flex items-start space-x-3 ${
                          isSelected
                            ? 'bg-indigo-950/20 border-indigo-500/40 text-white'
                            : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 mt-0.5 ${
                          isSelected ? 'bg-indigo-600 border-indigo-500 text-white' : 'border-slate-700 bg-slate-900'
                        }`}>
                          {isSelected && <Check className="w-3 h-3" />}
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-slate-200">{cat.label}</p>
                          <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">{cat.desc}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Step 4: Question Count */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-slate-300 uppercase tracking-wider">
                    4. Practice Session Length
                  </label>
                  <span className="text-xs font-bold text-indigo-400">{numQuestions} Questions</span>
                </div>
                <div className="flex items-center space-x-3">
                  {[3, 5, 8].map(count => (
                    <button
                      key={count}
                      type="button"
                      onClick={() => setNumQuestions(count)}
                      className={`flex-1 py-2 rounded-xl text-xs font-semibold border transition-all ${
                        numQuestions === count
                          ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-600/30'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      {count} Questions {count === 5 && '(Recommended)'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Launch Button */}
              <button
                onClick={handleCreateSession}
                disabled={isCreatingSession}
                className="w-full py-3.5 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 disabled:opacity-50 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/20 flex items-center justify-center space-x-2"
              >
                {isCreatingSession ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Extracting Evidence & Generating Grounded Questions...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Start Personalized Interview Session</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Right Column: Coaching Philosophy & Recent Sessions */}
          <div className="lg:col-span-4 space-y-6">
            {/* Rigorous Evidence Card */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-lg">
              <div className="flex items-center space-x-2 text-indigo-400 mb-3">
                <ShieldAlert className="w-5 h-5" />
                <h3 className="text-xs font-bold uppercase tracking-wider">Evidence Integrity Guarantee</h3>
              </div>
              <ul className="space-y-2.5 text-xs text-slate-400">
                <li className="flex items-start space-x-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>Zero Hallucinations:</strong> Technical and project questions are anchored strictly to real bullets and job specs.</span>
                </li>
                <li className="flex items-start space-x-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>Targeted Skill Gaps:</strong> Questions test unverified job skills so you can practice honest ramp-up strategies.</span>
                </li>
                <li className="flex items-start space-x-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <span><strong>Isolated Scoring:</strong> Practice scores assess answer structure and do not impact your job match score.</span>
                </li>
              </ul>
            </div>

            {/* Quick Session History List */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Previous Sessions</h3>
                <span className="text-[10px] text-slate-400 font-semibold">{sessions.length} total</span>
              </div>

              {isLoadingSessions ? (
                <div className="py-6 text-center text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
                  <p className="text-xs">Loading sessions...</p>
                </div>
              ) : sessions.length === 0 ? (
                <div className="py-6 text-center text-slate-500">
                  <BookOpen className="w-6 h-6 mx-auto mb-2 text-slate-600" />
                  <p className="text-xs">No previous practice sessions found.</p>
                </div>
              ) : (
                <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                  {sessions.slice(0, 5).map(s => (
                    <div
                      key={s.id}
                      onClick={() => handleResumeSession(s.id)}
                      className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-indigo-500/40 cursor-pointer transition-all group"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-xs font-semibold text-white group-hover:text-indigo-300 transition-colors">
                            {s.job_title}
                          </p>
                          <p className="text-[10px] text-slate-400 mt-0.5">
                            {s.completed_questions}/{s.total_questions} answered • {new Date(s.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="flex items-center space-x-1.5">
                          {s.average_score > 0 && (
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getScoreBadge(s.average_score)}`}>
                              {s.average_score}%
                            </span>
                          )}
                          <button
                            onClick={(e) => handleDeleteSession(s.id, e)}
                            title="Delete Session"
                            className="p-1 text-slate-500 hover:text-red-400 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* VIEW B: ACTIVE INTERVIEW SESSION WORKBENCH */
        <div className="space-y-6">
          {/* Active Session Top Bar */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => setActiveSession(null)}
                  className="p-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 hover:text-white transition-colors"
                  title="Back to Session List"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                <div>
                  <div className="flex items-center space-x-2">
                    <h2 className="text-lg font-bold text-white">{activeSession.job_title}</h2>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                      Candidate: {activeSession.candidate_name}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Session ID: <code className="text-slate-400">{activeSession.session_id.substring(0, 13)}...</code>
                  </p>
                </div>
              </div>

              {/* Progress & Avg Score Badges */}
              <div className="flex items-center space-x-4">
                <div className="text-right">
                  <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Progress</p>
                  <p className="text-sm font-bold text-white">
                    {activeSession.completed_questions} / {activeSession.total_questions} Answered
                  </p>
                </div>
                <div className="h-8 w-[1px] bg-slate-800" />
                <div className="text-right">
                  <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Avg Practice Score</p>
                  <p className={`text-sm font-bold ${activeSession.average_score > 0 ? 'text-indigo-400' : 'text-slate-400'}`}>
                    {activeSession.average_score > 0 ? `${activeSession.average_score}/100` : '—'}
                  </p>
                </div>
              </div>
            </div>

            {/* Score Isolation Banner */}
            <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
              <div className="flex items-center space-x-2">
                <ShieldAlert className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span>
                  <strong>Score Isolation:</strong> Practice scores reflect response clarity and rubric completeness. They are isolated and do not alter your job match score.
                </span>
              </div>
              <span className="hidden sm:inline text-slate-400">Autosaved to database</span>
            </div>

            {/* Data Limitation Notice (if applicable) */}
            {activeSession.data_limitation_note && (
              <div className="mt-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start space-x-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Data Limitation Notice: </span>
                  <span className="text-amber-400/90">{activeSession.data_limitation_note}</span>
                </div>
              </div>
            )}
          </div>

          {/* Workbench: Left Questions Navigation + Right Question Workspace */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Nav: Question List */}
            <div className="lg:col-span-4 space-y-2">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider px-1 mb-2">
                Questions ({activeSession.questions.length})
              </p>
              {activeSession.questions.map((q, idx) => {
                const isSelected = selectedQuestionIndex === idx;
                const isAnswered = !!q.evaluation;
                return (
                  <div
                    key={q.id}
                    onClick={() => setSelectedQuestionIndex(idx)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-indigo-950/30 border-indigo-500/60 shadow-md shadow-indigo-900/10'
                        : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center space-x-2">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase ${getCategoryColor(q.category)}`}>
                          {q.category}
                        </span>
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border capitalize ${getDifficultyColor(q.difficulty_level)}`}>
                          {q.difficulty_level}
                        </span>
                      </div>
                      {isAnswered ? (
                        <div className="flex items-center space-x-1 shrink-0">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span className={`text-[10px] font-bold px-1 py-0.2 rounded border ${getScoreBadge(q.evaluation!.overall_score)}`}>
                            {q.evaluation!.overall_score}
                          </span>
                        </div>
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-slate-600 shrink-0 mt-1" />
                      )}
                    </div>

                    <p className="text-xs font-medium text-slate-200 mt-2 line-clamp-2 leading-snug">
                      {q.question_text}
                    </p>

                    {q.related_requirement && (
                      <p className="text-[10px] text-slate-400 mt-1 line-clamp-1">
                        Skill: <span className="text-slate-300 font-medium">{q.related_requirement}</span>
                      </p>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Right Main: Question Detail, Answer Editor & Feedback */}
            <div className="lg:col-span-8 space-y-6">
              {currentQ ? (
                <>
                  {/* Question Focus Card */}
                  <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl">
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded border uppercase tracking-wider ${getCategoryColor(currentQ.category)}`}>
                        {currentQ.category}
                      </span>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded border capitalize ${getDifficultyColor(currentQ.difficulty_level)}`}>
                        {currentQ.difficulty_level} Level
                      </span>
                      {currentQ.related_requirement && (
                        <span className="text-xs font-medium px-2 py-0.5 rounded border bg-slate-800 text-slate-300 border-slate-700">
                          Target: {currentQ.related_requirement}
                        </span>
                      )}
                      {currentQ.is_generic_fallback && (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                          General Practice Fallback
                        </span>
                      )}
                    </div>

                    {/* Question Text */}
                    <h3 className="text-base sm:text-lg font-bold text-white leading-relaxed mb-4">
                      {currentQ.question_text}
                    </h3>

                    {/* Evaluator Goals & Difficulty Rationale */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                      <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                        <div className="flex items-center space-x-1.5 text-indigo-400 mb-1">
                          <Target className="w-3.5 h-3.5" />
                          <span className="text-[11px] font-bold uppercase tracking-wider">What Interviewer Evaluates</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {currentQ.what_interviewer_is_evaluating}
                        </p>
                      </div>

                      <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                        <div className="flex items-center space-x-1.5 text-cyan-400 mb-1">
                          <Compass className="w-3.5 h-3.5" />
                          <span className="text-[11px] font-bold uppercase tracking-wider">Difficulty & Source Grounding</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {currentQ.difficulty_rationale}
                        </p>
                        <p className="text-[10px] text-slate-400 mt-1">
                          Source: <span className="text-slate-300 font-mono">{currentQ.source_reference}</span>
                        </p>
                      </div>
                    </div>

                    {/* Rubric Preview Accordion / Table */}
                    <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/80">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2 text-slate-300">
                          <BookOpen className="w-4 h-4 text-indigo-400" />
                          <span className="text-xs font-bold uppercase tracking-wider">Evaluation Rubric ({currentQ.rubric.length} Criteria)</span>
                        </div>
                        <span className="text-[10px] text-slate-400">Scored on Technical Accuracy & Trade-offs</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                        {currentQ.rubric.map((crit, idx) => (
                          <div key={idx} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/80 text-xs">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-slate-200">{crit.name}</span>
                              <span className={`text-[9px] uppercase px-1.5 py-0.2 rounded font-bold ${
                                crit.focus === 'core' 
                                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' 
                                  : 'bg-slate-800 text-slate-400'
                              }`}>
                                {crit.focus}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400 leading-snug">{crit.description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Practice Answer Input & Submission */}
                  <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                        <FileText className="w-4 h-4 text-indigo-400" />
                        <span>Your Practice Response</span>
                      </label>
                      <div className="flex items-center space-x-3 text-xs text-slate-400">
                        <span>{answerText.trim().split(/\s+/).filter(Boolean).length} words</span>
                        <span>•</span>
                        <span>{answerText.length} characters</span>
                      </div>
                    </div>

                    <textarea
                      rows={7}
                      placeholder={
                        currentQ.category === 'behavioral'
                          ? "Tip: Use the STAR method (Situation, Task, Action, Result). State the context, the exact challenge, your specific leadership/technical actions, and the measurable business outcome..."
                          : currentQ.category === 'project'
                          ? "Tip: Detail the architectural design, key technical constraints, trade-offs evaluated (e.g. why tool A over B), and quantifiable scale/performance metrics..."
                          : currentQ.category === 'skill-gap'
                          ? "Tip: Honestly articulate your current foundational understanding, analogous transferable skills, and an explicit ramp-up plan..."
                          : "Provide a structured, in-depth explanation covering core mechanisms, operational trade-offs, failure modes, and production best practices..."
                      }
                      value={answerText}
                      onChange={(e) => setAnswerText(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 leading-relaxed font-sans"
                    />

                    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mt-4">
                      <p className="text-[11px] text-slate-400">
                        {currentEval ? 'Answer submitted. You can edit and re-evaluate anytime.' : 'Provide a comprehensive answer to unlock rubric-grounded feedback.'}
                      </p>

                      <button
                        onClick={handleSubmitAnswer}
                        disabled={isSubmittingAnswer || !answerText.trim()}
                        className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs transition-all shadow-md shadow-indigo-600/30 flex items-center justify-center space-x-2 shrink-0"
                      >
                        {isSubmittingAnswer ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>Evaluating Response...</span>
                          </>
                        ) : (
                          <>
                            <Send className="w-3.5 h-3.5" />
                            <span>{currentEval ? 'Re-Evaluate Revised Answer' : 'Submit for Rubric Evaluation'}</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Rubric Evaluation Results */}
                  {currentEval && (
                    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl space-y-6">
                      {/* Overall Score Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-slate-950/80 border border-slate-800">
                        <div>
                          <div className="flex items-center space-x-2">
                            <Award className="w-5 h-5 text-indigo-400" />
                            <h4 className="text-base font-bold text-white">Answer Evaluation Results</h4>
                          </div>
                          <p className="text-xs text-slate-400 mt-1">
                            Evaluated against documented rubric ({currentEval.word_count} words analyzed)
                          </p>
                        </div>
                        <div className="flex items-center space-x-3">
                          <div className="text-right">
                            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Overall Score</span>
                            <div className="flex items-baseline space-x-1">
                              <span className={`text-2xl font-black ${
                                currentEval.overall_score >= 80 ? 'text-emerald-400' :
                                currentEval.overall_score >= 65 ? 'text-cyan-400' :
                                currentEval.overall_score >= 50 ? 'text-amber-400' : 'text-rose-400'
                              }`}>
                                {currentEval.overall_score}
                              </span>
                              <span className="text-xs text-slate-400 font-medium">/100</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Criterion-Level Evaluations */}
                      <div>
                        <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                          Criterion-Level Breakdown
                        </h5>
                        <div className="grid grid-cols-1 gap-2.5">
                          {currentEval.criterion_feedback.map((crit, idx) => {
                            const isStrong = crit.rating === 'strong';
                            const isAdequate = crit.rating === 'adequate';
                            return (
                              <div
                                key={idx}
                                className={`p-3.5 rounded-xl border text-xs ${
                                  isStrong
                                    ? 'bg-emerald-950/20 border-emerald-500/30'
                                    : isAdequate
                                    ? 'bg-blue-950/20 border-blue-500/30'
                                    : 'bg-amber-950/20 border-amber-500/30'
                                }`}
                              >
                                <div className="flex items-center justify-between mb-1">
                                  <span className="font-bold text-white">{crit.criterion}</span>
                                  <div className="flex items-center space-x-2">
                                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${
                                      isStrong ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' :
                                      isAdequate ? 'bg-blue-500/20 text-blue-300 border-blue-500/40' :
                                      'bg-amber-500/20 text-amber-300 border-amber-500/40'
                                    }`}>
                                      {crit.rating.replace('_', ' ')}
                                    </span>
                                    <span className="text-xs font-mono font-bold text-slate-300">{crit.score}/100</span>
                                  </div>
                                </div>
                                <p className="text-slate-300 mt-1 leading-relaxed">{crit.feedback}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Strengths & Improvement Areas 2-column grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Strengths */}
                        <div className="p-4 rounded-xl bg-emerald-950/10 border border-emerald-500/20">
                          <div className="flex items-center space-x-2 text-emerald-400 mb-2">
                            <CheckCircle2 className="w-4 h-4" />
                            <h5 className="text-xs font-bold uppercase tracking-wider">Demonstrated Strengths</h5>
                          </div>
                          <ul className="space-y-1.5 text-xs text-slate-300">
                            {currentEval.strengths.map((str, idx) => (
                              <li key={idx} className="flex items-start space-x-2">
                                <span className="text-emerald-400 font-bold">•</span>
                                <span>{str}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        {/* Improvements */}
                        <div className="p-4 rounded-xl bg-amber-950/10 border border-amber-500/20">
                          <div className="flex items-center space-x-2 text-amber-400 mb-2">
                            <AlertCircle className="w-4 h-4" />
                            <h5 className="text-xs font-bold uppercase tracking-wider">Specific Improvement Areas</h5>
                          </div>
                          <ul className="space-y-1.5 text-xs text-slate-300">
                            {currentEval.improvement_areas.map((imp, idx) => (
                              <li key={idx} className="flex items-start space-x-2">
                                <span className="text-amber-400 font-bold">•</span>
                                <span>{imp}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      {/* Missing Concepts or Reasoning (if any) */}
                      {currentEval.missing_concepts && currentEval.missing_concepts.length > 0 && (
                        <div className="p-4 rounded-xl bg-purple-950/10 border border-purple-500/20">
                          <div className="flex items-center space-x-2 text-purple-400 mb-2">
                            <Lightbulb className="w-4 h-4" />
                            <h5 className="text-xs font-bold uppercase tracking-wider">Missing Concepts & Trade-off Nuances</h5>
                          </div>
                          <ul className="space-y-1.5 text-xs text-slate-300">
                            {currentEval.missing_concepts.map((concept, idx) => (
                              <li key={idx} className="flex items-start space-x-2">
                                <span className="text-purple-400 font-bold">•</span>
                                <span>{concept}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Suggested Structure */}
                      {currentEval.suggested_structure && (
                        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                          <div className="flex items-center space-x-2 text-indigo-400 mb-2">
                            <Layers className="w-4 h-4" />
                            <h5 className="text-xs font-bold uppercase tracking-wider">Suggested Response Structure</h5>
                          </div>
                          <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                            {currentEval.suggested_structure}
                          </p>
                        </div>
                      )}

                      {/* Hypothetical Illustrative Sample Answer Container */}
                      {currentEval.sample_answer && (
                        <div className="p-4 rounded-xl bg-gradient-to-br from-amber-950/10 via-slate-950 to-indigo-950/10 border border-amber-500/40">
                          <div className="flex items-center space-x-2 text-amber-400 mb-2">
                            <AlertTriangle className="w-4 h-4 shrink-0" />
                            <h5 className="text-xs font-bold uppercase tracking-wider">
                              Hypothetical Illustrative Sample Answer
                            </h5>
                          </div>

                          {/* Mandatory Disclaimer Box */}
                          <div className="mb-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-300 leading-snug">
                            <strong>HYPOTHETICAL ILLUSTRATIVE EXAMPLE ONLY:</strong> This sample answer is generated for educational structure demonstration. It does NOT represent the candidate's actual qualifications, career history, or work product.
                          </div>

                          <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800/80 text-xs text-slate-200 leading-relaxed whitespace-pre-line font-sans">
                            {currentEval.sample_answer}
                          </div>
                        </div>
                      )}

                      {/* Non-Hiring Coaching Disclaimer */}
                      <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/60 text-[11px] text-slate-400 flex items-start space-x-2.5">
                        <HelpCircle className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                        <div>
                          <p className="font-semibold text-slate-300">Coaching & Self-Assessment Notice</p>
                          <p className="mt-0.5">
                            {currentEval.disclaimer || 
                              "This AI-generated evaluation is an educational coaching tool designed for interview practice. It does not represent an actual hiring decision or guarantee interview outcomes."}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="py-12 text-center text-slate-500">
                  <p>Select a question from the navigation list on the left to begin practicing.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Session History Modal / Drawer */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <History className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-bold text-white">Your Interview Preparation Sessions</h3>
              </div>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="text-slate-400 hover:text-white text-xs font-semibold px-2 py-1"
              >
                Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
              {sessions.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-8">No saved sessions yet.</p>
              ) : (
                sessions.map(s => (
                  <div
                    key={s.id}
                    className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between hover:border-slate-700 transition-all"
                  >
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-semibold text-white">{s.job_title}</span>
                        {s.average_score > 0 && (
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getScoreBadge(s.average_score)}`}>
                            {s.average_score}% Avg
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        Candidate: {s.candidate_name} • {s.completed_questions}/{s.total_questions} answered •{' '}
                        {new Date(s.created_at).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleResumeSession(s.id)}
                        className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
                      >
                        Resume
                      </button>
                      <button
                        onClick={(e) => handleDeleteSession(s.id, e)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors"
                        title="Delete Session"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
