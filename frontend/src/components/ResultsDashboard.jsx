// === FILE: src/components/ResultsDashboard.jsx ===
// GymSense AI — Results dashboard container

import React from 'react';
import SummaryCards from './SummaryCards';
import TimelineChart from './TimelineChart';
import ExerciseCard from './ExerciseCard';
import CoachingPanel from './CoachingPanel';
import DownloadButton from './DownloadButton';

export default function ResultsDashboard({ data, onBack }) {
  const { session_summary, timeline, exercises, coaching, session_id } = data;

  return (
    <div className="animate-fade-in-up">
      {/* Page header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <button
            onClick={onBack}
            className="text-gray-500 hover:text-orange-400 text-sm mb-2 flex items-center gap-1 transition-colors"
          >
            ← Back to Upload
          </button>
          <h2 className="text-3xl font-bold text-white">
            Session <span className="text-orange-400">Results</span>
          </h2>
          <p className="text-gray-500 text-sm mt-1">
            Session ID: {session_id?.slice(0, 8)}...
          </p>
        </div>
        <DownloadButton sessionId={session_id} />
      </div>

      {/* Summary Cards */}
      <SummaryCards summary={session_summary} />

      {/* Timeline */}
      <section className="mt-8">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="text-orange-400">📊</span> Activity Timeline
        </h3>
        <div className="glass-card p-6">
          <TimelineChart timeline={timeline} />
        </div>
      </section>

      {/* Exercises */}
      <section className="mt-8">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="text-orange-400">💪</span> Exercise Breakdown
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 stagger">
          {exercises && exercises.map((ex, i) => (
            <ExerciseCard key={`${ex.name}-${i}`} exercise={ex} />
          ))}
        </div>
      </section>

      {/* Coaching */}
      <section className="mt-8">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="text-orange-400">🤖</span> AI Coaching
        </h3>
        <CoachingPanel coaching={coaching} sessionId={session_id} />
      </section>
    </div>
  );
}
