import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { History, Calendar, Clock, Dumbbell, Target, Loader2, GitCompare, X, TrendingUp, TrendingDown, Minus, Download } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';
import { getSessions, getReport } from '../api';
import { useTheme } from '../context/ThemeContext';

const r1 = n => (isFinite(n) ? Math.round(n * 10) / 10 : 0);
function safeDate(s) { if (!s || s === 'Unknown') return null; const d = new Date(s); return isNaN(d.getTime()) ? null : d; }
function fmtDate(s) {
  const d = safeDate(s);
  return d ? d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' }) : 'Recent';
}

// Distinct palette for up to 10 lines
const COLORS = ['#6366f1','#10b981','#f59e0b','#ef4444','#06b6d4','#8b5cf6','#f97316','#14b8a6','#ec4899','#64748b'];

const METRICS = [
  { key: 'avg_tempo_score',   label: 'Tempo Score',  unit: '/100', better: 1 },
  { key: 'total_reps',        label: 'Reps',         unit: '',     better: 1 },
  { key: 'total_duration_min',label: 'Duration',     unit: ' min', better: 1 },
  { key: 'total_exercises',   label: 'Exercises',    unit: '',     better: 1 },
];

function SessionCard({ s, selected, onToggle, compareMode }) {
  const [dl, setDl] = useState(false);
  const t = Number(s.avg_tempo_score) || 0;
  const tc = t >= 80 ? 'text-emerald-600 dark:text-emerald-400'
           : t >= 60 ? 'text-amber-500 dark:text-amber-400'
           : 'text-rose-500 dark:text-rose-400';

  const handleDl = async (e) => {
    e.stopPropagation();
    setDl(true);
    try {
      const blob = await getReport(s.session_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url;
      a.download = `GymSense_${s.session_id.slice(0,8)}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Report not available'); }
    finally { setDl(false); }
  };

  return (
    <div
      onClick={() => compareMode && onToggle(s)}
      className={`card p-4 transition-all duration-200 ${compareMode ? 'cursor-pointer' : ''} ${
        selected ? 'ring-2 ring-primary-500 bg-primary-50/30 dark:bg-primary-900/10' : compareMode ? 'hover:ring-1 hover:ring-primary-300' : ''
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-sm font-semibold text-slate-800 dark:text-white flex items-center gap-1.5">
            <Calendar size={13} className="text-primary-400" /> {fmtDate(s.session_date)}
          </div>
          <div className="text-xs text-slate-400 dark:text-zinc-600 mt-0.5 font-mono">{(s.session_id||'').slice(0,8)}</div>
        </div>
        <div className="flex items-center gap-2">
          {selected && <span className="text-xs bg-primary-600 text-white px-2 py-0.5 rounded-lg font-semibold">Selected</span>}
          <button onClick={handleDl} disabled={dl} className="text-slate-400 hover:text-primary-500 transition-colors disabled:opacity-50" title="Download PDF">
            {dl ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
          </button>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 mb-3">
        {[
          { icon: Clock,    val: `${Math.round(s.total_duration_min||0)}m`, label: 'Duration' },
          { icon: Dumbbell, val: s.total_exercises||0, label: 'Exercises' },
          { icon: Target,   val: s.total_reps||0, label: 'Reps' },
        ].map(({ icon: Icon, val, label }) => (
          <div key={label} className="bg-slate-50 dark:bg-zinc-800/60 rounded-lg p-2 text-center">
            <div className="text-xs font-bold text-slate-700 dark:text-zinc-300">{val}</div>
            <div className="text-[10px] text-slate-400 dark:text-zinc-600 mt-0.5">{label}</div>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400 dark:text-zinc-600">Tempo Score</span>
        <span className={`text-sm font-bold ${tc}`}>{Math.round(t)}/100</span>
      </div>
      <div className="h-1.5 bg-slate-100 dark:bg-zinc-800 rounded-full mt-1.5 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${t >= 80 ? 'bg-emerald-500' : t >= 60 ? 'bg-amber-400' : 'bg-rose-500'}`}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, t)}%` }}
          transition={{ duration: 0.8 }}
        />
      </div>
    </div>
  );
}

function ComparisonView({ selected, onClose, dark }) {
  const axis  = { fill: dark ? '#a1a1aa' : '#64748b', fontSize: 11 };
  const grid  = dark ? '#3f3f46' : '#e2e8f0';

  // Build chart data: one entry per metric, multiple values per session
  const metricData = METRICS.map(m => {
    const entry = { metric: m.label };
    selected.forEach((s, i) => { entry[`s${i}`] = r1(Number(s[m.key]) || 0); });
    return entry;
  });

  // Determine winner for each metric
  const deltas = METRICS.map(m => {
    const vals = selected.map(s => Number(s[m.key]) || 0);
    const best = m.better === 1 ? Math.max(...vals) : Math.min(...vals);
    return { ...m, vals, best };
  });

  const improvedCount = (i) => deltas.filter(d => d.vals[i] === d.best).length;

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 16 }}
      className="card p-6 mt-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <GitCompare size={16} className="text-primary-500" /> Comparison — {selected.length} Sessions
          </h2>
          <p className="text-xs text-slate-500 dark:text-zinc-500 mt-0.5">Side-by-side metric comparison across all selected sessions.</p>
        </div>
        <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-400 transition-colors">
          <X size={16} />
        </button>
      </div>

      {/* Color legend */}
      <div className="flex flex-wrap gap-3 mb-5">
        {selected.map((s, i) => (
          <div key={s.session_id} className="flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-zinc-300">
            <div className="w-3 h-3 rounded-sm" style={{ background: COLORS[i % COLORS.length] }} />
            Session {i + 1}: {fmtDate(s.session_date)}
          </div>
        ))}
      </div>

      {/* Metric table */}
      <div className="overflow-x-auto mb-6">
        <table className="w-full text-sm min-w-[500px]">
          <thead>
            <tr className="text-xs text-slate-500 dark:text-zinc-600 uppercase tracking-wider border-b border-slate-100 dark:border-zinc-800">
              <th className="text-left pb-2 font-semibold">Metric</th>
              {selected.map((s, i) => (
                <th key={i} className="text-right pb-2 font-semibold" style={{ color: COLORS[i % COLORS.length] }}>
                  S{i+1} · {fmtDate(s.session_date)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {deltas.map(d => (
              <tr key={d.key} className="border-b border-slate-50 dark:border-zinc-800/50">
                <td className="py-2.5 text-slate-600 dark:text-zinc-400 font-medium">{d.label}</td>
                {d.vals.map((v, i) => {
                  const isBest = v === d.best;
                  return (
                    <td key={i} className={`py-2.5 text-right font-semibold ${isBest ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-700 dark:text-zinc-300'}`}>
                      {r1(v)}{d.unit}
                      {isBest && selected.length > 1 && <span className="ml-1 text-[10px] bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 px-1 rounded">best</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Session scores */}
      {selected.length > 1 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {selected.map((s, i) => (
            <div key={s.session_id} className="rounded-xl p-3 border border-slate-100 dark:border-zinc-800 text-center" style={{ borderLeftColor: COLORS[i % COLORS.length], borderLeftWidth: 3 }}>
              <div className="text-xs font-semibold text-slate-500 dark:text-zinc-500 mb-1">Session {i+1}</div>
              <div className="text-base font-bold text-slate-900 dark:text-white">{improvedCount(i)}/{METRICS.length}</div>
              <div className="text-xs text-slate-400 dark:text-zinc-600">metrics best</div>
            </div>
          ))}
        </div>
      )}

      {/* Multi-line chart */}
      <div className="text-xs font-semibold text-slate-500 dark:text-zinc-500 uppercase tracking-wider mb-3">Tempo Score Over Time</div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid stroke={grid} strokeDasharray="3 3" />
          <XAxis dataKey="date" type="category" tick={axis} />
          <YAxis domain={[0, 100]} tick={axis} />
          <Tooltip contentStyle={{ background: dark ? '#27272a' : '#fff', border: `1px solid ${grid}`, borderRadius: 12, fontSize: 12 }} />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
          {selected.map((s, i) => (
            <Line
              key={s.session_id}
              data={[{ date: fmtDate(s.session_date), tempo: r1(Number(s.avg_tempo_score)||0) }]}
              type="monotone" dataKey="tempo"
              name={`S${i+1} ${fmtDate(s.session_date)}`}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2} dot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </motion.div>
  );
}

export default function HistoryPage() {
  const [sessions,     setSessions]     = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [compareMode,  setCompareMode]  = useState(false);
  const [selected,     setSelected]     = useState([]);
  const { dark } = useTheme();

  useEffect(() => {
    (async () => {
      try {
        console.log('[History] Fetching sessions...');
        const data = await getSessions();
        console.log('[History] Got', data.length);
        setSessions(data);
      } catch (e) { toast.error('Could not load history: ' + e.message); }
      finally { setLoading(false); }
    })();
  }, []);

  const toggle = (s) => {
    setSelected(prev =>
      prev.find(x => x.session_id === s.session_id)
        ? prev.filter(x => x.session_id !== s.session_id)
        : [...prev, s]
    );
  };
  const isSelected = (s) => selected.some(x => x.session_id === s.session_id);

  return (
    <div className="page-wrap">
      {/* Header */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title"><History size={22} className="text-primary-500" /> Session History</h1>
          <p className="page-sub">
            {compareMode
              ? `Select any sessions below to compare. ${selected.length} selected.`
              : `${sessions.length} session${sessions.length !== 1 ? 's' : ''} — click "Compare" to analyse differences.`}
          </p>
        </div>
        {sessions.length >= 2 && (
          <button
            onClick={() => { setCompareMode(m => !m); setSelected([]); }}
            className={compareMode ? 'btn-primary' : 'btn-outline'}
          >
            <GitCompare size={15} /> {compareMode ? 'Exit Compare' : 'Compare Sessions'}
          </button>
        )}
      </div>

      {/* Hint */}
      {compareMode && selected.length === 0 && (
        <div className="hint mb-5 text-sm">
          <strong>Compare Mode:</strong> Select any number of sessions below. A detailed metric comparison will appear automatically.
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-24 gap-3 text-slate-400 dark:text-zinc-600">
          <Loader2 className="w-6 h-6 animate-spin text-primary-500" /> Loading...
        </div>
      ) : sessions.length === 0 ? (
        <div className="card p-12 text-center">
          <History size={40} className="mx-auto text-slate-200 dark:text-zinc-700 mb-4" />
          <div className="text-base font-bold text-slate-700 dark:text-white mb-1">No Sessions Yet</div>
          <div className="text-sm text-slate-500 dark:text-zinc-500">Upload your first session CSV from the Analyse page.</div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sessions.map(s => (
              <SessionCard key={s.session_id} s={s} selected={isSelected(s)} onToggle={toggle} compareMode={compareMode} />
            ))}
          </div>

          <AnimatePresence>
            {compareMode && selected.length >= 2 && (
              <ComparisonView selected={selected} onClose={() => setSelected([])} dark={dark} />
            )}
          </AnimatePresence>

          {compareMode && selected.length === 1 && (
            <div className="mt-5 text-center text-sm text-slate-400 dark:text-zinc-600 py-4 border-2 border-dashed border-slate-200 dark:border-zinc-800 rounded-2xl">
              Select at least one more session to see the comparison.
            </div>
          )}
        </>
      )}
    </div>
  );
}
