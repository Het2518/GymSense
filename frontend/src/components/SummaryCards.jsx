import React from 'react';
import { Timer, Dumbbell, Repeat, Target } from 'lucide-react';

function getTempoColor(score) {
  if (score >= 75) return { bg: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-700', icon: 'text-rose-500' };
  if (score >= 50) return { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', icon: 'text-amber-500' };
  return { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', icon: 'text-red-500' };
}

function formatDuration(minutes) {
  const m = Math.floor(minutes);
  const s = Math.round((minutes - m) * 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

const CARDS = [
  {
    key: 'duration',
    label: 'Total Duration',
    icon: Timer,
    getValue: (s) => formatDuration(s.total_duration_min || 0),
    getColor: () => ({ bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', icon: 'text-amber-500' }),
  },
  {
    key: 'exercises',
    label: 'Exercises',
    icon: Dumbbell,
    getValue: (s) => s.total_exercises || 0,
    getColor: () => ({ bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', icon: 'text-purple-500' }),
  },
  {
    key: 'reps',
    label: 'Total Reps',
    icon: Repeat,
    getValue: (s) => s.total_reps || 0,
    getColor: () => ({ bg: 'bg-indigo-50', border: 'border-indigo-200', text: 'text-indigo-700', icon: 'text-indigo-500' }),
  },
  {
    key: 'tempo',
    label: 'Avg Tempo Score',
    icon: Target,
    getValue: (s) => Math.round(s.avg_tempo_score || 0),
    getColor: (s) => getTempoColor(s.avg_tempo_score || 0),
  },
];

export default function SummaryCards({ summary }) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {CARDS.map((card) => {
        const color = card.getColor(summary);
        const Icon = card.icon;
        return (
          <div
            key={card.key}
            className={`glass-card-light p-5 ${color.bg} border ${color.border} transition-all duration-300 hover:-translate-y-1 hover:shadow-md`}
          >
            <div className="flex items-center gap-2 mb-3">
              <Icon className={`w-5 h-5 ${color.icon}`} />
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">
                {card.label}
              </span>
            </div>
            <div className={`text-3xl font-bold ${color.text}`}>
              {card.getValue(summary)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
