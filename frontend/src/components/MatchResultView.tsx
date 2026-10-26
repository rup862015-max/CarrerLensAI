import React, { useState } from 'react';
import { 
  CheckCircle2, 
  ChevronRight, 
  FileText, 
  Award, 
  Lightbulb, 
  Info,
  AlertTriangle,
  XCircle
} from 'lucide-react';
import { MatchResponse, MatchedRequirement } from '../types';
import { ScoreRadial } from './ScoreRadial';
import { SideBySideCompare } from './SideBySideCompare';
import { CareerIntelligencePreview } from './CareerIntelligencePreview';

interface MatchResultViewProps {
  matchResult: MatchResponse;
  onExploreSimulation: () => void;
}

export const MatchResultView: React.FC<MatchResultViewProps> = ({
  matchResult,
  onExploreSimulation,
}) => {
  const [selectedRequirement, setSelectedRequirement] = useState<MatchedRequirement | null>(
    matchResult.matched_requirements && matchResult.matched_requirements.length > 0
      ? matchResult.matched_requirements[0]
      : null
  );

  const subscores = [
    { label: 'Skill Match', score: matchResult.skill_match, color: 'bg-indigo-500' },
    { label: 'Experience Clarity', score: matchResult.experience_match, color: 'bg-cyan-500' },
    { label: 'Education Fit', score: matchResult.education_match, color: 'bg-emerald-500' },
    { label: 'Project Relevance', score: matchResult.project_relevance, color: 'bg-amber-500' },
    { label: 'Semantic Fit', score: matchResult.semantic_fit, color: 'bg-purple-500' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Header Card */}
      <div className="p-6 sm:p-8 rounded-3xl bg-slate-900/80 border border-slate-800 shadow-2xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 text-xs font-semibold mb-2">
              <Award className="w-3.5 h-3.5" />
              <span>Target Role: {matchResult.job_title}</span>
            </div>
            <h2 className="text-2xl font-black text-white tracking-tight">
              Explainable Job Match Evaluation
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Multi-dimensional candidate-to-role fit calculated with 3-layer hybrid AI engine.
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-slate-800/80 px-4 py-2 rounded-2xl border border-slate-700">
            <span className="text-xs text-slate-400">Match Grade:</span>
            <span className="text-xl font-black text-emerald-400">{matchResult.match_grade}</span>
          </div>
        </div>

        {/* Score Radial & Subscore Breakdown */}
        <ScoreRadial
          score={matchResult.overall_score}
          label="Overall Match"
          size="lg"
          subscores={subscores}
        />
      </div>

      {/* Matched Requirements & Evidence Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Clickable Matched Requirements List */}
        <div className="lg:col-span-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span>Strong Matched Requirements ({matchResult.matched_requirements.length})</span>
            </h3>
            <span className="text-xs text-slate-400">Click to inspect evidence</span>
          </div>

          <div className="space-y-2.5">
            {matchResult.matched_requirements.map((req, idx) => {
              const isSelected = selectedRequirement?.requirement === req.requirement;
              return (
                <div
                  key={idx}
                  onClick={() => setSelectedRequirement(req)}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all flex items-center justify-between group ${
                    isSelected
                      ? 'bg-indigo-600/15 border-indigo-500 shadow-md text-white'
                      : 'bg-slate-900/50 border-slate-800 hover:border-slate-700 text-slate-300'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="font-semibold text-xs text-white group-hover:text-indigo-300 transition-colors">
                        {req.requirement}
                      </span>
                      <div className="flex items-center space-x-2 mt-0.5 text-[10px] text-slate-400">
                        <span className="capitalize">{req.match_type.replace('_', ' ')}</span>
                        <span>•</span>
                        <span className="text-emerald-400 font-bold">{Math.round(req.confidence * 100)}% Confidence</span>
                      </div>
                    </div>
                  </div>

                  <ChevronRight className={`w-4 h-4 text-slate-500 transition-transform ${isSelected ? 'translate-x-1 text-indigo-400' : ''}`} />
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Explainable Evidence Drawer/Inspector */}
        <div className="lg:col-span-6 space-y-4">
          <h3 className="text-base font-bold text-white flex items-center space-x-2">
            <Info className="w-5 h-5 text-cyan-400" />
            <span>Explainable Evidence Inspector</span>
          </h3>

          {selectedRequirement ? (
            <div className="p-6 rounded-3xl bg-slate-900/80 border border-slate-800 space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Inspecting Requirement</span>
                  <h4 className="text-lg font-bold text-white">{selectedRequirement.requirement}</h4>
                </div>
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Confidence</span>
                  <p className="text-sm font-black text-emerald-400">
                    {Math.round(selectedRequirement.confidence * 100)}%
                  </p>
                </div>
              </div>

              {/* Evidence Snippet */}
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                  <FileText className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Verified Resume Evidence Snippet:</span>
                </span>
                <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 text-xs text-slate-200 leading-relaxed font-mono">
                  "{selectedRequirement.resume_evidence}"
                </div>
              </div>

              {/* Evidence Locations */}
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Supporting Sections Found:
                </span>
                <div className="flex flex-wrap gap-2">
                  {selectedRequirement.evidence_locations && selectedRequirement.evidence_locations.map((loc, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 text-xs font-medium"
                    >
                      {loc}
                    </span>
                  ))}
                </div>
              </div>

              {/* Match Details Tag */}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/80 text-xs text-slate-400">
                <span>Evidence Type: <strong className="text-slate-200 capitalize">{selectedRequirement.match_type.replace('_', ' ')}</strong></span>
                <span>Requirement Weight: <strong className="text-slate-200 capitalize">{selectedRequirement.importance}</strong></span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  selectedRequirement.status === 'matched'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : selectedRequirement.status === 'partial'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                    : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                }`}>
                  Status: {selectedRequirement.status}
                </span>
              </div>

              {/* Scoring Contribution */}
              {selectedRequirement.scoring_contribution && (
                <div className="space-y-1 pt-2 border-t border-slate-800">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                    Configured Scoring Contribution:
                  </span>
                  <p className="text-xs text-indigo-300 font-mono bg-indigo-950/30 p-2.5 rounded-xl border border-indigo-500/20">
                    {selectedRequirement.scoring_contribution}
                  </p>
                </div>
              )}

              {/* Uncertainty Assessment */}
              {selectedRequirement.uncertainty_note && (
                <div className="space-y-1 pt-2 border-t border-slate-800">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                    Evidence Boundary & Uncertainty:
                  </span>
                  <p className="text-xs text-slate-400 italic">
                    {selectedRequirement.uncertainty_note}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 rounded-3xl bg-slate-900/40 border border-dashed border-slate-800 text-center text-xs text-slate-500">
              Select a requirement on the left to inspect candidate evidence.
            </div>
          )}
        </div>
      </div>

      {/* Skill Gaps Section */}
      {matchResult.skill_gaps && matchResult.skill_gaps.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              <span>Identified Skill Gaps & Prioritization ({matchResult.skill_gaps.length})</span>
            </h3>
            <span className="text-xs text-slate-400">Benchmark Market Demand</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {matchResult.skill_gaps.map((gap, idx) => (
              <div
                key={idx}
                className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-sm text-white">{gap.skill}</h4>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      gap.priority === 'High'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    }`}
                  >
                    {gap.priority} Priority
                  </span>
                </div>

                <div className="space-y-1.5 text-xs">
                  <p className="text-slate-300 font-medium">{gap.why_it_matters}</p>
                  <p className="text-slate-400 text-[11px]">{gap.market_prevalence}</p>
                </div>

                <div className="pt-2 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center space-x-1">
                  <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                  <span>{gap.current_evidence}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Side by Side Comparison */}
      <SideBySideCompare sideBySide={matchResult.side_by_side} />

      {/* Career Intelligence Preview Card */}
      <CareerIntelligencePreview
        careerPreview={matchResult.career_preview}
        onExploreSimulation={onExploreSimulation}
      />

      {/* Recommendations Banner */}
      {matchResult.recommendations && matchResult.recommendations.length > 0 && (
        <div className="p-6 rounded-2xl bg-indigo-950/30 border border-indigo-500/30 space-y-3">
          <h4 className="text-sm font-bold text-white flex items-center space-x-2">
            <Lightbulb className="w-4 h-4 text-cyan-400" />
            <span>Strategic Resume Improvement Recommendations</span>
          </h4>
          <ul className="space-y-2">
            {matchResult.recommendations.map((rec, idx) => (
              <li key={idx} className="text-xs text-slate-300 flex items-start space-x-2">
                <span className="text-indigo-400 font-bold mt-0.5">→</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
