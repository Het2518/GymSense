// === FILE: src/components/UploadForm.jsx ===
// GymSense AI — File upload with drag-and-drop + options

import React, { useState, useRef, useCallback } from 'react';
import { analyzeSession, checkHealth } from '../api';

const COACH_FOCUS_OPTIONS = [
  { value: 'general', label: '🎯 General', desc: 'Balanced feedback' },
  { value: 'form', label: '🧘 Form & Technique', desc: 'Tempo & movement quality' },
  { value: 'progressive_overload', label: '📈 Progressive Overload', desc: 'Next session planning' },
  { value: 'recovery', label: '💤 Recovery', desc: 'Rest & recovery focus' },
];

export default function UploadForm({ onComplete }) {
  const [file, setFile] = useState(null);
  const [userId, setUserId] = useState('');
  const [coachFocus, setCoachFocus] = useState('general');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const f = e.dataTransfer.files[0];
      if (f.name.endsWith('.csv')) {
        setFile(f);
        setError('');
      } else {
        setError('Please upload a CSV file');
      }
    }
  }, []);

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleSubmit = async () => {
    if (!file) {
      setError('Please select a CSV file');
      return;
    }

    setLoading(true);
    setError('');
    setProgress(0);

    try {
      // Check backend health first
      setStatusText('Connecting to backend...');
      setProgress(5);
      await checkHealth();

      // Start analysis
      setStatusText('Uploading and processing session data...');
      setProgress(15);

      // Simulate progress during analysis
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 85) {
            clearInterval(progressInterval);
            return 85;
          }
          return prev + Math.random() * 8;
        });
        const stages = [
          'Running neural network inference...',
          'Detecting exercise segments...',
          'Counting repetitions...',
          'Computing quality metrics...',
          'Generating AI coaching...',
          'Building PDF report...',
        ];
        setStatusText(stages[Math.floor(Math.random() * stages.length)]);
      }, 1500);

      const result = await analyzeSession(file, userId, coachFocus);

      clearInterval(progressInterval);
      setProgress(100);
      setStatusText('Analysis complete!');

      setTimeout(() => {
        onComplete(result);
      }, 500);
    } catch (err) {
      setError(err.message || 'Analysis failed. Please try again.');
      setLoading(false);
      setProgress(0);
      setStatusText('');
    }
  };

  return (
    <div className="max-w-2xl mx-auto animate-fade-in-up">
      {/* Hero */}
      <div className="text-center mb-10">
        <h2 className="text-4xl font-bold text-white mb-3">
          Analyse Your <span className="text-orange-400">Workout</span>
        </h2>
        <p className="text-gray-400 text-lg">
          Upload your gym session sensor data for AI-powered insights
        </p>
      </div>

      {/* Upload Card */}
      <div className="glass-card p-8 animate-pulse-glow">
        {/* Drag & Drop Zone */}
        <div
          className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer
            transition-all duration-300 mb-6
            ${dragActive
              ? 'border-orange-400 bg-orange-500/10'
              : file
                ? 'border-orange-500/40 bg-orange-500/5'
                : 'border-white/10 hover:border-white/20 hover:bg-white/[0.02]'
            }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            className="hidden"
            id="csv-upload"
          />
          {file ? (
            <div>
              <div className="text-4xl mb-3">📊</div>
              <p className="text-orange-400 font-semibold text-lg">{file.name}</p>
              <p className="text-gray-500 text-sm mt-1">
                {(file.size / (1024 * 1024)).toFixed(1)} MB — Click to change
              </p>
            </div>
          ) : (
            <div>
              <div className="text-4xl mb-3">📁</div>
              <p className="text-gray-300 font-medium text-lg">
                Drop your CSV file here
              </p>
              <p className="text-gray-500 text-sm mt-1">
                or click to browse — RecGym sensor data (.csv)
              </p>
            </div>
          )}
        </div>

        {/* Options */}
        <div className="space-y-4 mb-6">
          {/* Coaching Focus */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Coaching Focus
            </label>
            <div className="grid grid-cols-2 gap-2">
              {COACH_FOCUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setCoachFocus(opt.value)}
                  className={`p-3 rounded-xl text-left transition-all duration-200 text-sm
                    ${coachFocus === opt.value
                      ? 'bg-orange-500/20 border border-orange-500/40 text-orange-300'
                      : 'bg-white/[0.03] border border-white/[0.06] text-gray-400 hover:bg-white/[0.05]'
                    }`}
                >
                  <div className="font-medium">{opt.label}</div>
                  <div className="text-xs opacity-60 mt-0.5">{opt.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* User ID */}
          <div>
            <label htmlFor="user-id" className="block text-sm font-medium text-gray-400 mb-2">
              User ID <span className="text-gray-600">(optional — for session history)</span>
            </label>
            <input
              id="user-id"
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g. jay_01"
              className="input-field w-full"
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 mb-4 text-red-300 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* Progress */}
        {loading && (
          <div className="mb-4">
            <div className="flex justify-between text-xs text-gray-400 mb-1.5">
              <span>{statusText}</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-white/[0.06] rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-orange-500 to-orange-400 h-full rounded-full transition-all duration-500 ease-out shimmer"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Submit */}
        <button
          id="analyze-btn"
          onClick={handleSubmit}
          disabled={!file || loading}
          className="btn-primary w-full text-lg py-4"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analysing...
            </span>
          ) : (
            '🚀 Analyse Session'
          )}
        </button>
      </div>

      {/* Info footer */}
      <p className="text-center text-xs text-gray-600 mt-6">
        Powered by Hybrid CNN-Dilated Self-Attention • GPU-accelerated inference
      </p>
    </div>
  );
}
