import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Toaster } from 'react-hot-toast';

import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import Navbar from './components/Navbar';
import Background3D from './components/ThreeScene';

import LandingPage   from './pages/LandingPage';
import LoginPage     from './pages/LoginPage';
import SignupPage    from './pages/SignupPage';
import DashboardPage from './pages/DashboardPage';
import UploadPage    from './pages/UploadPage';
import ResultsPage   from './pages/ResultsPage';
import HistoryPage   from './pages/HistoryPage';
import ProfilePage   from './pages/ProfilePage';
import AnalyticsPage from './pages/AnalyticsPage';
import GoalsPage     from './pages/GoalsPage';
import SimulationPage from './pages/SimulationPage';

const ProtectedRoute = ({ children }) => {
  const { token, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center text-slate-500 dark:text-zinc-400">
      Loading...
    </div>
  );
  return token ? children : <Navigate to="/login" replace />;
};

function AnimatedRoutes() {
  const location = useLocation();
  const [results, setResults] = useState(null);

  return (
    <AnimatePresence mode="wait">
      <Routes key={location.pathname} location={location}>
        <Route path="/"         element={<LandingPage />} />
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/signup"   element={<SignupPage />} />

        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/upload"    element={<ProtectedRoute><UploadPage onComplete={setResults} /></ProtectedRoute>} />
        <Route path="/results"   element={<ProtectedRoute><ResultsPage data={results} /></ProtectedRoute>} />
        <Route path="/history"   element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
        <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
        <Route path="/profile"   element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/goals"     element={<ProtectedRoute><GoalsPage /></ProtectedRoute>} />
        <Route path="/simulate"  element={<ProtectedRoute><SimulationPage /></ProtectedRoute>} />
        <Route path="*"          element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          {/* 3D animated background — visible on ALL pages */}
          <Background3D />

          <div className="relative min-h-screen flex flex-col" style={{ zIndex: 1 }}>
            <Toaster
              position="top-right"
              toastOptions={{
                className: '!rounded-xl !shadow-lg !text-sm !font-medium',
                style: { fontFamily: 'Inter, system-ui, sans-serif' },
              }}
            />
            <Navbar />
            <main className="flex-1">
              <AnimatedRoutes />
            </main>
            <footer className="py-4 text-center text-xs text-slate-400 dark:text-zinc-600 border-t border-slate-200 dark:border-zinc-800">
              GymSense AI &mdash; Powered by Hybrid CNN · Dilated Self-Attention
            </footer>
          </div>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
