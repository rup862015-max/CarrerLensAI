import React, { useState, useEffect } from 'react';
import { TabType, ResumeAnalysisResponse } from './types';
import { apiService } from './services/api';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { ResumeAnalysisPage } from './pages/ResumeAnalysisPage';
import { JobMatchingPage } from './pages/JobMatchingPage';
import { Phase2Placeholder } from './components/Phase2Placeholder';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const [currentAnalysis, setCurrentAnalysis] = useState<ResumeAnalysisResponse | null>(null);

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

  // Load initial resume on startup
  useEffect(() => {
    const initData = async () => {
      // 1. Try to load latest resume from database
      const latest = await apiService.getLatestResume();
      if (latest) {
        setCurrentAnalysis(latest);
      } else {
        // 2. Default initial demo resume state
        const demoAnalysis: ResumeAnalysisResponse = {
          resume_id: 'res_demo_default',
          filename: 'Software_Engineer_Resume.pdf',
          health_scores: {
            overall: 82,
            content_quality: 86,
            skills_coverage: 91,
            experience_clarity: 78,
            project_strength: 84,
            ats_readability: 80,
          },
          extracted_profile: {
            candidate_name: 'Alex Mercer',
            email: 'alex.mercer@email.com',
            phone: '(555) 019-2834',
            education: ['B.Tech Information Technology | University of California, Berkeley (2019 - 2023)'],
            experience: [
              'Software Developer Intern | Apex Tech Solutions (2022 - 2023): Developed and deployed 12+ RESTful API microservices using Node.js, FastAPI, and PostgreSQL.',
              'Optimized database queries and created indexing strategies in MongoDB, reducing average API response times by 38%.',
            ],
            years_of_experience: 2.0,
            skills: [
              'Python', 'JavaScript', 'TypeScript', 'Java', 'SQL', 
              'React', 'Node.js', 'FastAPI', 'MongoDB', 'PostgreSQL', 
              'Docker', 'Git', 'REST APIs', 'Microservices'
            ],
            projects: [
              {
                title: 'Food Delivery Platform',
                technologies: ['React', 'Node.js', 'MongoDB'],
                evidence: [
                  'Backend REST API development and JWT authentication.',
                  'Database schema optimization and indexing in MongoDB.',
                  'Responsive frontend state management and checkout flow.'
                ],
                inferred_skills: ['REST APIs', 'JavaScript', 'Database Design']
              },
              {
                title: 'AI Resume & Job Matcher',
                technologies: ['Python', 'FastAPI', 'SQL', 'Git'],
                evidence: [
                  'Architected NLP keyword extraction and similarity algorithms.',
                  'Integrated SQLite database layer with relational schemas.',
                  'Automated CI/CD workflows and unit test suites with GitHub Actions.'
                ],
                inferred_skills: ['Microservices', 'CI/CD', 'Data Structures']
              }
            ]
          }
        };
        setCurrentAnalysis(demoAnalysis);
      }
    };
    initData();
  }, []);

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
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/60 py-6 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>© 2026 CareerLens AI — Explainable Career Intelligence & Job Matching System (Phase 1)</p>
          <div className="flex items-center space-x-4 text-[11px] text-slate-400">
            <span>FastAPI + SQLite Backend</span>
            <span>•</span>
            <span>React + TypeScript Frontend</span>
            <span>•</span>
            <span>Explainable AI Engine</span>
          </div>
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
    </div>
  );
};

export default App;
