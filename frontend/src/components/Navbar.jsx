import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Activity, LayoutDashboard, Upload, History, BarChart3, Flag, User, LogOut, Sun, Moon, Menu, X, Zap } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/upload',    label: 'Analyse',   icon: Upload },
  { to: '/simulate',  label: 'Simulate',  icon: Zap },
  { to: '/history',   label: 'History',   icon: History },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/goals',     label: 'Goals',     icon: Flag },
];

export default function Navbar() {
  const { user, token, logout } = useAuth();
  const { dark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = () => { logout(); navigate('/'); setOpen(false); };

  const linkCls = ({ isActive }) =>
    `flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150 ${
      isActive
        ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'
        : 'text-slate-600 dark:text-zinc-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-slate-100 dark:hover:bg-zinc-800'
    }`;

  return (
    <nav
      className="sticky top-0 z-50 border-b border-slate-200 dark:border-zinc-800"
      style={{ background: dark ? 'rgba(9,9,11,0.85)' : 'rgba(255,255,255,0.85)', backdropFilter: 'blur(16px)' }}
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <NavLink to={token ? '/dashboard' : '/'} className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-primary-600 dark:bg-primary-500 flex items-center justify-center shadow-sm">
              <Activity size={16} className="text-white" />
            </div>
            <span className="font-bold text-slate-900 dark:text-white text-base tracking-tight">
              GymSense<span className="text-primary-500 font-light"> AI</span>
            </span>
          </NavLink>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {token ? (
              <>
                {NAV.map(({ to, label, icon: Icon }) => (
                  <NavLink key={to} to={to} className={linkCls}>
                    <Icon size={15} /> {label}
                  </NavLink>
                ))}
                <div className="w-px h-5 bg-slate-200 dark:bg-zinc-700 mx-2" />
                <NavLink to="/profile" className={linkCls}>
                  <User size={15} /> {user?.name?.split(' ')[0] || 'Profile'}
                </NavLink>
                <button onClick={handleLogout} className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium text-slate-500 dark:text-zinc-500 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-all duration-150">
                  <LogOut size={15} /> Logout
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login"  className="btn-ghost">Sign In</NavLink>
                <NavLink to="/signup" className="btn-primary">Get Started</NavLink>
              </>
            )}
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="ml-2 w-9 h-9 flex items-center justify-center rounded-xl bg-slate-100 dark:bg-zinc-800 text-slate-500 dark:text-zinc-400 hover:bg-slate-200 dark:hover:bg-zinc-700 transition-all duration-150"
              aria-label="Toggle theme"
            >
              {dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>

          {/* Mobile: theme + hamburger */}
          <div className="flex md:hidden items-center gap-2">
            <button onClick={toggleTheme} className="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-100 dark:bg-zinc-800 text-slate-500 dark:text-zinc-400">
              {dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <button onClick={() => setOpen(o => !o)} className="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400">
              {open ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden border-t border-slate-200 dark:border-zinc-800 px-4 pb-4 pt-3 space-y-1" style={{ background: dark ? 'rgba(9,9,11,0.95)' : 'rgba(255,255,255,0.95)' }}>
          {token ? (
            <>
              {NAV.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} onClick={() => setOpen(false)} className={linkCls}>
                  <Icon size={15} /> {label}
                </NavLink>
              ))}
              <NavLink to="/profile" onClick={() => setOpen(false)} className={linkCls}>
                <User size={15} /> Profile
              </NavLink>
              <button onClick={handleLogout} className="flex items-center gap-2 w-full px-3 py-2 rounded-xl text-sm font-medium text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20">
                <LogOut size={15} /> Logout
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login"  onClick={() => setOpen(false)} className={linkCls}><User size={15} /> Sign In</NavLink>
              <NavLink to="/signup" onClick={() => setOpen(false)} className="btn-primary w-full justify-center">Get Started</NavLink>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
