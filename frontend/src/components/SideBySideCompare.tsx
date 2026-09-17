import React from 'react';
import { CheckCircle2, XCircle, ArrowRightLeft } from 'lucide-react';

interface SideBySideCompareProps {
  sideBySide: {
    profile_skills: { name: string; has_match: boolean }[];
    job_requirements: { name: string; matched: boolean; importance: string }[];
  };
}

export const SideBySideCompare: React.FC<SideBySideCompareProps> = ({ sideBySide }) => {
  return (
    <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <ArrowRightLeft className="w-5 h-5 text-indigo-400" />
          <h3 className="text-base font-bold text-white">Resume vs Job Side-by-Side Comparison</h3>
        </div>
        <span className="text-xs text-slate-400">Direct Alignment Checklist</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Candidate Profile Column */}
        <div className="space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
              Your Profile Skills
            </span>
            <span className="text-[11px] text-slate-400">
              {sideBySide.profile_skills.filter(s => s.has_match).length} / {sideBySide.profile_skills.length} Matched
            </span>
          </div>

          <div className="space-y-2">
            {sideBySide.profile_skills.map((skill, idx) => (
              <div 
                key={idx}
                className={`flex items-center justify-between p-2.5 rounded-xl border text-xs transition-colors ${
                  skill.has_match 
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200' 
                    : 'bg-slate-800/40 border-slate-700/60 text-slate-300'
                }`}
              >
                <span className="font-medium">{skill.name}</span>
                {skill.has_match ? (
                  <span className="flex items-center space-x-1 text-emerald-400 text-[11px] font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>In Demand</span>
                  </span>
                ) : (
                  <span className="text-slate-500 text-[11px]">Additional Competency</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Job Requirements Column */}
        <div className="space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">
              Job Requirements
            </span>
            <span className="text-[11px] text-slate-400">
              {sideBySide.job_requirements.filter(r => r.matched).length} / {sideBySide.job_requirements.length} Satisfied
            </span>
          </div>

          <div className="space-y-2">
            {sideBySide.job_requirements.map((req, idx) => (
              <div 
                key={idx}
                className={`flex items-center justify-between p-2.5 rounded-xl border text-xs transition-colors ${
                  req.matched 
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200' 
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-200'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <span className="font-medium">{req.name}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded uppercase font-bold ${
                    req.importance === 'critical' ? 'bg-rose-500/20 text-rose-300' : 'bg-slate-700 text-slate-300'
                  }`}>
                    {req.importance}
                  </span>
                </div>

                {req.matched ? (
                  <span className="flex items-center space-x-1 text-emerald-400 text-[11px] font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Satisfied</span>
                  </span>
                ) : (
                  <span className="flex items-center space-x-1 text-rose-400 text-[11px] font-bold">
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Missing Gap</span>
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
