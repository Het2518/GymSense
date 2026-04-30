// === FILE: src/components/ExerciseCard.jsx ===
// GymSense AI — Per-exercise card with SVG tempo gauge

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp } from 'lucide-react';

const EXERCISE_EMOJIS = {
  Squat: '🦵',
  BenchPress: '🏋️',
  LegPress: '🦿',
  Adductor: '🦵',
  LegCurl: '🦵',
  ArmCurl: '💪',
  RopeSkipping: '⏭️',
  Running: '🏃',
  Walking: '🚶',
  StairClimber: '🪜',
  Riding: '🚴',
};

const MUSCLE_GROUPS = {
  Squat: ['Quads', 'Glutes', 'Hamstrings'],
  BenchPress: ['Chest', 'Triceps', 'Shoulders'],
  LegPress: ['Quads', 'Glutes'],
  Adductor: ['Adductors'],
  LegCurl: ['Hamstrings'],
  ArmCurl: ['Biceps'],
  RopeSkipping: ['Calves', 'Cardio'],
  Running: ['Cardio', 'Calves'],
  Walking: ['Cardio'],
  StairClimber: ['Quads', 'Glutes', 'Cardio'],
  Riding: ['Cardio', 'Quads'],
};

function TempoGauge({ score, size = 80 }) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 6;
  const circumference = Math.PI * r;
  const filled = (score / 100) * circumference;
  const color = score >= 75 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <svg width={size} height={size / 2 + 14} viewBox={`0 0 ${size} ${size / 2 + 14}`}>
      <path
        d={`M ${cx - r},${cy} A ${r},${r} 0 0,1 ${cx + r},${cy}`}
        fill="none" stroke="#e2e8f0" strokeWidth="7" strokeLinecap="round"
      />
      <path
        d={`M ${cx - r},${cy} A ${r},${r} 0 0,1 ${cx + r},${cy}`}
        fill="none" stroke={color} strokeWidth="7" strokeLinecap="round"
        strokeDasharray={`${filled} ${circumference}`}
        style={{ transition: 'stroke-dasharray 1s ease-out' }}
      />
      <text x={cx} y={cy - 4} textAnchor="middle" fontSize="16" fontWeight="bold" fill={color}>
        {score}
      </text>
      <text x={cx} y={cy + 10} textAnchor="middle" fontSize="8" fill="#64748b" fontWeight="600">
        TEMPO
      </text>
    </svg>
  );
}

export default function ExerciseCard({ exercise }) {
  const [expanded, setExpanded] = useState(false);
  const ex = exercise;
  const emoji = EXERCISE_EMOJIS[ex.name] || '🏋️';
  const muscles = MUSCLE_GROUPS[ex.name] || [];

  return (
    <div className="glass-card-light p-5 hover:bg-slate-50 transition-all duration-300 group border-slate-200 shadow-sm hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {/* Header */}
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">{emoji}</span>
            <div>
              <h4 className="text-slate-800 font-bold text-lg">{ex.name}</h4>
              <p className="text-slate-500 text-xs font-medium">{ex.start_time} – {ex.end_time}</p>
            </div>
          </div>

          {/* Metrics Row */}
          <div className="flex flex-wrap gap-2 mb-3">
            <div className="badge-success bg-rose-50 text-rose-700 border-rose-200">{ex.total_reps} reps</div>
            <div className="badge-success bg-rose-50 text-rose-700 border-rose-200">{ex.sets} sets</div>
            <div className="badge-success bg-orange-50 text-orange-700 border-orange-200">{ex.completion_pct}% complete</div>
            {ex.fatigue_detected && (
              <div className="badge-danger">
                ⚡ Fatigue at rep {ex.fatigue_onset_rep || '?'}
              </div>
            )}
            {ex.rest_flags && ex.rest_flags.some(f => f !== 'ok' && f !== 'n/a') && (
              <div className="badge-warning">Rest issue</div>
            )}
          </div>

          {/* Muscle groups */}
          <div className="flex flex-wrap gap-1.5">
            {muscles.map((m) => (
              <span key={m} className="text-[10px] font-medium bg-slate-100 text-slate-500 px-2 py-0.5 rounded-md border border-slate-200">
                {m}
              </span>
            ))}
          </div>
        </div>

        {/* Tempo Gauge */}
        <div className="flex-shrink-0 ml-4">
          <TempoGauge score={ex.tempo_score || 0} />
        </div>
      </div>

      {/* Expandable details */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-orange-600 mt-4 transition-colors"
      >
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        {expanded ? 'Hide details' : 'Show reps per set'}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-4 pt-4 border-t border-slate-200">
              <div className="grid grid-cols-3 gap-3 text-sm">
                {ex.reps_per_set && ex.reps_per_set.map((reps, i) => (
                  <div key={i} className="bg-slate-50 border border-slate-100 rounded-lg p-2 text-center shadow-sm">
                    <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-0.5">Set {i + 1}</div>
                    <div className="text-slate-700 font-bold">{reps} reps</div>
                  </div>
                ))}
              </div>
              {ex.rest_times_sec && ex.rest_times_sec.length > 0 && (
                <div className="mt-3 text-xs font-medium text-slate-500 bg-slate-50 p-2 rounded-lg border border-slate-100">
                  Rest between sets: <span className="text-slate-700">{ex.rest_times_sec.map(r => `${r}s`).join(', ')}</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
