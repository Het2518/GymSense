import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { LayoutDashboard, Upload, History, BarChart3, Flag, TrendingUp, Clock, Dumbbell, Zap, ChevronRight, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getDashboardStats, getSessions, checkHealth } from '../api';

const r1 = n => (isFinite(n) ? Math.round(n * 10) / 10 : 0);

function KPI({ label, value, sub, icon: Icon, color }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-4 ${color}`}>
        <Icon size={18} className="text-white" />
      </div>
      <div className="text-2xl font-bold text-slate-900 dark:text-white leading-none">{value ?? '—'}</div>
      <div className="text-sm font-semibold text-slate-600 dark:text-zinc-400 mt-1">{label}</div>
      {sub && <div className="text-xs text-slate-400 dark:text-zinc-600 mt-0.5">{sub}</div>}
    </motion.div>
  );
}

function QuickLink({ to, icon: Icon, label, desc }) {
  return (
    <Link to={to} className="card-hover p-4 flex items-start gap-3 group">
      <div className="w-9 h-9 rounded-lg bg-primary-100 dark:bg-primary-900/40 flex items-center justify-center flex-shrink-0">
        <Icon size={16} className="text-primary-600 dark:text-primary-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-slate-800 dark:text-white">{label}</div>
        <div className="text-xs text-slate-500 dark:text-zinc-500 mt-0.5">{desc}</div>
      </div>
      <ChevronRight size={14} className="text-slate-300 dark:text-zinc-700 group-hover:text-primary-500 transition-colors mt-0.5 flex-shrink-0" />
    </Link>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats,    setStats]    = useState(null);
  const [sessions, setSessions] = useState([]);
  const [health,   setHealth]   = useState(null);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    console.log('[Dashboard] Loading...');
    Promise.all([
      getDashboardStats().catch(() => null),
      getSessions().catch(() => []),
      checkHealth().catch(() => null),
    ]).then(([s, sess, h]) => {
      console.log('[Dashboard] stats:', s, 'sessions:', sess?.length, 'health:', h?.model_loaded);
      setStats(s); setSessions(sess || []); setHealth(h); setLoading(false);
    });
  }, []);

  const avgTempo = sessions.length
    ? r1(sessions.reduce((a, s) => a + (Number(s.avg_tempo_score) || 0), 0) / sessions.length)
    : 0;
  const isNew = !loading && sessions.length === 0;
  const hour  = new Date().getHours();
  const greet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <div className="page-wrap">
      {/* Header */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title"><LayoutDashboard size={22} className="text-primary-500" /> {greet}, {user?.name?.split(' ')[0] || 'Athlete'}</h1>
          <p className="page-sub">
            {isNew
              ? 'Welcome! Upload your first session to get started.'
              : `${sessions.length} session${sessions.length !== 1 ? 's' : ''} analysed · AI model ${health?.model_loaded ? 'ready' : 'loading'}`}
          </p>
        </div>
        <Link to="/upload" className="btn-primary">
          <Upload size={16} /> Analyse Session
        </Link>
      </div>

      {/* Onboarding for new users */}
      {isNew && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="hint mb-8">
          <div className="font-semibold mb-2 flex items-center gap-2 text-primary-700 dark:text-primary-300">
            <AlertCircle size={16} /> How to use GymSense AI
          </div>
          <ol className="space-y-1 text-sm text-slate-700 dark:text-zinc-300 list-decimal list-inside">
            <li>Go to <strong>Profile</strong> and fill in your age, weight, goal and experience level.</li>
            <li>Go to <strong>Analyse</strong> and upload a CSV file from your wearable sensor.</li>
            <li>Receive an AI coaching report — then track progress in <strong>History</strong> and <strong>Analytics</strong>.</li>
          </ol>
        </motion.div>
      )}

      {/* KPIs */}
      {!loading && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <KPI icon={Dumbbell} label="Sessions"     value={stats?.total_workouts || 0}                   color="bg-primary-500"   sub="total analysed" />
          <KPI icon={Clock}    label="Active Time"  value={`${r1(stats?.total_duration_min || 0)} min`}  color="bg-cyan-500"      sub="all sessions" />
          <KPI icon={Zap}      label="Total Reps"   value={(stats?.total_reps || 0).toLocaleString()}     color="bg-emerald-500"   sub="all exercises" />
          <KPI icon={TrendingUp} label="Avg Tempo"  value={avgTempo || '—'}                              color="bg-violet-500"    sub="quality score / 100" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent sessions */}
        <div className="lg:col-span-2 card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-bold text-slate-800 dark:text-white">Recent Sessions</div>
            {sessions.length > 0 && (
              <Link to="/history" className="text-xs text-primary-500 hover:underline font-semibold">View all</Link>
            )}
          </div>

          {sessions.length === 0 && !loading ? (
            <div className="py-10 text-center text-slate-400 dark:text-zinc-600 text-sm">
              No sessions yet. <Link to="/upload" className="text-primary-500 hover:underline">Upload one now</Link>.
            </div>
          ) : (
            <div className="space-y-2">
              {sessions.slice(0, 5).map((s, i) => {
                const date = s.session_date && s.session_date !== 'Unknown'
                  ? new Date(s.session_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })
                  : 'Recent';
                const t = Number(s.avg_tempo_score) || 0;
                const tc = t >= 80 ? 'text-emerald-600 dark:text-emerald-400'
                         : t >= 60 ? 'text-amber-600 dark:text-amber-400'
                         : 'text-rose-600 dark:text-rose-400';
                return (
                  <div key={s.session_id || i} className="flex items-center justify-between py-2.5 px-3 rounded-xl hover:bg-slate-50 dark:hover:bg-zinc-800/60 transition-colors">
                    <div>
                      <div className="text-sm font-semibold text-slate-800 dark:text-white">{date}</div>
                      <div className="text-xs text-slate-400 dark:text-zinc-600">{s.total_exercises || 0} exercises · {s.total_reps || 0} reps · {Math.round(s.total_duration_min || 0)} min</div>
                    </div>
                    <div className={`text-base font-bold ${tc}`}>
                      {Math.round(t)}<span className="text-xs font-normal text-slate-400 dark:text-zinc-600">/100</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Quick links */}
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-zinc-600 mb-3 px-1">Quick Navigation</div>
          <QuickLink to="/upload"    icon={Upload}    label="Analyse a Session"    desc="Upload wearable CSV for AI analysis" />
          <QuickLink to="/history"   icon={History}   label="Session History"      desc="Compare and review past sessions" />
          <QuickLink to="/analytics" icon={BarChart3} label="Deep Analytics"       desc="Charts and performance trends" />
          <QuickLink to="/goals"     icon={Flag}      label="Fitness Goals"         desc="Set and track training targets" />
          <QuickLink to="/profile"   icon={Dumbbell}  label="Athlete Profile"       desc="Update body stats and preferences" />
        </div>
      </div>

      {/* Muscle distribution */}
      {stats?.total_workouts > 0 && Object.keys(stats?.muscle_distribution || {}).length > 0 && (
        <div className="card p-5 mt-6">
          <div className="text-sm font-bold text-slate-800 dark:text-white mb-4">Muscle Group Focus</div>
          <div className="space-y-2">
            {Object.entries(stats.muscle_distribution)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 8)
              .map(([m, c]) => {
                const max = Math.max(...Object.values(stats.muscle_distribution));
                return (
                  <div key={m} className="flex items-center gap-3">
                    <div className="w-24 text-xs font-medium text-slate-600 dark:text-zinc-400 capitalize truncate">{m}</div>
                    <div className="flex-1 h-2 bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-primary-500 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${(c / max) * 100}%` }}
                        transition={{ duration: 0.8 }}
                      />
                    </div>
                    <div className="text-xs text-slate-400 dark:text-zinc-600 w-6 text-right">{c}×</div>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
