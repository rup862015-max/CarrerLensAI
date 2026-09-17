import React from 'react';

interface ScoreRadialProps {
  score: number;
  label: string;
  size?: 'sm' | 'md' | 'lg';
  subscores?: { label: string; score: number; color?: string }[];
}

export const ScoreRadial: React.FC<ScoreRadialProps> = ({ 
  score, 
  label, 
  size = 'md',
  subscores 
}) => {
  // Score color helper
  const getScoreColor = (val: number) => {
    if (val >= 85) return { stroke: '#10b981', text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' };
    if (val >= 70) return { stroke: '#6366f1', text: 'text-indigo-400', bg: 'bg-indigo-500/10', border: 'border-indigo-500/30' };
    if (val >= 55) return { stroke: '#f59e0b', text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' };
    return { stroke: '#f43f5e', text: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/30' };
  };

  const colors = getScoreColor(score);

  const sizeConfigs = {
    sm: { radius: 36, strokeWidth: 7, width: 90, height: 90, textSize: 'text-xl' },
    md: { radius: 52, strokeWidth: 9, width: 130, height: 130, textSize: 'text-3xl' },
    lg: { radius: 68, strokeWidth: 11, width: 170, height: 170, textSize: 'text-4xl' },
  };

  const cfg = sizeConfigs[size];
  const circumference = 2 * Math.PI * cfg.radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6 p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl backdrop-blur-sm">
      {/* Radial Ring */}
      <div className="relative flex flex-col items-center justify-center">
        <svg width={cfg.width} height={cfg.height} className="rotate-[-90deg]">
          {/* Background circle */}
          <circle
            cx={cfg.width / 2}
            cy={cfg.height / 2}
            r={cfg.radius}
            stroke="#1e293b"
            strokeWidth={cfg.strokeWidth}
            fill="transparent"
          />
          {/* Progress circle */}
          <circle
            cx={cfg.width / 2}
            cy={cfg.height / 2}
            r={cfg.radius}
            stroke={colors.stroke}
            strokeWidth={cfg.strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        <div className="absolute flex flex-col items-center justify-center">
          <span className={`font-black tracking-tight ${cfg.textSize} ${colors.text}`}>
            {score}
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">/ 100</span>
        </div>
        <p className="mt-2 text-xs font-semibold text-slate-300 text-center">{label}</p>
      </div>

      {/* Subscore Breakdown Bars */}
      {subscores && subscores.length > 0 && (
        <div className="flex-1 w-full space-y-3">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            Performance Breakdown
          </div>
          {subscores.map((sub, i) => {
            const barColor = sub.color || (sub.score >= 80 ? 'bg-indigo-500' : (sub.score >= 65 ? 'bg-cyan-500' : 'bg-amber-500'));
            return (
              <div key={i} className="space-y-1">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-300 font-medium">{sub.label}</span>
                  <span className="text-slate-200 font-bold">{sub.score}%</span>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-700 ease-out ${barColor}`}
                    style={{ width: `${sub.score}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
