import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, Sparkles, AlertCircle, Loader2 } from 'lucide-react';
import { apiService } from '../services/api';
import { ResumeAnalysisResponse } from '../types';

interface ResumeUploadProps {
  onAnalysisComplete: (result: ResumeAnalysisResponse) => void;
}

const LOADING_STAGES = [
  'Extracting raw content...',
  'Analyzing profile & career timeline...',
  'Identifying skills & taxonomy graph...',
  'Evaluating ATS readability & metrics...',
  'Building structured career profile...'
];

export const ResumeUpload: React.FC<ResumeUploadProps> = ({ onAnalysisComplete }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const simulateLoadingStages = async (callback: () => Promise<ResumeAnalysisResponse>) => {
    setIsLoading(true);
    setErrorMessage(null);
    setCurrentStageIdx(0);

    const interval = setInterval(() => {
      setCurrentStageIdx((prev) => (prev < LOADING_STAGES.length - 1 ? prev + 1 : prev));
    }, 450);

    try {
      const result = await callback();
      // Wait slight buffer so user sees stages
      setTimeout(() => {
        clearInterval(interval);
        setIsLoading(false);
        onAnalysisComplete(result);
      }, 1200);
    } catch (err: any) {
      clearInterval(interval);
      setIsLoading(false);
      setErrorMessage(err.message || 'An error occurred during resume analysis.');
    }
  };

  const handleFile = async (file: File) => {
    if (!file) return;

    const validTypes = ['.pdf', '.docx', '.txt'];
    const hasValidExt = validTypes.some(ext => file.name.toLowerCase().endsWith(ext));

    if (!hasValidExt) {
      setErrorMessage('Unsupported file format. Please upload a PDF (.pdf) or Word document (.docx).');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage('File exceeds 10 MB limit.');
      return;
    }

    setFileName(file.name);
    await simulateLoadingStages(() => apiService.uploadResume(file));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleLoadDemo = async () => {
    setFileName('Alex_Mercer_Software_Engineer.pdf');
    const demoText = `Alex Mercer
San Francisco, CA | alex.mercer@email.com | (555) 019-2834 | linkedin.com/in/alexmercer

PROFESSIONAL SUMMARY
Results-oriented Software Engineer with 2+ years of experience designing, developing, and deploying scalable web services, RESTful APIs, and responsive frontends.

EDUCATION
B.Tech Information Technology | University of California, Berkeley (2019 - 2023)
GPA: 3.8/4.0 | Dean's Honor List

TECHNICAL SKILLS
Languages: Python, JavaScript, TypeScript, Java, SQL, HTML, CSS
Frameworks & Libraries: React, Node.js, Express, FastAPI, Tailwind CSS, Redux
Databases: PostgreSQL, MySQL, MongoDB, SQLite, Redis
Tools & DevOps: Git, Docker, Linux, CI/CD pipelines, REST APIs, Microservices

WORK EXPERIENCE
Software Developer Intern | Apex Tech Solutions (2022 - 2023)
• Developed and deployed 12+ RESTful API microservices using Node.js, FastAPI, and PostgreSQL, serving 50,000+ daily requests.
• Optimized database queries and created indexing strategies in MongoDB, reducing average API response times by 38%.
• Collaborated in an Agile Scrum squad of 6 engineers, participating in bi-weekly sprints and peer code reviews.

PROJECTS
Food Delivery Platform (React, Node.js, MongoDB)
• Architected a full-stack food delivery web application using React, Express, and MongoDB.
• Implemented secure JWT-based candidate authentication and Stripe payment integration.

AI Resume & Job Matcher (Python, FastAPI, SQL, Git)
• Engineered an NLP matching pipeline using Python, Scikit-Learn, and FastAPI to score resume-job alignment.
• Built SQLite schema migrations and designed intuitive REST endpoints for candidate profile extraction.`;

    await simulateLoadingStages(() => apiService.analyzeResumeText(demoText, 'Demo_Software_Engineer_Resume.pdf'));
  };

  return (
    <div className="w-full space-y-4">
      {/* Upload Box */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 transition-all duration-200 text-center ${
          isDragging 
            ? 'border-indigo-400 bg-indigo-500/10' 
            : 'border-slate-700 hover:border-slate-600 bg-slate-900/40 hover:bg-slate-900/60'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFile(e.target.files[0]);
            }
          }}
        />

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-6 space-y-4">
            <div className="relative">
              <Loader2 className="w-12 h-12 text-indigo-400 animate-spin" />
              <Sparkles className="w-5 h-5 text-cyan-300 absolute -top-1 -right-1 animate-pulse" />
            </div>
            
            <div className="space-y-1">
              <p className="text-sm font-semibold text-white">
                {fileName ? `Processing ${fileName}` : 'Analyzing Resume...'}
              </p>
              <p className="text-xs text-indigo-300 font-medium animate-pulse">
                {LOADING_STAGES[currentStageIdx]}
              </p>
            </div>

            {/* Stepper Dots */}
            <div className="flex space-x-1.5 pt-2">
              {LOADING_STAGES.map((_, idx) => (
                <div
                  key={idx}
                  className={`h-1.5 rounded-full transition-all duration-300 ${
                    idx <= currentStageIdx ? 'w-6 bg-indigo-400' : 'w-2 bg-slate-700'
                  }`}
                />
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-105 transition-transform">
              <UploadCloud className="w-8 h-8" />
            </div>

            <div className="space-y-1 max-w-sm">
              <h3 className="text-base font-bold text-white">Upload your resume</h3>
              <p className="text-xs text-slate-400">
                Drag & drop your resume file here or browse from your device
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all flex items-center space-x-2"
              >
                <FileText className="w-4 h-4" />
                <span>Browse Files</span>
              </button>

              <button
                type="button"
                onClick={handleLoadDemo}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-all flex items-center space-x-2"
              >
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Load Demo Resume</span>
              </button>
            </div>

            <p className="text-[11px] text-slate-500 font-medium">
              Supported Formats: PDF / DOCX • Max 10 MB
            </p>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-3 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
          <div>
            <span className="font-bold">Upload Error: </span>
            {errorMessage}
          </div>
        </div>
      )}
    </div>
  );
};
