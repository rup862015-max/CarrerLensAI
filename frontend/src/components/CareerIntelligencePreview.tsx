import React from 'react';
import { Compass, Sparkles, TrendingUp, PlusCircle, ArrowRight } from 'lucide-react';
import { CareerPreview } from '../types';

interface CareerIntelligencePreviewProps {
  careerPreview: CareerPreview;
  onExploreSimulation: () => void;
}

export const CareerIntelligencePreview: React.FC<CareerIntelligencePreviewProps> = ({
  careerPreview,
  onExploreSimulation,
}) => {
  return (
    <div className="p-6 rounded-2xl bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-cyan-950/40 border border-indigo-500/30 space-y-6 shadow-xl relative overflow-hidden">
      {/* Background ambient glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Compass className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Career Intelligence Preview</h3>
            <p className="text-xs text-slate-400">Algorithmic career progression & transition modeling</p>
          </div>
        </div>

        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 flex items-center space-x-1">
          <Sparkles className="w-3 h-3" />
          <span>Readiness: {careerPreview.readiness_level}</span>
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Current Strongest Path */}
        <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Current Strongest Path
          </span>
          <div className="flex items-baseline justify-between">
            <h4 className="text-base font-bold text-white">{careerPreview.current_strongest_path}</h4>
            <span className="text-sm font-black text-indigo-400">
              {careerPreview.match_percentage}% Match
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Strongest empirical alignment with your current project and technology stack.
          </p>
        </div>

        {/* Potential Next Step */}
        <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-400 flex items-center space-x-1">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Potential Next Step</span>
          </span>
          <h4 className="text-base font-bold text-white">{careerPreview.potential_next_step}</h4>
          <p className="text-xs text-slate-400">
            High-leverage career milestone accessible by closing targeted skill gaps.
          </p>
        </div>
      </div>

      {/* Skills to Add */}
      <div className="space-y-2">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Target Skills to Accelerate Trajectory:
        </span>
        <div className="flex flex-wrap gap-2">
          {careerPreview.skills_to_add && careerPreview.skills_to_add.map((skill, idx) => (
            <span
              key={idx}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/30"
            >
              <PlusCircle className="w-3.5 h-3.5 text-indigo-400" />
              <span>{skill}</span>
            </span>
          ))}
        </div>
      </div>

      {/* CTA Button */}
      <div className="pt-2 flex justify-end">
        <button
          type="button"
          onClick={onExploreSimulation}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white text-xs font-bold shadow-lg shadow-indigo-500/20 transition-all flex items-center space-x-2 group"
        >
          <span>Explore Career Simulation</span>
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>
  );
};
