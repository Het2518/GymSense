// === FILE: src/components/CoachingPanel.jsx ===
// GymSense AI — LLM coaching display with re-generation

import React, { useState } from 'react';
import { CheckCircle2, TrendingUp, ArrowRightCircle } from 'lucide-react';

const SECTIONS = [
  { key: 'strengths', icon: CheckCircle2, title: 'Strengths', color: 'text-rose-700', bgColor: 'bg-rose-50', borderColor: 'border-rose-200' },
  { key: 'improvements', icon: TrendingUp, title: 'Improvements', color: 'text-amber-700', bgColor: 'bg-amber-50', borderColor: 'border-amber-200' },
  { key: 'next_session', icon: ArrowRightCircle, title: 'Next Session', color: 'text-amber-700', bgColor: 'bg-amber-50', borderColor: 'border-amber-200' },
];

export default function CoachingPanel({ coaching, sessionId }) {
  const [coachingData, setCoachingData] = useState(coaching || {});

  if (!coachingData || (!coachingData.strengths && !coachingData.improvements && !coachingData.next_session)) {
    return (
      <div className="glass-card p-6 text-center text-slate-500 border-slate-200">
        <p>No coaching data available. Set GEMINI_API_KEY to enable AI coaching.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {SECTIONS.map((section) => {
        const content = coachingData[section.key];
        if (!content) return null;
        
        const Icon = section.icon;

        return (
          <div
            key={section.key}
            className={`glass-card-light p-5 sm:p-6 border-l-4 ${section.borderColor} ${section.bgColor} shadow-sm hover:shadow-md transition-shadow`}
          >
            <div className="flex items-center gap-3 mb-3">
              <Icon className={`w-6 h-6 ${section.color}`} />
              <h4 className={`font-bold text-lg ${section.color}`}>{section.title}</h4>
            </div>
            <p className="text-slate-700 text-sm sm:text-base leading-relaxed whitespace-pre-wrap">
              {content}
            </p>
          </div>
        );
      })}
    </div>
  );
}
