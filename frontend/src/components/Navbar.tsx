import React from 'react';
import { 
  Sparkles, 
  LayoutDashboard, 
  FileSearch, 
  Target, 
  Compass, 
  MapPin, 
  MessageSquare, 
  ShieldCheck 
} from 'lucide-react';
import { TabType, User } from '../types';
import { LogIn, LogOut } from 'lucide-react';

interface NavbarProps {
  activeTab: TabType;
  onSelectTab: (tab: TabType) => void;
  onOpenPhase2: (title: string, desc: string, items: string[]) => void;
  user: User | null;
  onOpenAuth: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ 
  activeTab, 
  onSelectTab, 
  onOpenPhase2,
  user,
  onOpenAuth,
  onLogout,
}) => {
  const functionalTabs = [
    { id: 'dashboard' as TabType, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'resume-analysis' as TabType, label: 'Resume Analysis', icon: FileSearch },
    { id: 'job-matching' as TabType, label: 'Job Matching', icon: Target },
    { id: 'career-simulator' as TabType, label: 'Career Simulator', icon: Compass },
    { id: 'skill-roadmap' as TabType, label: 'Skill Roadmap', icon: MapPin },
    { id: 'security-audit' as TabType, label: 'Security Audit', icon: ShieldCheck },
    { id: 'interview' as TabType, label: 'Interview Prep', icon: MessageSquare },
  ];

  const phase2Tabs: any[] = [];

  const username = user?.username || (user?.email ? user.email.split('@')[0] : 'user');
  const displayName = user?.full_name || user?.username || (user?.email ? user.email.split('@')[0] : 'User');
  const userInitial = (username ? username.charAt(0) : 'U').toUpperCase();

  return (
    <header className="sticky top-0 z-40 bg-[#090d16]/95 backdrop-blur-md border-b border-slate-800">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-3">

          {/* ─── LEFT: Account ID followed horizontally by all tabs ─── */}
          <div className="flex items-center space-x-3 overflow-x-auto no-scrollbar py-1 min-w-0">
            {/* Account ID on top-left of the application */}
            <div className="flex items-center space-x-2 shrink-0 pr-3 border-r border-slate-800">
              {user ? (
                <div className="flex items-center space-x-2.5 bg-slate-900/90 px-3 py-1.5 rounded-xl border border-slate-800 hover:border-slate-700 transition-colors shadow-sm">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-cyan-500 flex items-center justify-center text-white text-xs font-bold shadow-sm shrink-0">
                    {userInitial}
                  </div>
                  <div className="text-left shrink-0">
                    <p className="text-xs font-semibold text-slate-100 leading-tight">
                      {displayName}
                    </p>
                    <p className="text-[10px] text-slate-400 leading-tight font-mono">
                      @{username}
                    </p>
                  </div>
                  <button
                    onClick={onLogout}
                    title="Sign Out"
                    className="ml-1 p-1 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors cursor-pointer"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={onOpenAuth}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 transition-all shadow-sm shadow-indigo-600/30 cursor-pointer"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span>Sign In</span>
                </button>
              )}
            </div>

            {/* Dashboard View & all other tabs on the left side horizontally */}
            <nav className="hidden lg:flex items-center space-x-1 shrink-0">
              {functionalTabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => onSelectTab(tab.id)}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 cursor-pointer shrink-0 ${
                      isActive 
                        ? 'bg-indigo-600/25 text-indigo-200 border border-indigo-500/40 shadow-sm' 
                        : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                    <span>{tab.label}</span>
                    {(tab as any).badge && (
                      <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        {(tab as any).badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* ─── RIGHT: CareerLens AI Brand Logo & Name ─── */}
          <div 
            className="flex items-center space-x-2.5 cursor-pointer select-none shrink-0 pl-3 border-l border-slate-800/60"
            onClick={() => onSelectTab('dashboard')}
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-md shadow-indigo-500/20">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <span className="text-sm font-bold tracking-tight text-white">CareerLens AI</span>
              <p className="text-[10px] text-slate-400 hidden xl:block">Explainable Career Intelligence</p>
            </div>
          </div>

          {/* Mobile Navigation Dropdown */}
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
              <optgroup label="Active Modules">
                <option value="dashboard">Dashboard</option>
                <option value="resume-analysis">Resume Analysis</option>
                <option value="job-matching">Job Matching</option>
                <option value="career-simulator">Career Simulator</option>
                <option value="skill-roadmap">Skill Roadmap</option>
                <option value="security-audit">Security Audit</option>
                <option value="interview">Interview Prep</option>
              </optgroup>
            </select>
          </div>

        </div>
      </div>
    </header>
  );
};
