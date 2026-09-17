import React from 'react';
import { Sparkles, X, CheckCircle2 } from 'lucide-react';

interface Phase2PlaceholderProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description: string;
  features: string[];
}

export const Phase2Placeholder: React.FC<Phase2PlaceholderProps> = ({
  isOpen,
  onClose,
  title,
  description,
  features,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="w-full max-w-lg bg-slate-900 border border-slate-700/80 rounded-3xl p-6 sm:p-8 space-y-6 shadow-2xl relative overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Ambient Top Glow */}
        <div className="absolute top-0 right-1/2 translate-x-1/2 w-48 h-20 bg-indigo-500/20 rounded-full blur-2xl pointer-events-none" />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
            <span>Coming in Phase 2</span>
          </div>
          <h2 className="text-xl font-bold text-white">{title}</h2>
          <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
        </div>

        {/* Features List */}
        <div className="space-y-3 p-4 rounded-2xl bg-slate-800/40 border border-slate-700/50">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Planned Phase 2 Capabilities:
          </h4>
          <ul className="space-y-2.5">
            {features.map((feat, idx) => (
              <li key={idx} className="text-xs text-slate-200 flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>{feat}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Action button */}
        <div className="flex justify-end space-x-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all"
          >
            Got it, Return to App
          </button>
        </div>
      </div>
    </div>
  );
};
