import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Activity, Loader2, FileCheck, Dumbbell } from 'lucide-react';
import toast from 'react-hot-toast';
import { analyzeSession } from '../api';
import ThreeScene from '../components/ThreeScene';

export default function UploadPage({ onComplete }) {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [coachFocus, setCoachFocus] = useState('general');
  const navigate = useNavigate();

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      toast.error('Please select a file first.');
      return;
    }

    setAnalyzing(true);
    try {
      const data = await analyzeSession(file, coachFocus);
      toast.success('Analysis complete!');
      if (onComplete) onComplete(data);
      navigate('/results');
    } catch (err) {
      toast.error('Analysis failed: ' + err.message);
      setAnalyzing(false);
    }
  };

  return (
    <div className="relative min-h-[calc(100vh-64px)] overflow-hidden">
      {/* 3D Background */}
      <ThreeScene />

      {/* Foreground Content */}
      <div className="relative z-10 max-w-3xl mx-auto px-4 py-12 lg:py-24">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center justify-center p-3 bg-white/80 rounded-2xl shadow-sm mb-4 border border-orange-100 backdrop-blur-sm">
            <Activity className="w-8 h-8 text-orange-600" />
          </div>
          <h1 className="text-4xl lg:text-5xl font-extrabold text-slate-800 tracking-tight mb-4">
            Analyze Session
          </h1>
          <p className="text-lg text-slate-600 max-w-xl mx-auto">
            Upload your raw IMU sensor data (CSV) and our Hybrid AI model will reconstruct your entire workout.
          </p>
        </motion.div>

        <motion.form 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          onSubmit={handleSubmit} 
          className="glass-card p-8 md:p-12 shadow-xl"
        >
          {/* File Upload Area */}
          <div 
            className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-200 cursor-pointer mb-8 relative overflow-hidden group
              ${isDragging ? 'border-orange-500 bg-orange-50/50' : 'border-slate-300 bg-slate-50/50 hover:bg-slate-100 hover:border-slate-400'}
              ${file ? 'border-orange-500 bg-orange-50/20' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-upload').click()}
          >
            <input 
              id="file-upload"
              type="file" 
              accept=".csv"
              className="hidden" 
              onChange={(e) => e.target.files && setFile(e.target.files[0])}
            />

            <AnimatePresence mode="wait">
              {file ? (
                <motion.div 
                  key="file-selected"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center"
                >
                  <div className="bg-orange-100 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform">
                    <FileCheck className="w-10 h-10 text-orange-600" />
                  </div>
                  <p className="text-slate-800 font-bold text-lg mb-1">{file.name}</p>
                  <p className="text-slate-500 text-sm">{(file.size / 1024).toFixed(1)} KB</p>
                  <p className="text-orange-600 text-sm font-semibold mt-4 hover:underline">Click to change file</p>
                </motion.div>
              ) : (
                <motion.div 
                  key="no-file"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center"
                >
                  <div className="bg-white p-4 rounded-full mb-4 shadow-sm group-hover:scale-110 transition-transform">
                    <Upload className="w-10 h-10 text-slate-400" />
                  </div>
                  <p className="text-slate-700 font-semibold text-lg mb-2">Drag & Drop your CSV file here</p>
                  <p className="text-slate-500 text-sm">or click to browse from your computer</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Coaching Focus */}
          <div className="mb-8">
            <label className="block text-sm font-bold text-slate-700 mb-3 uppercase tracking-wide">
              AI Coaching Focus
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {['general', 'hypertrophy', 'strength', 'endurance'].map((focus) => (
                <div 
                  key={focus}
                  onClick={() => setCoachFocus(focus)}
                  className={`border rounded-xl p-3 text-center cursor-pointer transition-all ${
                    coachFocus === focus 
                      ? 'bg-orange-600 border-orange-600 text-white font-semibold shadow-md scale-105' 
                      : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300 font-medium'
                  }`}
                >
                  {focus.charAt(0).toUpperCase() + focus.slice(1)}
                </div>
              ))}
            </div>
          </div>

          <button 
            type="submit" 
            disabled={!file || analyzing}
            className="w-full btn-primary h-14 text-lg shadow-lg flex items-center justify-center relative overflow-hidden"
          >
            {analyzing ? (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-3"
              >
                <Loader2 className="w-6 h-6 animate-spin" />
                <span>Running Inference Pipeline...</span>
              </motion.div>
            ) : (
              <span className="flex items-center gap-2">
                <Dumbbell className="w-6 h-6" /> Analyze Workout
              </span>
            )}

            {/* Scanning light effect when analyzing */}
            {analyzing && (
              <motion.div 
                animate={{ x: ['-100%', '200%'] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                className="absolute top-0 bottom-0 w-1/3 bg-gradient-to-r from-transparent via-white/30 to-transparent skew-x-12"
              />
            )}
          </button>
        </motion.form>
      </div>
    </div>
  );
}
