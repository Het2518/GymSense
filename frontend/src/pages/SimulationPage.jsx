import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Play, Square, Loader2, Activity, Cpu, Dumbbell, Zap } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';
import { analyzeSession } from '../api';

const WORKOUT_CLASSES = [
  "Null", "Adductor", "ArmCurl", "BenchPress", "LegCurl", "LegPress",
  "Riding", "RopeSkipping", "Running", "Squat", "StairClimber", "Walking"
];

// Physics profiles mimicking human kinematics
const PROFILES = {
  Adductor:    { freq:0.38, amp:[2.0,0.3,0.4,0.2,0.6,0.15,0.14], noise:0.05 },
  ArmCurl:     { freq:0.55, amp:[0.5,2.2,0.3,0.2,0.55,1.8,0.40], noise:0.07 },
  BenchPress:  { freq:0.45, amp:[1.8,0.3,0.5,0.2,0.4,0.2,0.18],  noise:0.06 },
  LegCurl:     { freq:0.50, amp:[0.2,0.5,1.5,0.8,0.2,0.3,0.18],  noise:0.05 },
  LegPress:    { freq:0.40, amp:[0.3,0.4,2.0,0.6,0.15,0.25,0.22],noise:0.06 },
  Null:        { freq:0.05, amp:[0.04,0.04,0.1,0.02,0.02,0.03,0.05], noise:0.03 },
  Riding:      { freq:1.50, amp:[0.15,0.2,0.8,0.1,0.1,0.15,0.60], noise:0.04 },
  RopeSkipping:{ freq:3.20, amp:[0.4,0.3,3.0,0.2,0.15,0.4,0.32],  noise:0.15 },
  Running:     { freq:2.80, amp:[0.8,0.5,2.5,0.3,0.2,0.6,0.22],   noise:0.12 },
  Squat:       { freq:0.45, amp:[0.2,1.8,0.8,0.55,0.1,0.2,0.28],  noise:0.06 },
  StairClimber:{ freq:0.85, amp:[0.4,0.85,1.6,0.4,0.2,0.3,0.20],  noise:0.08 },
  Walking:     { freq:1.80, amp:[0.3,0.2,1.2,0.1,0.1,0.3,0.12],   noise:0.06 },
};

const CHANNEL_COLORS = ['#ff4d6d', '#ff9a3c', '#ffd166', '#06d6a0', '#118ab2', '#8338ec', '#ff70a6'];
const CHANNEL_NAMES = ['A_x', 'A_y', 'A_z', 'G_x', 'G_y', 'G_z', 'C_1'];

