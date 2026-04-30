import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp, Activity, Clock, Zap, Target, Loader2, Info } from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts';
import { getSessions } from '../api';
import { useTheme } from '../context/ThemeContext';

const r1 = n => (isFinite(n) ? Math.round(n * 10) / 10 : 0);

function safeDate(s) {
  if (!s || s === 'Unknown') return null;
  const d = new Date(s); return isNaN(d.getTime()) ? null : d;
}
function fmtDate(s) {
  const d = safeDate(s);
  return d ? d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : 'N/A';
}

function ChartCard({ title, hint, children }) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-4">
        <div className="text-sm font-bold text-slate-800 dark:text-white">{title}</div>
        <div className="group relative">
          <Info size={14} className="text-slate-300 dark:text-zinc-600 cursor-help" />
          <div className="absolute right-0 top-5 w-56 bg-slate-900 dark:bg-zinc-800 text-white text-xs rounded-xl p-3 shadow-xl opacity-0 group-hover:opacity-100 transition-opacity z-20 pointer-events-none">
            {hint}
          </div>
        </div>
      </div>
      {children}
    </div>
  );
}

const CustomTooltip = ({ active, payload, label, unit = '' }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900 dark:bg-zinc-800 text-white text-xs rounded-xl px-3 py-2 shadow-xl">
      <div className="font-semibold mb-1">{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>
          {p.name}: <strong>{r1(p.value)}{unit}</strong>
        </div>
      ))}
    </div>
  );
};

