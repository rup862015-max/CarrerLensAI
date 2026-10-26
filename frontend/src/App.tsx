import React, { useState, useEffect } from 'react';
import { TabType, ResumeAnalysisResponse, User } from './types';
import { apiService } from './services/api';
import { Navbar } from './components/Navbar';
import { AuthModal } from './components/AuthModal';
import { DashboardPage } from './pages/DashboardPage';
import { ResumeAnalysisPage } from './pages/ResumeAnalysisPage';
import { JobMatchingPage } from './pages/JobMatchingPage';
import { CareerSimulatorPage } from './pages/CareerSimulatorPage';
import { SkillRoadmapPage } from './pages/SkillRoadmapPage';
import { SecurityAuditPage } from './pages/SecurityAuditPage';
import { InterviewPage } from './pages/InterviewPage';
import { FairnessAuditPage } from './pages/FairnessAuditPage';
import { Phase2Placeholder } from './components/Phase2Placeholder';
import { ShieldAlert, LogIn } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const [currentAnalysis, setCurrentAnalysis] = useState<ResumeAnalysisResponse | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Phase 2 Modal State
  const [phase2Modal, setPhase2Modal] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    features: string[];
  }>({
    isOpen: false,
    title: '',
    description: '',
    features: [],
  });

  // Check auth and load initial resume on startup
  useEffect(() => {
    const initData = async () => {
      try {
        const currentUser = await apiService.getMe();
        setUser(currentUser);
        if (currentUser) {
          const latest = await apiService.getLatestResume();
          setCurrentAnalysis(latest);
        } else {
          setCurrentAnalysis(null);
        }
      } catch (err) {
        setUser(null);
        setCurrentAnalysis(null);
      }
    };
    initData();
  }, []);

  // Listen for automatic session expiry (HTTP 401)
  useEffect(() => {
    const handleAuthExpired = () => {
      setUser(null);
      setCurrentAnalysis(null);
      setIsAuthModalOpen(true);
    };
    window.addEventListener('auth:expired', handleAuthExpired);
    return () => window.removeEventListener('auth:expired', handleAuthExpired);
  }, []);

  const handleLoginSuccess = async (loggedInUser: User) => {
    setUser(loggedInUser);
    try {
      const latest = await apiService.getLatestResume();
      setCurrentAnalysis(latest);
    } catch {
      setCurrentAnalysis(null);
    }
  };

  const handleLogout = async () => {
    await apiService.logout();
    setUser(null);
    setCurrentAnalysis(null);
  };

  const handleOpenPhase2 = (title: string, description: string, features: string[]) => {
    setPhase2Modal({
      isOpen: true,
      title,
      description,
      features,
    });
  };

  const handleClosePhase2 = () => {
    setPhase2Modal(prev => ({ ...prev, isOpen: false }));
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        onSelectTab={(tab) => setActiveTab(tab)}
        onOpenPhase2={handleOpenPhase2}
        user={user}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!user && (
          <div className="mb-6 p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg shadow-indigo-950/20">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 shrink-0">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">Guest Session Mode</h4>
                <p className="text-xs text-slate-300">
                  Sign in or register an account to save your resumes, simulate careers, and ensure strict privacy data isolation.
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shrink-0 cursor-pointer transition-colors shadow-sm"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In / Register</span>
            </button>
          </div>
        )}

        {activeTab === 'dashboard' && (
          <DashboardPage
            currentAnalysis={currentAnalysis}
            onNavigate={(tab) => setActiveTab(tab)}
            onOpenPhase2={handleOpenPhase2}
          />
        )}

        {activeTab === 'resume-analysis' && (
          <ResumeAnalysisPage
            analysisResult={currentAnalysis}
            onAnalysisComplete={(result) => setCurrentAnalysis(result)}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'job-matching' && (
          <JobMatchingPage
            currentAnalysis={currentAnalysis}
            onOpenPhase2={handleOpenPhase2}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'career-simulator' && (
          <CareerSimulatorPage
            currentAnalysis={currentAnalysis}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'skill-roadmap' && (
          <SkillRoadmapPage
            currentAnalysis={currentAnalysis}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'security-audit' && (
          <SecurityAuditPage
            currentAnalysis={currentAnalysis}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'interview' && (
          <InterviewPage
            currentAnalysis={currentAnalysis}
            onNavigate={(tab) => setActiveTab(tab)}
            onOpenAuth={() => setIsAuthModalOpen(true)}
          />
        )}

        {activeTab === 'fairness-audit' && (
          <FairnessAuditPage
            currentAnalysis={currentAnalysis}
            onNavigate={(tab) => setActiveTab(tab)}
            onOpenAuth={() => setIsAuthModalOpen(true)}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/60 py-6 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-center">
          <p>© 2026 CareerLens AI — Explainable Career Intelligence & Job Matching System</p>
        </div>
      </footer>

      {/* Phase 2 Placeholder Modal */}
      <Phase2Placeholder
        isOpen={phase2Modal.isOpen}
        onClose={handleClosePhase2}
        title={phase2Modal.title}
        description={phase2Modal.description}
        features={phase2Modal.features}
      />

      {/* Authentication Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={handleLoginSuccess}
      />
    </div>
  );
};

export default App;
