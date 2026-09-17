import React from 'react';
import { 
  Sparkles, 
  LayoutDashboard, 
  FileSearch, 
  Target, 
  Compass, 
  MapPin, 
  MessageSquare, 
  ShieldCheck, 
  Scale 
} from 'lucide-react';
import { TabType } from '../types';

interface NavbarProps {
  activeTab: TabType;
  onSelectTab: (tab: TabType) => void;
  onOpenPhase2: (title: string, desc: string, items: string[]) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onSelectTab, onOpenPhase2 }) => {
  const functionalTabs = [
    { id: 'dashboard' as TabType, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'resume-analysis' as TabType, label: 'Resume Analysis', icon: FileSearch },
    { id: 'job-matching' as TabType, label: 'Job Matching', icon: Target },
  ];

  const phase2Tabs = [
    { 
      id: 'career-simulator' as TabType, 
      label: 'Career Simulator', 
      icon: Compass,
      desc: 'Simulate the impact of acquiring new technical competencies and forecast job alignment.',
      items: ['Dynamic what-if skill impact forecasting', 'Target role salary & readiness projection', 'Path transition feasibility mapping']
    },
    { 
      id: 'skill-roadmap' as TabType, 
      label: 'Skill Roadmap', 
      icon: MapPin,
      desc: 'Generate curated step-by-step learning roadmaps aligned with market demand.',
      items: ['Curated project & certification milestones', 'Effort estimation & timeline forecasting', 'Course & documentation recommendations']
    },
    { 
      id: 'interview' as TabType, 
      label: 'Interview', 
      icon: MessageSquare,
      desc: 'Interactive AI-driven behavioral and technical mock interview simulation.',
      items: ['Real-time STAR method answer evaluation', 'Role-specific system design & coding prompts', 'Confidence & clarity scoring']
    },
    { 
      id: 'security-audit' as TabType, 
      label: 'Security Audit', 
      icon: ShieldCheck,
      desc: 'AI prompt injection and hidden resume prompt injection vulnerability scanning.',
      items: ['White-text & zero-width character detection', 'Prompt injection payload defense', 'Metadata sanitization & authenticity verification']
    },
    { 
      id: 'fairness-audit' as TabType, 
      label: 'Fairness Audit', 
      icon: Scale,
      desc: 'Algorithmic bias audit to ensure non-discriminatory candidate evaluation.',
      items: ['Demographic parity & proxy variable audit', 'Gender & ethnicity neutral language scoring', 'Audit compliance certificate generation']
    },
  ];

  return (
    <header className="sticky top-0 z-40 bg-[#090d16]/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Name */}
          <div 
            className="flex items-center space-x-3 cursor-pointer select-none"
            onClick={() => onSelectTab('dashboard')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-lg font-bold tracking-tight text-white">CareerLens AI</span>
                <span className="text-[10px] font-semibold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full">Phase 1</span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">Explainable Career Intelligence & Job Matching</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center space-x-1">
            {/* Functional Tabs */}
            {functionalTabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onSelectTab(tab.id)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                    isActive 
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-sm' 
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}

            <div className="h-5 w-[1px] bg-slate-800 mx-2" />

            {/* Phase 2 Coming Soon Tabs */}
            {phase2Tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => onOpenPhase2(tab.label, tab.desc, tab.items)}
                  className="group relative flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 transition-colors"
                >
                  <Icon className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300" />
                  <span>{tab.label}</span>
                  <span className="text-[9px] font-semibold text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700/60">P2</span>
                </button>
              );
            })}
          </nav>

          {/* Mobile Navigation Dropdown Button */}
          <div className="flex lg:hidden items-center space-x-2">
            <select
              aria-label="Navigation Menu"
              value={activeTab}
              onChange={(e) => {
                const val = e.target.value as TabType;
                const p2 = phase2Tabs.find(t => t.id === val);
                if (p2) {
                  onOpenPhase2(p2.label, p2.desc, p2.items);
                } else {
                  onSelectTab(val);
                }
              }}
              className="bg-slate-800 text-slate-200 text-xs rounded-lg px-3 py-2 border border-slate-700 outline-none"
            >
              <optgroup label="Core Modules (Phase 1)">
                <option value="dashboard">Dashboard</option>
                <option value="resume-analysis">Resume Analysis</option>
                <option value="job-matching">Job Matching</option>
              </optgroup>
              <optgroup label="Phase 2 Previews">
                <option value="career-simulator">Career Simulator (P2)</option>
                <option value="skill-roadmap">Skill Roadmap (P2)</option>
                <option value="interview">Interview Simulator (P2)</option>
                <option value="security-audit">Security Audit (P2)</option>
                <option value="fairness-audit">Fairness Audit (P2)</option>
              </optgroup>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};
