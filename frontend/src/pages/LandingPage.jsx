import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Activity, ShieldCheck, Target, TrendingUp } from 'lucide-react';
import ThreeScene from '../components/ThreeScene';

export default function LandingPage() {
  const features = [
    {
      icon: <Activity className="w-6 h-6 text-orange-500" />,
      title: "Kinematic AI Analysis",
      desc: "Upload sensor data and our Hybrid CNN model instantly detects exercises, reps, and sets."
    },
    {
      icon: <Target className="w-6 h-6 text-amber-500" />,
      title: "Tempo Diagnostics",
      desc: "Get precise mathematical breakdowns of your lifting tempo to maximize muscle hypertrophy."
    },
    {
      icon: <ShieldCheck className="w-6 h-6 text-rose-500" />,
      title: "Medical-Grade Reports",
      desc: "Export your findings into professional, clinical-style PDF reports authorized by AI."
    },
    {
      icon: <TrendingUp className="w-6 h-6 text-orange-600" />,
      title: "SaaS Dashboard",
      desc: "Track your lifetime stats, aggregate muscle group distributions, and view deep analytics."
    }
  ];

  return (
    <div className="relative min-h-[calc(100vh-64px)] overflow-hidden bg-orange-50/30">
      <ThreeScene />
      
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32 flex flex-col items-center justify-center text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-3xl"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-orange-100 text-orange-700 font-semibold text-sm mb-6 border border-orange-200">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-orange-500"></span>
            </span>
            System Online • SaaS v2.0
          </div>
          
          <h1 className="text-5xl lg:text-7xl font-extrabold text-slate-800 tracking-tight mb-8">
            Diagnostic Intelligence for <span className="text-orange-600">Human Performance</span>
          </h1>
          
          <p className="text-xl text-slate-600 mb-10 max-w-2xl mx-auto leading-relaxed">
            GymSense AI utilizes a cutting-edge Hybrid CNN-Dilated Self-Attention pipeline to analyze your IMU sensor data. Get clinical-grade biomechanical feedback in seconds.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link to="/signup" className="btn-primary text-lg px-8 py-4 w-full sm:w-auto">
              Start Free Trial
            </Link>
            <Link to="/login" className="btn-secondary text-lg px-8 py-4 w-full sm:w-auto">
              Sign In
            </Link>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-24 w-full"
        >
          {features.map((feat, idx) => (
            <div key={idx} className="glass-card-light p-6 text-left hover:-translate-y-1 transition-transform">
              <div className="bg-white w-12 h-12 rounded-xl flex items-center justify-center shadow-sm border border-slate-100 mb-4">
                {feat.icon}
              </div>
              <h3 className="text-lg font-bold text-slate-800 mb-2">{feat.title}</h3>
              <p className="text-slate-500 text-sm leading-relaxed">{feat.desc}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
