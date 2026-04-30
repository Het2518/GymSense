import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Scale, Dumbbell, Moon, Shield, CheckCircle, AlertCircle, Loader2, ChevronRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { updateProfile } from '../api';
import toast from 'react-hot-toast';

const TABS = [
  { id: 'basic',    label: 'Basic Info',     icon: User },
  { id: 'body',     label: 'Body Stats',     icon: Scale },
  { id: 'fitness',  label: 'Fitness',        icon: Dumbbell },
  { id: 'lifestyle',label: 'Lifestyle',      icon: Moon },
  { id: 'medical',  label: 'Medical Notes',  icon: Shield },
];

const Field = ({ label, helper, children }) => (
  <div>
    <label className="label">{label}</label>
    {children}
    {helper && <p className="text-xs text-slate-400 dark:text-zinc-600 mt-1.5">{helper}</p>}
  </div>
);

const Input = ({ name, type = 'text', value, onChange, placeholder, min, max, step }) => (
  <input className="input-field" type={type} name={name} value={value ?? ''} onChange={onChange}
    placeholder={placeholder} min={min} max={max} step={step} />
);

const Select = ({ name, value, onChange, options }) => (
  <select className="input-field bg-white dark:bg-zinc-900" name={name} value={value ?? ''} onChange={onChange}>
    <option value="">Select...</option>
    {options.map(o => <option key={o.value || o} value={o.value || o}>{o.label || o}</option>)}
  </select>
);

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const [tab,    setTab]    = useState('basic');
  const [form,   setForm]   = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) {
      console.log('[Profile] Syncing form from user:', user);
      setForm({
        name: user.name || '', age: user.age || '', gender: user.gender || '',
        weight: user.weight || '', height: user.height || '', target_weight: user.target_weight || '',
        experience_level: user.experience_level || '', primary_goal: user.primary_goal || '',
        workout_frequency: user.workout_frequency || '', preferred_workout_duration: user.preferred_workout_duration || '',
        dietary_preference: user.dietary_preference || '', sleep_quality: user.sleep_quality || '',
        medical_conditions: user.medical_conditions || '',
      });
    }
  }, [user]);

  const onChange = (e) => {
    const { name, value } = e.target;
    console.log(`[Profile] ${name} = ${value}`);
    setForm(p => ({ ...p, [name]: value }));
  };

  const onSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        name: form.name || undefined,
        age: form.age ? Number(form.age) : null,
        gender: form.gender || null,
        weight: form.weight ? Number(form.weight) : null,
        height: form.height ? Number(form.height) : null,
        target_weight: form.target_weight ? Number(form.target_weight) : null,
        experience_level: form.experience_level || null,
        primary_goal: form.primary_goal || null,
        workout_frequency: form.workout_frequency ? Number(form.workout_frequency) : null,
        preferred_workout_duration: form.preferred_workout_duration ? Number(form.preferred_workout_duration) : null,
        dietary_preference: form.dietary_preference || null,
        sleep_quality: form.sleep_quality || null,
        medical_conditions: form.medical_conditions || null,
      };
      console.log('[Profile] Saving:', payload);
      const updated = await updateProfile(payload);
      setUser(updated);
      toast.success('Profile saved successfully');
    } catch (err) {
      console.error('[Profile] Save error:', err);
      toast.error(err.message || 'Failed to save');
    } finally { setSaving(false); }
  };

  const bmi = form.weight && form.height
    ? (Number(form.weight) / Math.pow(Number(form.height) / 100, 2)).toFixed(1)
    : null;
  const bmiLabel = !bmi ? null
    : bmi < 18.5 ? 'Underweight' : bmi < 25 ? 'Healthy' : bmi < 30 ? 'Overweight' : 'Obese';
  const bmiColor = !bmi ? '' : bmi < 25 ? 'text-emerald-600 dark:text-emerald-400' : bmi < 30 ? 'text-amber-500' : 'text-rose-600 dark:text-rose-400';

  // Completion
  const vals = Object.values(form);
  const filled = vals.filter(v => v !== '' && v != null).length;
  const pct = Math.round((filled / vals.length) * 100);

  return (
    <div className="page-wrap max-w-3xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="page-title"><User size={22} className="text-primary-500" /> Profile</h1>
        <p className="page-sub">Your details power the AI coaching engine. The more you fill in, the better the advice.</p>
        {/* Completion bar */}
        <div className="flex items-center gap-3 mt-4">
          <div className="flex-1 h-1.5 bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
            <motion.div className="h-full bg-primary-500 rounded-full" initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8 }} />
          </div>
          <span className="text-xs font-semibold text-slate-500 dark:text-zinc-500">{pct}% complete</span>
        </div>
      </div>

      <form onSubmit={onSave}>
        <div className="flex gap-6">
          {/* Sidebar tabs */}
          <div className="hidden sm:flex flex-col gap-1 w-40 flex-shrink-0">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button key={id} type="button" onClick={() => setTab(id)}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm font-medium text-left transition-all duration-150 ${
                  tab === id
                    ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                    : 'text-slate-500 dark:text-zinc-500 hover:bg-slate-100 dark:hover:bg-zinc-800'
                }`}>
                <Icon size={14} /> {label}
              </button>
            ))}
          </div>

          {/* Mobile tabs */}
          <div className="sm:hidden flex gap-1 w-full overflow-x-auto mb-4">
            {TABS.map(({ id, label }) => (
              <button key={id} type="button" onClick={() => setTab(id)}
                className={`flex-shrink-0 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  tab === id ? 'bg-primary-500 text-white' : 'bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400'
                }`}>
                {label}
              </button>
            ))}
          </div>

          {/* Panel */}
          <div className="flex-1 min-w-0">
            {/* User header */}
            <div className="card p-4 mb-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-primary-600 dark:bg-primary-500 flex items-center justify-center text-white text-lg font-bold flex-shrink-0">
                {user?.name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <div className="min-w-0">
                <div className="font-bold text-slate-900 dark:text-white truncate">{user?.name}</div>
                <div className="text-xs text-slate-400 dark:text-zinc-600 truncate">{user?.email}</div>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {user?.primary_goal && <span className="badge badge-indigo">{user.primary_goal}</span>}
                  {bmi && <span className={`badge bg-slate-100 dark:bg-zinc-800 ${bmiColor}`}>BMI {bmi} · {bmiLabel}</span>}
                </div>
              </div>
            </div>

            {/* Tab content */}
            <AnimatePresence mode="wait">
              <motion.div key={tab} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.15 }}
                className="card p-5 space-y-4">

                {tab === 'basic' && (<>
                  <Field label="Full Name"><Input name="name" value={form.name} onChange={onChange} placeholder="Your name" /></Field>
                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Age"><Input name="age" type="number" value={form.age} onChange={onChange} placeholder="Years" min={10} max={100} /></Field>
                    <Field label="Gender"><Select name="gender" value={form.gender} onChange={onChange} options={['Male','Female','Non-binary','Prefer not to say']} /></Field>
                  </div>
                  <Field label="Email">
                    <input className="input-field opacity-50 cursor-not-allowed" value={user?.email || ''} disabled />
                    <p className="text-xs text-slate-400 dark:text-zinc-600 mt-1.5">Contact support to change your email.</p>
                  </Field>
                </>)}

                {tab === 'body' && (<>
                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Current Weight (kg)"><Input name="weight" type="number" value={form.weight} onChange={onChange} placeholder="e.g. 75" min={30} max={300} step={0.1} /></Field>
                    <Field label="Height (cm)"><Input name="height" type="number" value={form.height} onChange={onChange} placeholder="e.g. 178" min={100} max={250} /></Field>
                  </div>
                  <Field label="Target Weight (kg)" helper="Your goal body weight. Used by the AI to tailor volume and diet advice.">
                    <Input name="target_weight" type="number" value={form.target_weight} onChange={onChange} placeholder="e.g. 70" min={30} max={300} step={0.1} />
                  </Field>
                  {bmi && (
                    <div className={`hint text-sm font-medium ${bmiColor}`}>
                      Your BMI is <strong>{bmi}</strong> — {bmiLabel}.
                      {bmi >= 25 && ' The AI will factor this into recovery and cardio recommendations.'}
                      {bmi < 18.5 && ' The AI will recommend higher calorie training strategies.'}
                    </div>
                  )}
                </>)}

                {tab === 'fitness' && (<>
                  <Field label="Experience Level" helper="How long have you been training consistently?">
                    <Select name="experience_level" value={form.experience_level} onChange={onChange}
                      options={[{ value:'Beginner',     label:'Beginner (< 1 year)' },
                                { value:'Intermediate', label:'Intermediate (1–3 years)' },
                                { value:'Advanced',     label:'Advanced (3–6 years)' },
                                { value:'Elite',        label:'Elite (6+ years)' }]} />
                  </Field>
                  <Field label="Primary Goal" helper="The AI will prioritise advice around this goal.">
                    <Select name="primary_goal" value={form.primary_goal} onChange={onChange}
                      options={['Hypertrophy','Strength','Weight Loss','Endurance','General Health','Athletic Performance']} />
                  </Field>
                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Sessions / Week"><Input name="workout_frequency" type="number" value={form.workout_frequency} onChange={onChange} min={1} max={7} placeholder="e.g. 4" /></Field>
                    <Field label="Session Length (min)"><Input name="preferred_workout_duration" type="number" value={form.preferred_workout_duration} onChange={onChange} min={20} max={180} placeholder="e.g. 60" /></Field>
                  </div>
                </>)}

                {tab === 'lifestyle' && (<>
                  <Field label="Dietary Preference" helper="Used to tailor nutrition tips in AI coaching.">
                    <Select name="dietary_preference" value={form.dietary_preference} onChange={onChange}
                      options={['Standard','Vegetarian','Vegan','Keto','Paleo','Intermittent Fasting']} />
                  </Field>
                  <Field label="Sleep Quality" helper="Poor sleep reduces recovery by up to 30%. The AI adjusts volume recommendations accordingly.">
                    <Select name="sleep_quality" value={form.sleep_quality} onChange={onChange}
                      options={[{ value:'Excellent', label:'Excellent (8+ hrs, restful)' },
                                { value:'Good',      label:'Good (7–8 hrs)' },
                                { value:'Fair',      label:'Fair (5–6 hrs)' },
                                { value:'Poor',      label:'Poor (< 5 hrs or disturbed)' }]} />
                  </Field>
                </>)}

                {tab === 'medical' && (<>
                  <Field label="Conditions, Injuries & Notes" helper="Shared only with the AI coach. Helps generate safer, more relevant advice.">
                    <textarea name="medical_conditions" value={form.medical_conditions} onChange={onChange}
                      className="input-field min-h-[130px] resize-y"
                      placeholder={"Examples:\n- Left shoulder impingement — avoid overhead press\n- Lower back issues — no heavy deadlifts\n- Goal: run 5K by September"} />
                  </Field>
                  <div className="hint text-xs text-slate-600 dark:text-zinc-400">
                    GymSense AI coaching is not a substitute for professional medical advice. Always consult your physician before changing your training programme.
                  </div>
                </>)}
              </motion.div>
            </AnimatePresence>

            {/* Save */}
            <div className="flex justify-end mt-4">
              <button type="submit" disabled={saving} className="btn-primary">
                {saving ? <><Loader2 size={14} className="animate-spin" /> Saving...</> : <><CheckCircle size={14} /> Save Profile</>}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
