import React, { useState, useEffect } from 'react';
import {
  Scale,
  ShieldAlert,
  RefreshCw,
  Search,
  Info,
  Layers,
  ArrowRight,
  Sliders,
  FileText,
  Trash2,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import {
  FairnessAuditReport,
  FairnessAuditSummary,
  FairnessTestResult,
  FairnessFinding,
  FairnessMetricItem,
  UnassessedDimension,
  ResumeAnalysisResponse,
  TabType
} from '../types';
import { apiService } from '../services/api';

interface FairnessAuditPageProps {
  currentAnalysis?: ResumeAnalysisResponse | null;
  onNavigate?: (tab: TabType) => void;
  onOpenAuth?: () => void;
}

export const FairnessAuditPage: React.FC<FairnessAuditPageProps> = ({
  onOpenAuth,
}) => {
  const [report, setReport] = useState<FairnessAuditReport | null>(null);
  const [history, setHistory] = useState<FairnessAuditSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [runningAudit, setRunningAudit] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isAuthError = (msg: string | null): boolean => {
    if (!msg) return false;
    const lower = msg.toLowerCase();
    return (
      lower.includes('sign in') ||
      lower.includes('log in') ||
      lower.includes('bearer') ||
      lower.includes('token') ||
      lower.includes('auth') ||
      lower.includes('401')
    );
  };

  // Sub-tabs
  const [activeTab, setActiveTab] = useState<'tests' | 'findings' | 'policy' | 'unassessed'>('tests');

  // Test explorer filters
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedTestId, setExpandedTestId] = useState<string | null>(null);

  // Load latest audit and history on mount
  useEffect(() => {
    loadAuditData();
  }, []);

  const loadAuditData = async () => {
    setLoading(true);
    setErrorMessage(null);
    if (!apiService.isAuthenticated()) {
      setLoading(false);
      return;
    }
    try {
      const [latestReport, histList] = await Promise.all([
        apiService.getLatestFairnessAudit(),
        apiService.listFairnessAudits()
      ]);
      setReport(latestReport);
      setHistory(histList);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load fairness audit records');
    } finally {
      setLoading(false);
    }
  };

  const handleRunAudit = async () => {
    if (!apiService.isAuthenticated()) {
      setErrorMessage('You need to sign in to use this feature.');
      if (onOpenAuth) onOpenAuth();
      return;
    }
    setRunningAudit(true);
    setErrorMessage(null);
    try {
      const newReport = await apiService.runFairnessAudit();
      setReport(newReport);
      const histList = await apiService.listFairnessAudits();
      setHistory(histList);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to execute fairness audit');
    } finally {
      setRunningAudit(false);
    }
  };

  const handleSelectAudit = async (auditId: string) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const fetched = await apiService.getFairnessAudit(auditId);
      setReport(fetched);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to retrieve selected audit');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAudit = async (auditId: string) => {
    if (!window.confirm('Are you sure you want to delete this fairness audit record?')) return;
    try {
      await apiService.deleteFairnessAudit(auditId);
      const histList = await apiService.listFairnessAudits();
      setHistory(histList);
      if (report?.audit_id === auditId) {
        if (histList.length > 0) {
          handleSelectAudit(histList[0].audit_id);
        } else {
          setReport(null);
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to delete audit record');
    }
  };

  // Filter test results
  const filteredTests = (report?.test_results || []).filter((t: FairnessTestResult) => {
    if (categoryFilter !== 'all' && t.category !== categoryFilter) return false;
    if (statusFilter !== 'all' && t.status !== statusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = t.test_id.toLowerCase().includes(q);
      const matchDesc = t.description.toLowerCase().includes(q);
      const matchAttr = t.attribute_manipulated.toLowerCase().includes(q);
      if (!matchId && !matchDesc && !matchAttr) return false;
    }
    return true;
  });

  const categories = [
    { id: 'all', label: 'All Test Batteries' },
    { id: 'demographic_proxy_invariance', label: 'Demographic Proxy (Names)' },
    { id: 'section_order_invariance', label: 'Section Ordering' },
    { id: 'contact_location_invariance', label: 'Contact & Location' },
    { id: 'layout_formatting_invariance', label: 'Layout & Bullet Syntax' },
    { id: 'alias_normalization_consistency', label: 'Skill Alias Normalization' },
    { id: 'boundary_case_resilience', label: 'Boundary & Null Cases' },
    { id: 'score_isolation_guarantee', label: 'Score Isolation' },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* ─── Header & Actions ─── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-indigo-950/40 border border-slate-800 shadow-xl backdrop-blur-md">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-500 text-white shadow-lg shadow-indigo-500/20">
              <Scale className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2.5">
                <h1 className="text-2xl font-bold tracking-tight text-white">Fairness Audit & Scoring Consistency</h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                  Policy {report?.policy_version || 'v1.2.0'}
                </span>
              </div>
              <p className="text-sm text-slate-400">
                Reproducible counterfactual test harness measuring individual invariance, attribute sensitivity, and policy adherence.
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          {history.length > 0 && report && (
            <div className="flex items-center space-x-1.5">
              <select
                aria-label="Historical Audit Runs"
                value={report?.audit_id || ''}
                onChange={(e) => handleSelectAudit(e.target.value)}
                className="bg-slate-800 text-slate-200 text-xs rounded-xl px-3 py-2.5 border border-slate-700 outline-none hover:border-slate-600 transition-colors"
              >
                {history.map((h: FairnessAuditSummary) => (
                  <option key={h.audit_id} value={h.audit_id}>
                    {new Date(h.timestamp).toLocaleString()} ({h.passed_tests}/{h.total_tests} pass)
                  </option>
                ))}
              </select>
              <button
                onClick={() => handleDeleteAudit(report.audit_id)}
                title="Delete this audit record"
                className="p-2.5 rounded-xl bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-300 border border-slate-700 transition-colors cursor-pointer"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          )}

          <button
            onClick={handleRunAudit}
            disabled={runningAudit}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-medium text-xs transition-all shadow-lg ${
              runningAudit
                ? 'bg-indigo-600/50 text-indigo-200 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-500/25 hover:shadow-indigo-500/40 cursor-pointer'
            }`}
          >
            <RefreshCw className={`w-4 h-4 ${runningAudit ? 'animate-spin' : ''}`} />
            <span>{runningAudit ? 'Executing Test Batteries...' : 'Run New Audit Suite'}</span>
          </button>
        </div>
      </div>

      {/* Friendly Notice / Warning Banner */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/40 flex items-start justify-between gap-3 text-amber-200 text-sm">
          <div className="flex items-start space-x-3">
            <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <p className="font-semibold text-amber-100">
                {isAuthError(errorMessage) ? 'Please Sign In' : 'Notice'}
              </p>
              <p className="text-xs text-amber-300/90 leading-relaxed">
                {isAuthError(errorMessage)
                  ? 'You need to sign in to use this feature.'
                  : errorMessage}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            {isAuthError(errorMessage) && onOpenAuth && (
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

      {/* ─── Mandatory Ethical Disclaimer & Limitations Card ─── */}
      <div className="p-5 rounded-2xl bg-amber-950/20 border border-amber-500/30 backdrop-blur-sm">
        <div className="flex items-start space-x-3">
          <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400 shrink-0 mt-0.5">
            <Info className="w-5 h-5" />
          </div>
          <div className="space-y-1.5 text-xs text-slate-300">
            <h4 className="font-semibold text-amber-200 text-sm flex items-center space-x-2">
              <span>Fairness Measurement Methodology & Ethical Boundaries</span>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                Transparent Limitations
              </span>
            </h4>
            <p className="leading-relaxed">
              <strong className="text-slate-100">Controlled Individual Invariance:</strong> This audit tests whether altering single irrelevant attributes (such as candidate names, contact phone numbers, section layouts, bullet characters, or skill aliases) alters candidate match scores on identical qualifications.
            </p>
            <p className="leading-relaxed">
              <strong className="text-slate-100">Explicit Demographic Non-Inference:</strong> CareerLens AI does <strong className="text-amber-200">NOT</strong> infer race, gender, religion, or disability from candidate names or resume text. Synthetic cultural names are tested solely to verify name-string invariance. A passed test verifies that tested irrelevant inputs did not distort scores; it is <strong className="text-amber-200">NOT</strong> an empirical proof that the overall system is free of population-level demographic disparities.
            </p>
            <p className="leading-relaxed text-slate-400 italic">
              Group-level demographic parity (e.g., Four-Fifths / 80% Rule) remains unassessed because real candidate demographic data is ethically protected and not collected by this platform.
            </p>
          </div>
        </div>
      </div>

      {loading && !report ? (
        <div className="p-16 text-center space-y-4">
          <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
          <p className="text-slate-400 text-sm">Evaluating counterfactual test batteries against matching pipeline...</p>
        </div>
      ) : report ? (
        <>
          {/* ─── Executive Scorecards / Metrics ─── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {report.metrics.map((metric: FairnessMetricItem, idx: number) => {
              const isPassed = metric.status === 'passed';
              return (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-2 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium text-slate-400 line-clamp-1" title={metric.name}>
                      {metric.name.split('(')[0].trim()}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                        isPassed
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}
                    >
                      {isPassed ? 'Compliant' : 'Flagged'}
                    </span>
                  </div>

                  <div className="flex items-baseline space-x-1.5">
                    <span className="text-2xl font-bold tracking-tight text-white">
                      {metric.name.includes('Rate') ? `${metric.value}%` : metric.value}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      (tol: {metric.name.includes('Rate') ? `${metric.tolerance}%` : `≤ ${metric.tolerance}`})
                    </span>
                  </div>

                  <div className="text-[10px] text-slate-400 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-slate-400">{metric.formula}</span>
                      <span className="text-slate-400">N={metric.sample_size}</span>
                    </div>
                    <p className="line-clamp-2 text-slate-400" title={metric.description}>
                      {metric.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* ─── Navigation Sub-Tabs ─── */}
          <div className="flex border-b border-slate-800 space-x-2">
            <button
              onClick={() => setActiveTab('tests')}
              className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
                activeTab === 'tests'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Counterfactual Test Explorer ({report.total_tests})</span>
            </button>

            <button
              onClick={() => setActiveTab('findings')}
              className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
                activeTab === 'findings'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Documented Findings ({report.findings.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('policy')}
              className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
                activeTab === 'policy'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sliders className="w-4 h-4" />
              <span>Scoring Policy & Weights</span>
            </button>

            <button
              onClick={() => setActiveTab('unassessed')}
              className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
                activeTab === 'unassessed'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Unassessed Dimensions ({report.unassessed_dimensions.length})</span>
            </button>
          </div>

          {/* ─── Tab 1: Counterfactual Test Explorer ─── */}
          {activeTab === 'tests' && (
            <div className="space-y-4">
              {/* Filter Bar */}
              <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    aria-label="Filter by Test Battery"
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="bg-slate-800 text-slate-200 text-xs rounded-lg px-3 py-2 border border-slate-700 outline-none"
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.label}
                      </option>
                    ))}
                  </select>

                  <select
                    aria-label="Filter by Compliance Status"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="bg-slate-800 text-slate-200 text-xs rounded-lg px-3 py-2 border border-slate-700 outline-none"
                  >
                    <option value="all">All Outcomes</option>
                    <option value="passed">Passed (Within Tolerance)</option>
                    <option value="discrepancy">Discrepancy (Flagged)</option>
                  </select>
                </div>

                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    placeholder="Search test ID, description..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-slate-800 text-slate-200 text-xs rounded-lg pl-9 pr-3 py-2 border border-slate-700 outline-none w-full sm:w-64 placeholder-slate-500"
                  />
                </div>
              </div>

              {/* Test Items Table / List */}
              <div className="space-y-3">
                {filteredTests.length === 0 ? (
                  <div className="p-8 text-center text-slate-400 text-xs">
                    No counterfactual tests match the selected filters.
                  </div>
                ) : (
                  filteredTests.map((test: FairnessTestResult) => {
                    const isExpanded = expandedTestId === test.test_id;
                    const isPassed = test.status === 'passed';
                    const compKeys = Object.keys(test.component_deltas || {});

                    return (
                      <div
                        key={test.test_id}
                        className="rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-all overflow-hidden"
                      >
                        <div
                          onClick={() => setExpandedTestId(isExpanded ? null : test.test_id)}
                          className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer select-none"
                        >
                          <div className="space-y-1 flex-1">
                            <div className="flex items-center space-x-2.5">
                              <span className="font-mono text-xs font-bold text-indigo-400">
                                {test.test_id}
                              </span>
                              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                                {test.category.replace(/_/g, ' ')}
                              </span>
                              <span
                                className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                                  isPassed
                                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                    : 'bg-red-500/20 text-red-300 border border-red-500/30'
                                }`}
                              >
                                {test.status}
                              </span>
                            </div>
                            <p className="text-sm font-medium text-slate-200">
                              {test.description}
                            </p>
                          </div>

                          <div className="flex items-center space-x-6 shrink-0">
                            <div className="text-right">
                              <p className="text-[10px] text-slate-400 uppercase font-semibold">Match Score</p>
                              <div className="flex items-center space-x-2">
                                <span className="text-sm font-medium text-slate-400">{test.baseline_score}</span>
                                <ArrowRight className="w-3 h-3 text-slate-500" />
                                <span className="text-sm font-bold text-white">{test.variant_score}</span>
                                <span
                                  className={`text-xs font-mono font-semibold px-1.5 py-0.5 rounded ${
                                    test.score_delta === 0
                                      ? 'text-emerald-400 bg-emerald-500/10'
                                      : Math.abs(test.score_delta) <= 1
                                      ? 'text-amber-400 bg-amber-500/10'
                                      : 'text-red-400 bg-red-500/10'
                                  }`}
                                >
                                  {test.score_delta > 0 ? `+${test.score_delta}` : test.score_delta}
                                </span>
                              </div>
                            </div>

                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4 text-slate-400" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-slate-400" />
                            )}
                          </div>
                        </div>

                        {/* Expanded Component Inspection Drawer */}
                        {isExpanded && (
                          <div className="px-4 pb-4 pt-2 border-t border-slate-800/80 bg-slate-950/40 space-y-3">
                            <div className="text-xs text-slate-300">
                              <strong className="text-slate-100">Audit Explanation:</strong> {test.explanation}
                            </div>

                            {compKeys.length > 0 && (
                              <div className="space-y-1.5">
                                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                                  Deterministic Component Breakdown
                                </p>
                                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                                  {compKeys.map((cKey) => {
                                    const cd = test.component_deltas[cKey];
                                    const isZero = cd.delta === 0;
                                    return (
                                      <div
                                        key={cKey}
                                        className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1 text-center"
                                      >
                                        <p className="text-[10px] text-slate-400 truncate uppercase font-semibold">
                                          {cd.component.replace('_', ' ')}
                                        </p>
                                        <div className="flex items-center justify-center space-x-1 text-xs">
                                          <span className="text-slate-400">{cd.baseline}</span>
                                          <ArrowRight className="w-2.5 h-2.5 text-slate-600" />
                                          <span className="font-bold text-white">{cd.variant}</span>
                                        </div>
                                        <span
                                          className={`inline-block text-[10px] font-mono font-bold px-1.5 py-0.2 rounded ${
                                            isZero
                                              ? 'text-emerald-400 bg-emerald-500/10'
                                              : 'text-amber-400 bg-amber-500/10'
                                          }`}
                                        >
                                          Δ {cd.delta > 0 ? `+${cd.delta}` : cd.delta}
                                        </span>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                              <span>Baseline: <strong className="text-slate-300">{test.baseline_name}</strong></span>
                              <span>Variant: <strong className="text-slate-300">{test.variant_name}</strong></span>
                              <span>Manipulated Attribute: <strong className="text-slate-300">{test.attribute_manipulated}</strong></span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* ─── Tab 2: Documented Findings & Remediations ─── */}
          {activeTab === 'findings' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 leading-relaxed">
                Structured catalog of confirmed scoring discrepancies, root-cause investigations, and software remediations. Confirmed defects are distinguished from possible future risks.
              </div>

              <div className="grid grid-cols-1 gap-4">
                {report.findings.map((f: FairnessFinding) => {
                  const isRemediated = f.status === 'remediated';
                  const isRisk = f.status === 'active_risk' || f.status === 'unassessed_risk';

                  return (
                    <div
                      key={f.id}
                      className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3 hover:border-slate-700 transition-colors"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center space-x-2.5">
                          <span className="font-mono text-sm font-bold text-indigo-400">{f.id}</span>
                          <h3 className="text-sm font-semibold text-white">{f.title}</h3>
                        </div>

                        <div className="flex items-center space-x-2">
                          <span
                            className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                              f.severity === 'high'
                                ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                                : f.severity === 'medium'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                            }`}
                          >
                            {f.severity} severity
                          </span>

                          <span
                            className={`text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full ${
                              isRemediated
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : isRisk
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : 'bg-slate-800 text-slate-300 border border-slate-700'
                            }`}
                          >
                            {f.status.replace('_', ' ')}
                          </span>
                        </div>
                      </div>

                      <p className="text-xs text-slate-300">{f.description}</p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-slate-950/40 p-3 rounded-lg border border-slate-800/80">
                        <div>
                          <strong className="text-slate-400 uppercase text-[10px] block">Observed Defect / Behavior</strong>
                          <span className="text-red-300/90">{f.observed_behavior}</span>
                        </div>
                        <div>
                          <strong className="text-slate-400 uppercase text-[10px] block">Expected Authoritative Behavior</strong>
                          <span className="text-emerald-300/90">{f.expected_behavior}</span>
                        </div>
                      </div>

                      <div className="text-xs space-y-1">
                        <strong className="text-slate-400 uppercase text-[10px] block">Engineering Remediation Implemented</strong>
                        <p className="text-slate-300 leading-relaxed">{f.remediation}</p>
                      </div>

                      <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/60 text-[11px] text-slate-400">
                        <span>Affected Components:</span>
                        {f.affected_components.map((comp) => (
                          <span
                            key={comp}
                            className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                          >
                            {comp}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ─── Tab 3: Authoritative Scoring Policy ─── */}
          {activeTab === 'policy' && (
            <div className="space-y-6">
              {/* Formula Card */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <div className="flex items-center space-x-2">
                  <Sliders className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-base font-semibold text-white">Authoritative Scoring Formula</h3>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-cyan-300 overflow-x-auto">
                  {report.scoring_policy_summary.formula_definition ||
                    'overall_score = min(99, max(0, int(0.35 * skill_match + 0.20 * project_relevance + 0.20 * experience_match + 0.15 * semantic_fit + 0.10 * education_match)))'}
                </div>
                <p className="text-xs text-slate-400">
                  Inspected from <code className="text-indigo-300">backend/services/matching_service.py</code>. Scoring weights are strictly versioned ({report.policy_version}) and never adjusted merely to artificially improve fairness test outcomes.
                </p>
              </div>

              {/* Weight Grid */}
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                {[
                  { name: 'Skill Match', weight: '35%', desc: 'Canonicalized taxonomy matching with importance weights and bidirectional alias expansion.' },
                  { name: 'Project Relevance', weight: '20%', desc: 'Candidate project count, complexity, and technology overlap with role requirements.' },
                  { name: 'Experience Match', weight: '20%', desc: 'Years of professional domain experience against seniority requirements.' },
                  { name: 'Semantic Fit', weight: '15%', desc: 'TF-IDF lexical cosine similarity between resume context and job description.' },
                  { name: 'Education Match', weight: '10%', desc: 'Degree alignment and field of study credential hierarchy.' },
                ].map((item, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white">{item.name}</span>
                      <span className="text-sm font-bold text-indigo-400">{item.weight}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>

              {/* Policy Inputs vs Irrelevant Attributes */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                    Legitimate Influencing Inputs
                  </h4>
                  <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
                    <li>Technical & soft skills validated against role requirements</li>
                    <li>Years of professional domain experience</li>
                    <li>Verified projects with matching tech stacks</li>
                    <li>Formal educational credentials & degree tier</li>
                    <li>Document vocabulary relevance (TF-IDF semantic domain fit)</li>
                  </ul>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                    Strictly Irrelevant Attributes (Invariant Under Policy)
                  </h4>
                  <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
                    <li>Candidate Name (zero deterministic weight)</li>
                    <li>Demographic Proxy Variables (ethnicity, gender, religion, age)</li>
                    <li>Contact details: phone format, email host, physical address</li>
                    <li>Resume document section ordering</li>
                    <li>Bullet point marker syntax (• vs - vs *)</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* ─── Tab 4: Unassessed Dimensions & Limitations ─── */}
          {activeTab === 'unassessed' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 leading-relaxed">
                To maintain ethical integrity and scientific rigor, CareerLens AI explicitly documents dimensions of algorithmic fairness that cannot be assessed with synthetic counterfactual testing alone.
              </div>

              <div className="grid grid-cols-1 gap-4">
                {report.unassessed_dimensions.map((dim: UnassessedDimension, idx: number) => (
                  <div
                    key={idx}
                    className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-white">{dim.dimension}</h4>
                      <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {dim.status}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">{dim.reason}</p>

                    <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 space-y-1 text-xs">
                      <strong className="text-amber-400 text-[11px] block">Ethical Boundary</strong>
                      <p className="text-slate-400">{dim.ethical_boundary}</p>
                    </div>

                    <div className="text-xs text-slate-400 space-y-1">
                      <strong className="text-slate-400 uppercase text-[10px] block">Generalization Risk</strong>
                      <p className="italic text-slate-400">{dim.generalization_risk}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="p-10 rounded-2xl bg-slate-900/40 border border-slate-800 text-center max-w-lg mx-auto space-y-4 my-8">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
            <Scale className="w-6 h-6" />
          </div>
          <div className="space-y-1.5">
            <h3 className="text-base font-semibold text-white">Fairness & Scoring Consistency</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              {apiService.isAuthenticated()
                ? "No audit run yet. Click 'Run New Audit Suite' above to start testing candidate match scoring!"
                : "You need to sign in to use this feature. Please sign in or create an account to run fairness tests and view results."}
            </p>
          </div>
          {!apiService.isAuthenticated() && onOpenAuth && (
            <button
              type="button"
              onClick={onOpenAuth}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
            >
              <span>Sign In / Register</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};