export default function AnalyticsPage() {
  const [sessions, setSessions] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);
  const { dark } = useTheme();

  useEffect(() => {
    (async () => {
      try {
        console.log('[Analytics] Fetching sessions...');
        const data = await getSessions();
        console.log('[Analytics] Got', data.length, 'sessions');
        const sorted = [...data].sort((a, b) => {
          const da = safeDate(a.session_date), db = safeDate(b.session_date);
          if (!da && !db) return 0; if (!da) return 1; if (!db) return -1;
          return da - db;
        });
        setSessions(sorted);
      } catch (e) { console.error('[Analytics]', e); setError(e.message); }
      finally { setLoading(false); }
    })();
  }, []);

  const axis  = { fill: dark ? '#a1a1aa' : '#64748b', fontSize: 11 };
  const grid  = dark ? '#3f3f46' : '#e2e8f0';
  const area1 = dark ? '#818cf8' : '#6366f1';
  const area2 = dark ? '#34d399' : '#10b981';

  // Recharts data
  const chartData = sessions.map(s => ({
    date:     fmtDate(s.session_date),
    tempo:    r1(Number(s.avg_tempo_score) || 0),
    reps:     Number(s.total_reps) || 0,
    duration: r1(Number(s.total_duration_min) || 0),
  }));

  // Radar data — muscle group frequency
  const muscleMap = {};
  sessions.forEach(s => (s.muscle_groups_trained || []).forEach(m => { muscleMap[m] = (muscleMap[m] || 0) + 1; }));
  const radarData = Object.entries(muscleMap).map(([subject, value]) => ({ subject, value }));

  // Summary KPIs
  const total = sessions.length;
  const avgTempo = total ? r1(sessions.reduce((a, s) => a + (Number(s.avg_tempo_score)||0), 0) / total) : 0;
  const totalReps = sessions.reduce((a, s) => a + (Number(s.total_reps)||0), 0);
  const totalTime = r1(sessions.reduce((a, s) => a + (Number(s.total_duration_min)||0), 0));
  const tempoTrend = total >= 2
    ? r1((Number(sessions[total-1].avg_tempo_score)||0) - (Number(sessions[0].avg_tempo_score)||0))
    : null;

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh] gap-3 text-slate-400 dark:text-zinc-600">
      <Loader2 className="w-6 h-6 animate-spin text-primary-500" /> Loading analytics...
    </div>
  );
  if (error) return (
    <div className="page-wrap"><div className="card p-8 text-center text-rose-600 dark:text-rose-400">{error}</div></div>
  );

  return (
    <div className="page-wrap space-y-6">
      {/* Header */}
      <div>
        <h1 className="page-title"><BarChart3 size={22} className="text-primary-500" /> Analytics</h1>
        <p className="page-sub">Track your performance trends and progression over time.</p>
      </div>

      {/* No data hint */}
      {sessions.length === 0 && (
        <div className="hint">
          <strong>No data yet.</strong> Upload at least one session from the Analyse page to see your charts here.
        </div>
      )}

      {/* KPI strip */}
      {sessions.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Sessions',    value: total,                         icon: Activity,  color: 'text-primary-500' },
            { label: 'Avg Tempo',   value: `${avgTempo}/100`,             icon: Target,    color: 'text-amber-500' },
            { label: 'Total Reps',  value: totalReps.toLocaleString(),    icon: Zap,       color: 'text-emerald-500' },
            { label: 'Active Time', value: `${totalTime} min`,            icon: Clock,     color: 'text-cyan-500' },
          ].map(({ label, value, icon: Icon, color }) => (
            <motion.div key={label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card p-4 flex items-center gap-3">
              <Icon size={20} className={color} />
              <div>
                <div className="text-lg font-bold text-slate-900 dark:text-white leading-none">{value}</div>
                <div className="text-xs text-slate-500 dark:text-zinc-500 mt-0.5">{label}</div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {sessions.length < 2 && sessions.length > 0 && (
        <div className="hint">Upload at least <strong>2 sessions</strong> to see progression charts.</div>
      )}

      {sessions.length >= 2 && (
        <>
          {/* Tempo trend badge */}
          {tempoTrend !== null && (
            <div className={`inline-flex items-center gap-2 text-sm font-semibold px-3 py-1.5 rounded-xl border ${
              tempoTrend > 0 ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400'
              : tempoTrend < 0 ? 'bg-rose-50 dark:bg-rose-900/20 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-400'
              : 'bg-slate-100 dark:bg-zinc-800 border-slate-200 dark:border-zinc-700 text-slate-600 dark:text-zinc-400'
            }`}>
              <TrendingUp size={14} />
              Tempo {tempoTrend > 0 ? `improved +${tempoTrend}` : tempoTrend < 0 ? `declined ${tempoTrend}` : 'unchanged'} pts since first session
            </div>
          )}

          {/* Tempo progression */}
          <ChartCard
            title="Tempo Score — Progression"
            hint="Tempo score (0–100) measures how consistent and controlled your rep speed is. Higher = better form."
          >
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gTempo" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={area1} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={area1} stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={grid} strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={axis} />
                <YAxis domain={[0, 100]} tick={axis} />
                <Tooltip content={<CustomTooltip unit="/100" />} />
                <Area type="monotone" dataKey="tempo" name="Tempo" stroke={area1} fill="url(#gTempo)" strokeWidth={2} dot={{ r: 4, fill: area1 }} />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Reps + Duration */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ChartCard
              title="Reps per Session"
              hint="Total repetitions performed in each session. Increasing reps over time indicates volume progression."
            >
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke={grid} strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={axis} />
                  <YAxis tick={axis} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="reps" name="Reps" fill={area1} radius={[6,6,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              title="Session Duration (min)"
              hint="How long each session lasted. Longer sessions with stable tempo indicate improved endurance."
            >
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke={grid} strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={axis} />
                  <YAxis tick={axis} />
                  <Tooltip content={<CustomTooltip unit=" min" />} />
                  <Bar dataKey="duration" name="Duration" fill={area2} radius={[6,6,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          {/* Muscle radar */}
          {radarData.length > 2 && (
            <ChartCard
              title="Muscle Group Balance"
              hint="Shows which muscle groups you train most often. A balanced radar indicates well-rounded training."
            >
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke={grid} />
                  <PolarAngleAxis dataKey="subject" tick={{ ...axis, fontSize: 10 }} />
                  <Radar name="Sessions" dataKey="value" stroke={area1} fill={area1} fillOpacity={0.25} />
                  <Tooltip content={<CustomTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
            </ChartCard>
          )}
        </>
      )}

      {/* Session table */}
      {sessions.length > 0 && (
        <div className="card p-5">
          <div className="text-sm font-bold text-slate-800 dark:text-white mb-4">All Sessions</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-500 dark:text-zinc-600 uppercase tracking-wider border-b border-slate-100 dark:border-zinc-800">
                  <th className="text-left pb-2 font-semibold">Date</th>
                  <th className="text-right pb-2 font-semibold">Tempo</th>
                  <th className="text-right pb-2 font-semibold">Reps</th>
                  <th className="text-right pb-2 font-semibold">Duration</th>
                  <th className="text-right pb-2 font-semibold">Exercises</th>
                </tr>
              </thead>
              <tbody>
                {[...sessions].reverse().map((s, i) => {
                  const t = Number(s.avg_tempo_score) || 0;
                  const tc = t >= 80 ? 'text-emerald-600 dark:text-emerald-400'
                           : t >= 60 ? 'text-amber-600 dark:text-amber-400' : 'text-rose-500 dark:text-rose-400';
                  return (
                    <tr key={s.session_id || i} className="border-b border-slate-50 dark:border-zinc-800/50 hover:bg-slate-50 dark:hover:bg-zinc-800/40 transition-colors">
                      <td className="py-3 text-slate-700 dark:text-zinc-300 font-medium">{fmtDate(s.session_date)}</td>
                      <td className={`py-3 text-right font-bold ${tc}`}>{Math.round(t)}/100</td>
                      <td className="py-3 text-right text-slate-600 dark:text-zinc-400">{s.total_reps || 0}</td>
                      <td className="py-3 text-right text-slate-600 dark:text-zinc-400">{Math.round(s.total_duration_min || 0)} min</td>
                      <td className="py-3 text-right text-slate-600 dark:text-zinc-400">{s.total_exercises || 0}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
