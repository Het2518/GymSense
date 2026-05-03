import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useLocation } from 'react-router-dom';
import { ChevronLeft, Download, Activity, Target, BrainCircuit, Dumbbell, Info } from 'lucide-react';
import SummaryCards from '../components/SummaryCards';
import TimelineChart from '../components/TimelineChart';
import ExerciseCard from '../components/ExerciseCard';
import CoachingPanel from '../components/CoachingPanel';
import DownloadButton from '../components/DownloadButton';

export default function ResultsPage({ data }) {
  const navigate = useNavigate();
  const location = useLocation();
  const pageData = location.state?.resultData || data;

  useEffect(() => {
    if (!pageData) {
      navigate('/');
    }
  }, [pageData, navigate]);

  if (!pageData) return null;

  const { session_summary, timeline, exercises, coaching, session_id } = pageData;

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } }
  };

  return (
    <motion.div 
      initial="hidden" 
      animate="show" 
      variants={containerVariants}
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
    >
      {/* Page header */}
      <motion.div variants={itemVariants} className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
        <div>
          <button
            onClick={() => navigate('/')}
            className="text-slate-500 hover:text-orange-600 font-medium text-sm mb-2 flex items-center gap-1 transition-colors"
          >
            <ChevronLeft size={16} /> Back to Upload
          </button>
          <h2 className="text-3xl font-bold text-slate-800 tracking-tight">
            Session <span className="text-orange-600">Results</span>
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            Session ID: <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">{session_id?.slice(0, 8)}...</span>
          </p>
        </div>
        <DownloadButton sessionId={session_id} />
      </motion.div>

      {/* Summary Cards */}
      <motion.div variants={itemVariants}>
        <SummaryCards summary={session_summary} />
      </motion.div>

      {/* Timeline */}
      <motion.section variants={itemVariants} className="mt-10">
        <h3 className="text-xl font-bold text-slate-800 mb-5 flex items-center gap-2">
          <Activity className="text-orange-500" /> Activity Timeline
        </h3>
        <div className="glass-card p-2 sm:p-6">
          <TimelineChart timeline={timeline} />
        </div>
      </motion.section>

      {/* Exercises */}
      <motion.section variants={itemVariants} className="mt-10">
        <h3 className="text-xl font-bold text-slate-800 mb-5 flex items-center gap-2">
          <Dumbbell className="text-orange-500" /> Exercise Breakdown
        </h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {exercises && exercises.map((ex, i) => (
            <motion.div key={`${ex.name}-${i}`} variants={itemVariants}>
              <ExerciseCard exercise={ex} />
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* Tempo Formula Info Panel */}
      <motion.section variants={itemVariants} className="mt-8">
        <div className="bg-amber-50 border border-amber-100 rounded-xl p-5 flex gap-4 items-start">
          <Info className="text-amber-500 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-amber-900">How is the Tempo Score calculated?</h4>
            <p className="text-amber-800/80 text-sm mt-1 leading-relaxed">
              The <strong>Tempo Score (0-100)</strong> evaluates the consistency of your repetition speed. We measure the duration of each individual rep using sensor peaks. 
              The score is computed using the inverse coefficient of variation: <code>Score = max(0, 100 - (StdDev / Mean) * 100)</code>. 
              A score above 85 indicates highly controlled and consistent pacing!
            </p>
          </div>
        </div>
      </motion.section>

      {/* Coaching */}
      <motion.section variants={itemVariants} className="mt-10 mb-12">
        <h3 className="text-xl font-bold text-slate-800 mb-5 flex items-center gap-2">
          <BrainCircuit className="text-orange-500" /> AI Coaching Insights
        </h3>
        <CoachingPanel coaching={coaching} sessionId={session_id} />
      </motion.section>
    </motion.div>
  );
}