// Box-Muller transform for gaussian noise
function randn() {
  let u = Math.random(), v = Math.random();
  if (u === 0) u = 0.001; 
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

export default function SimulationPage() {
  const navigate = useNavigate();
  const [isRunning, setIsRunning] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [workout, setWorkout] = useState("Null");
  
  // Ref for continuous data accumulation
  const dataStore = useRef([]);
  const [chartData, setChartData] = useState([]);
  const [stats, setStats] = useState({ duration: 0, samples: 0 });
  const timerRef = useRef(null);

  // Clean up on unmount
  useEffect(() => {
    return () => stopSimulation();
  }, []);

  const stopSimulation = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const toggleSimulation = () => {
    if (isRunning) {
      stopSimulation();
      setIsRunning(false);
    } else {
      setIsRunning(true);
    }
  };

  // Re-bind interval if workout changes while running
  const workoutRef = useRef(workout);
  useEffect(() => {
    workoutRef.current = workout;
  }, [workout]);

  useEffect(() => {
    if (isRunning) {
      stopSimulation();
      const SR = 20;
      const intervalMs = 1000 / SR;
      
      timerRef.current = setInterval(() => {
        const currentWk = workoutRef.current;
        const p = PROFILES[currentWk] || PROFILES.Null;
        const phase = [0, 1.57, 0, 3.14, 0, 0.79, 0.3];
        
        const t = dataStore.current.length / SR;
        
        // Generate single frame (7 channels)
        const frame = CHANNEL_NAMES.reduce((acc, ch, ci) => {
          let v = p.amp[ci] * Math.sin(2 * Math.PI * p.freq * t + phase[ci]);
          v += p.amp[ci] * 0.2 * Math.sin(2 * Math.PI * p.freq * 2 * t + phase[ci] * 1.2);
          v += randn() * p.noise * (p.amp[ci] + 0.01);
          
          if (currentWk === 'RopeSkipping' && ci === 2) {
            const interval = Math.floor(SR / p.freq);
            if (dataStore.current.length % interval < 3) v += Math.random() * 2 + 1.2;
          }
          acc[ch] = v;
          return acc;
        }, {});
        
        frame.time = t;
        frame.workout = currentWk;
        
        // Push to permanent store
        dataStore.current.push(frame);
        
        // Update live chart (last 100 points = 5 seconds)
        setChartData([...dataStore.current].slice(-100));
        setStats({
          duration: Math.floor(dataStore.current.length / SR),
          samples: dataStore.current.length
        });

      }, intervalMs);
    } else {
      stopSimulation();
    }
    return stopSimulation;
  }, [isRunning]);

  const handleReset = () => {
    stopSimulation();
    setIsRunning(false);
    dataStore.current = [];
    setChartData([]);
    setStats({ duration: 0, samples: 0 });
  };

  const handleAnalyze = async () => {
    if (dataStore.current.length < 100) {
      toast.error('Not enough data. Please simulate for at least 5 seconds.');
      return;
    }
    
    stopSimulation();
    setIsRunning(false);
    setIsAnalyzing(true);
    
    try {
      // 1. Build CSV string
      // Format: Subject,Position,Session,A_x,A_y,A_z,G_x,G_y,G_z,C_1,Workout
      const header = "Subject,Position,Session,A_x,A_y,A_z,G_x,G_y,G_z,C_1,Workout\n";
      const rows = dataStore.current.map(f => {
        // Normalise base generated values around 0.5 (to mimic the dummy.csv provided)
        // Scaler std dev is ~0.04, so using 0.04 correctly maps variance for the model!
        const fmt = (val) => (val * 0.04 + 0.5).toFixed(4);
        return `1,wrist,1,${fmt(f.A_x)},${fmt(f.A_y)},${fmt(f.A_z)},${fmt(f.G_x)},${fmt(f.G_y)},${fmt(f.G_z)},${fmt(f.C_1)},${f.workout}`;
      });
      const csvContent = header + rows.join("\n");
      
      // 2. Convert to File object
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const file = new File([blob], `simulation_${Date.now()}.csv`, { type: 'text/csv' });
      
      toast.success('Simulation complete! Analyzing data...');
      
      // 3. Send to API (auto-bridge)
      const data = await analyzeSession(file, "general");
      
      toast.success('Analysis successful!');
      navigate('/results', { state: { resultData: data } });
      
    } catch (err) {
      console.error(err);
      toast.error(err.message || 'Failed to analyze simulation');
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="page-wrap">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title"><Activity size={22} className="text-primary-500" /> Real-Time Simulation</h1>
          <p className="page-sub">
            Generate synthetic sensor streams and feed them directly into the analytics pipeline.
          </p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={toggleSimulation} 
            disabled={isAnalyzing}
            className={`${isRunning ? 'bg-amber-100 text-amber-700 border-amber-200 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800' : 'btn-primary'} px-4 py-2 rounded-xl font-semibold flex items-center gap-2 transition-all`}
          >
            {isRunning ? <Square size={16} className="fill-current" /> : <Play size={16} className="fill-current" />}
            {isRunning ? 'Stop Simulation' : 'Start Simulation'}
          </button>
          
          <button 
            onClick={handleAnalyze}
            disabled={isAnalyzing || dataStore.current.length === 0}
            className={`btn-outline bg-white dark:bg-zinc-900 px-4 py-2 flex items-center gap-2 transition-all ${
              isAnalyzing ? 'border-primary-500 text-primary-600 bg-primary-50 dark:bg-primary-900/20' : 'disabled:opacity-50'
            }`}
          >
            {isAnalyzing ? (
              <>
                <Loader2 size={16} className="animate-spin text-primary-500" />
                <span className="animate-pulse font-medium">Running Deep Inference...</span>
              </>
            ) : (
              <>
                <Zap size={16} />
                Analyze Session
              </>
            )}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Controls Panel */}
        <div className="lg:col-span-1 space-y-6">
          <div className="card p-5">
            <h3 className="text-sm font-bold text-slate-800 dark:text-zinc-200 mb-4 flex items-center gap-2 uppercase tracking-wide">
              <Dumbbell size={16} className="text-primary-500" /> Current Activity
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {WORKOUT_CLASSES.map(cls => (
                <button
                  key={cls}
                  onClick={() => setWorkout(cls)}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold border transition-all ${
                    workout === cls 
                      ? 'bg-primary-50 border-primary-300 text-primary-700 dark:bg-primary-900/30 dark:border-primary-500/50 dark:text-primary-400' 
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-primary-300 dark:bg-zinc-800/50 dark:border-zinc-700/50 dark:text-zinc-400 dark:hover:border-primary-500/30'
                  }`}
                >
                  {cls}
                </button>
              ))}
            </div>
            {isRunning && (
              <div className="mt-4 text-center p-3 rounded-lg bg-emerald-50 border border-emerald-100 dark:bg-emerald-900/20 dark:border-emerald-800/30">
                <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium animate-pulse flex items-center justify-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500"></div> Stream Active: {workout}
                </div>
              </div>
            )}
          </div>

          <div className="card p-5">
            <h3 className="text-sm font-bold text-slate-800 dark:text-zinc-200 mb-4 flex items-center gap-2 uppercase tracking-wide">
              <Cpu size={16} className="text-primary-500" /> Sensor Status
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center border-b border-slate-100 dark:border-zinc-800 pb-2">
                <span className="text-sm text-slate-500 dark:text-zinc-400">Sample Rate</span>
                <span className="text-sm font-mono font-semibold text-slate-700 dark:text-zinc-300">20 Hz</span>
              </div>
              <div className="flex justify-between items-center border-b border-slate-100 dark:border-zinc-800 pb-2">
                <span className="text-sm text-slate-500 dark:text-zinc-400">Total Samples</span>
                <span className="text-sm font-mono font-semibold text-primary-600 dark:text-primary-400">{stats.samples}</span>
              </div>
              <div className="flex justify-between items-center pb-1">
                <span className="text-sm text-slate-500 dark:text-zinc-400">Elapsed Time</span>
                <span className="text-sm font-mono font-semibold text-slate-700 dark:text-zinc-300">{stats.duration} s</span>
              </div>
              
              <button 
                onClick={handleReset} 
                disabled={isRunning || stats.samples === 0}
                className="w-full mt-4 py-2 text-xs font-semibold text-rose-500 bg-rose-50 border border-rose-100 hover:bg-rose-100 rounded-lg transition-colors dark:bg-rose-900/20 dark:border-rose-900/30 dark:hover:bg-rose-900/40 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Clear Buffer
              </button>
            </div>
          </div>
        </div>

        {/* Visualization Panel */}
        <div className="lg:col-span-2">
          <div className="card p-5 h-[500px] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-800 dark:text-zinc-200 uppercase tracking-wide">Live Telemetry (5s window)</h3>
              <div className="flex gap-3">
                {CHANNEL_NAMES.map((name, i) => (
                  <div key={name} className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-sm" style={{ background: CHANNEL_COLORS[i] }}></div>
                    <span className="text-[10px] font-mono font-semibold text-slate-500">{name}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="flex-1 min-h-0 bg-slate-50 dark:bg-zinc-900/50 rounded-xl border border-slate-100 dark:border-zinc-800 p-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="time" type="number" domain={['dataMin', 'dataMax']} hide />
                  <YAxis domain={[-5, 5]} tick={{fontSize: 10, fill: '#94a3b8'}} axisLine={false} tickLine={false} />
                  {CHANNEL_NAMES.map((name, i) => (
                    <Line 
                      key={name}
                      type="monotone" 
                      dataKey={name} 
                      stroke={CHANNEL_COLORS[i]} 
                      strokeWidth={1.5} 
                      dot={false}
                      isAnimationActive={false} 
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
