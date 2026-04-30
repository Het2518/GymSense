import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Flag, Plus, Circle, CheckCircle, Trash2, Edit3, X, Loader2, Target, Calendar, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { getGoals, saveGoal, updateGoal, deleteGoal } from '../api';

const TYPES = ['Strength','Endurance','Weight','Frequency','Technique','Custom'];
const PRIORITIES = [
  { value: 'high',   label: 'High',   cls: 'badge-red' },
  { value: 'medium', label: 'Medium', cls: 'badge badge-indigo' },
  { value: 'low',    label: 'Low',    cls: 'badge-green' },
];

function daysLeft(deadline) {
  if (!deadline) return null;
  return Math.ceil((new Date(deadline) - new Date()) / 86400000);
}

function GoalModal({ init, onSave, onClose }) {
  const [f, setF] = useState({ title:'', type:'Strength', priority:'medium', target_value:'', target_unit:'', deadline:'', description:'', ...init });
  const ch = e => setF(p => ({ ...p, [e.target.name]: e.target.value }));
  const submit = () => { if (!f.title.trim()) { toast.error('Enter a goal title'); return; } onSave(f); };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div initial={{ scale: 0.95, y: 16 }} animate={{ scale: 1, y: 0 }}
        className="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl w-full max-w-md p-6 border border-slate-200 dark:border-zinc-800">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-base font-bold text-slate-900 dark:text-white">{init?._id ? 'Edit Goal' : 'New Goal'}</h3>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-400 transition-colors"><X size={16} /></button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="label">Goal Title</label>
            <input name="title" value={f.title} onChange={ch} className="input-field" placeholder="e.g. Bench press 100 kg" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Category</label>
              <select name="type" value={f.type} onChange={ch} className="input-field bg-white dark:bg-zinc-900">
                {TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Priority</label>
              <select name="priority" value={f.priority} onChange={ch} className="input-field bg-white dark:bg-zinc-900">
                {PRIORITIES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Target</label>
              <input name="target_value" value={f.target_value} onChange={ch} type="number" className="input-field" placeholder="e.g. 100" />
            </div>
            <div>
              <label className="label">Unit</label>
              <input name="target_unit" value={f.target_unit} onChange={ch} className="input-field" placeholder="kg / km / reps" />
            </div>
          </div>
          <div>
            <label className="label">Deadline</label>
            <input name="deadline" value={f.deadline} onChange={ch} type="date" className="input-field" />
          </div>
          <div>
            <label className="label">Notes</label>
            <textarea name="description" value={f.description} onChange={ch} className="input-field resize-none min-h-[70px]" placeholder="Why this goal matters..." />
          </div>
        </div>
        <div className="flex gap-3 mt-5 pt-4 border-t border-slate-100 dark:border-zinc-800">
          <button onClick={onClose} className="btn-ghost flex-1 justify-center">Cancel</button>
          <button onClick={submit} className="btn-primary flex-1 justify-center">{init?._id ? 'Update' : 'Create'}</button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function GoalCard({ g, onToggle, onEdit, onDelete }) {
  const dl = daysLeft(g.deadline);
  const pri = PRIORITIES.find(p => p.value === g.priority);

  return (
    <motion.div layout initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}
      className={`card p-4 flex items-start gap-3 transition-all duration-200 ${g.completed ? 'opacity-60' : ''}`}>
      <button onClick={() => onToggle(g)} className="mt-0.5 flex-shrink-0">
        {g.completed
          ? <CheckCircle size={20} className="text-emerald-500" />
          : <Circle size={20} className="text-slate-300 dark:text-zinc-600 hover:text-primary-500 transition-colors" />}
      </button>
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-semibold text-slate-900 dark:text-white leading-snug ${g.completed ? 'line-through opacity-60' : ''}`}>{g.title}</div>
        {g.description && <div className="text-xs text-slate-500 dark:text-zinc-500 mt-1 leading-relaxed">{g.description}</div>}
        <div className="flex flex-wrap items-center gap-2 mt-2.5">
          <span className="badge bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400">{g.type}</span>
          {pri && <span className={pri.cls}>{pri.label} priority</span>}
          {g.target_value && (
            <span className="badge bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400 flex items-center gap-1">
              <Target size={10} /> {g.target_value} {g.target_unit}
            </span>
          )}
          {dl !== null && (
            <span className={`badge ${dl < 0 ? 'badge-red' : dl < 7 ? 'badge bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400' : 'bg-slate-100 dark:bg-zinc-800 text-slate-500 dark:text-zinc-500'} flex items-center gap-1`}>
              <Calendar size={10} /> {dl < 0 ? `${Math.abs(dl)}d overdue` : dl === 0 ? 'Due today' : `${dl}d left`}
            </span>
          )}
        </div>
      </div>
      <div className="flex gap-1 flex-shrink-0">
        <button onClick={() => onEdit(g)} className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"><Edit3 size={13} /></button>
        <button onClick={() => onDelete(g._id)} className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors"><Trash2 size={13} /></button>
      </div>
    </motion.div>
  );
}

export default function GoalsPage() {
  const [goals,   setGoals]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal,   setModal]   = useState(null);

  useEffect(() => {
    (async () => {
      try {
        console.log('[Goals] Loading...');
        const data = await getGoals();
        console.log('[Goals]', data.length, 'goals');
        setGoals(data);
      } catch (e) { toast.error('Could not load goals: ' + e.message); }
      finally { setLoading(false); }
    })();
  }, []);

  const handleSave = async (f) => {
    try {
      if (f._id) {
        await updateGoal(f._id, f);
        setGoals(prev => prev.map(g => g._id === f._id ? { ...g, ...f } : g));
        toast.success('Goal updated');
      } else {
        const created = await saveGoal(f);
        setGoals(prev => [created, ...prev]);
        toast.success('Goal created');
      }
      setModal(null);
    } catch (e) { toast.error(e.message); }
  };

  const handleToggle = async (g) => {
    const updated = { ...g, completed: !g.completed };
    await updateGoal(g._id, { completed: updated.completed });
    setGoals(prev => prev.map(x => x._id === g._id ? updated : x));
    if (updated.completed) toast.success('Goal completed!');
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this goal?')) return;
    await deleteGoal(id);
    setGoals(prev => prev.filter(g => g._id !== id));
    toast.success('Goal removed');
  };

  const active    = goals.filter(g => !g.completed);
  const completed = goals.filter(g => g.completed);
  const pct = goals.length ? Math.round((completed.length / goals.length) * 100) : 0;

  return (
    <div className="page-wrap max-w-3xl">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="page-title"><Flag size={22} className="text-primary-500" /> Goals</h1>
          <p className="page-sub">Set fitness targets, track deadlines, and mark them complete as you progress.</p>
        </div>
        <button onClick={() => setModal({})} className="btn-primary flex-shrink-0"><Plus size={15} /> Add Goal</button>
      </div>

      {/* Progress */}
      {goals.length > 0 && (
        <div className="card p-4 mb-6 flex items-center gap-4">
          <div className="text-center flex-shrink-0">
            <div className="text-2xl font-black text-primary-600 dark:text-primary-400">{pct}%</div>
            <div className="text-xs text-slate-500 dark:text-zinc-500">complete</div>
          </div>
          <div className="flex-1">
            <div className="flex justify-between text-xs text-slate-500 dark:text-zinc-600 mb-1.5">
              <span>{completed.length} done</span><span>{active.length} remaining</span>
            </div>
            <div className="h-2 bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
              <motion.div className="h-full bg-primary-500 rounded-full" initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8 }} />
            </div>
          </div>
        </div>
      )}

      {/* Hint for new users */}
      {!loading && goals.length === 0 && (
        <div className="hint mb-6">
          <strong>No goals yet.</strong> Set specific, measurable targets — like "Bench press 80 kg" or "Train 4× per week" — to track your progress intentionally.
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 gap-3 text-slate-400 dark:text-zinc-600">
          <Loader2 className="w-5 h-5 animate-spin text-primary-500" /> Loading...
        </div>
      ) : (
        <div className="space-y-6">
          {active.length > 0 && (
            <div>
              <div className="label mb-3">Active — {active.length}</div>
              <div className="space-y-2">
                <AnimatePresence>{active.map(g => <GoalCard key={g._id} g={g} onToggle={handleToggle} onEdit={setModal} onDelete={handleDelete} />)}</AnimatePresence>
              </div>
            </div>
          )}
          {completed.length > 0 && (
            <div>
              <div className="label mb-3 flex items-center gap-1.5"><CheckCircle size={12} className="text-emerald-500" /> Completed — {completed.length}</div>
              <div className="space-y-2">
                <AnimatePresence>{completed.map(g => <GoalCard key={g._id} g={g} onToggle={handleToggle} onEdit={setModal} onDelete={handleDelete} />)}</AnimatePresence>
              </div>
            </div>
          )}
          {goals.length === 0 && (
            <div className="card p-12 text-center">
              <Flag size={36} className="mx-auto text-slate-200 dark:text-zinc-700 mb-3" />
              <div className="text-sm font-semibold text-slate-700 dark:text-white mb-4">No goals set yet</div>
              <button onClick={() => setModal({})} className="btn-primary mx-auto"><Plus size={14} /> Create First Goal</button>
            </div>
          )}
        </div>
      )}

      <AnimatePresence>
        {modal !== null && <GoalModal init={modal} onSave={handleSave} onClose={() => setModal(null)} />}
      </AnimatePresence>
    </div>
  );
}
