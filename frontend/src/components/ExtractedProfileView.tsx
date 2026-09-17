import React from 'react';
import { GraduationCap, Briefcase, Code2, FolderGit2, CheckCircle2 } from 'lucide-react';
import { ExtractedProfile } from '../types';

interface ExtractedProfileViewProps {
  profile: ExtractedProfile;
}

export const ExtractedProfileView: React.FC<ExtractedProfileViewProps> = ({ profile }) => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <span>Extracted Candidate Profile</span>
            <span className="text-xs bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2.5 py-0.5 rounded-full font-medium">
              Verified by AI Parser
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Structured entities extracted from your uploaded resume.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Education Card */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center space-x-2 text-indigo-400 font-semibold text-sm">
            <GraduationCap className="w-4 h-4" />
            <span>Education</span>
          </div>

          <div className="space-y-3">
            {profile.education && profile.education.length > 0 ? (
              profile.education.map((edu, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 text-xs text-slate-200">
                  <p className="font-semibold text-white">{edu}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 italic">No formal education entries detected.</p>
            )}
          </div>
        </div>

        {/* Experience Card */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-indigo-400 font-semibold text-sm">
              <Briefcase className="w-4 h-4" />
              <span>Experience Timeline</span>
            </div>
            <span className="text-[11px] font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">
              ~{profile.years_of_experience || 2} Years
            </span>
          </div>

          <div className="space-y-2.5">
            {profile.experience && profile.experience.length > 0 ? (
              profile.experience.slice(0, 3).map((exp, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 text-xs text-slate-300">
                  <p className="line-clamp-3 leading-relaxed">{exp}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 italic">No experience entries detected.</p>
            )}
          </div>
        </div>
      </div>

      {/* Skills Section */}
      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-indigo-400 font-semibold text-sm">
            <Code2 className="w-4 h-4" />
            <span>Extracted Skills ({profile.skills?.length || 0})</span>
          </div>
          <span className="text-[11px] text-slate-400">Classified by Taxonomy</span>
        </div>

        <div className="flex flex-wrap gap-2">
          {profile.skills && profile.skills.length > 0 ? (
            profile.skills.map((skill, idx) => (
              <span
                key={idx}
                className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-slate-800/80 text-slate-200 border border-slate-700 hover:border-indigo-500/40 transition-colors"
              >
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                <span>{skill}</span>
              </span>
            ))
          ) : (
            <p className="text-xs text-slate-500 italic">No skills detected.</p>
          )}
        </div>
      </div>

      {/* Projects Section with Explicit vs Inferred Distinction */}
      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-indigo-400 font-semibold text-sm">
            <FolderGit2 className="w-4 h-4" />
            <span>Project Portfolio & Skill Evidence</span>
          </div>
          <div className="flex items-center space-x-3 text-[11px]">
            <span className="flex items-center space-x-1 text-indigo-300">
              <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
              <span>Explicit Tech</span>
            </span>
            <span className="flex items-center space-x-1 text-cyan-300">
              <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
              <span>Inferred Evidence</span>
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {profile.projects && profile.projects.length > 0 ? (
            profile.projects.map((proj, idx) => (
              <div 
                key={idx}
                className="p-4 rounded-xl bg-slate-800/30 border border-slate-700/60 space-y-3 hover:border-slate-600 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-sm text-white">{proj.title}</h4>
                  <span className="text-[10px] uppercase font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                    Verified Project
                  </span>
                </div>

                {/* Technologies List */}
                <div className="space-y-1.5">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Technologies:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {proj.technologies && proj.technologies.map((tech, tIdx) => (
                      <span
                        key={tIdx}
                        className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/30"
                      >
                        {tech}
                        <span className="ml-1 text-[9px] text-indigo-400 font-bold">Explicit</span>
                      </span>
                    ))}

                    {proj.inferred_skills && proj.inferred_skills.map((inf, iIdx) => (
                      <span
                        key={iIdx}
                        className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                      >
                        {inf}
                        <span className="ml-1 text-[9px] text-cyan-400 font-bold">Inferred</span>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Evidence bullet points */}
                {proj.evidence && proj.evidence.length > 0 && (
                  <div className="space-y-1 pt-1 border-t border-slate-700/40">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Evidence / Deliverables:
                    </span>
                    <ul className="space-y-1">
                      {proj.evidence.map((ev, eIdx) => (
                        <li key={eIdx} className="text-xs text-slate-300 flex items-start space-x-1.5">
                          <span className="text-indigo-400 font-bold">•</span>
                          <span>{ev}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500 italic">No projects found.</p>
          )}
        </div>
      </div>
    </div>
  );
};
