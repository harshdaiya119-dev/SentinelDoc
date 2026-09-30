import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield,
  Lock,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  ArrowRight,
  Info,
  Zap,
  Bookmark,
  Check,
  Trash2,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';

const SAVED_CREDS_KEY = 'sentineldoc-saved-credentials';

const DEMO_ACCOUNTS = [
  { username: 'admin', password: 'sentinel2026', displayName: 'Admin' },
  { username: 'judge', password: 'ieee2026', displayName: 'Judge' },
  { username: 'helium', password: 'helium123', displayName: 'Team Helium' },
];

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const { theme, toggleTheme } = useTheme();

  // Load saved credentials from localStorage on initial render
  const [savedCreds, setSavedCreds] = useState<{ username: string; password: string } | null>(() => {
    try {
      const stored = localStorage.getItem(SAVED_CREDS_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [username, setUsername] = useState(() => savedCreds?.username || '');
  const [password, setPassword] = useState(() => savedCreds?.password || '');
  const [rememberMe, setRememberMe] = useState(true);
  const [savedFeedback, setSavedFeedback] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [shake, setShake] = useState(false);
  const [showHint, setShowHint] = useState(false);

  // Perform login action
  const performLogin = (u: string, p: string) => {
    const cleanUser = u.trim();
    if (!cleanUser || !p.trim()) {
      setError('Please enter both username and password.');
      triggerShake();
      return;
    }

    if (rememberMe) {
      try {
        const payload = { username: cleanUser, password: p };
        localStorage.setItem(SAVED_CREDS_KEY, JSON.stringify(payload));
        setSavedCreds(payload);
      } catch (err) {
        console.error('Failed to save credentials to localStorage:', err);
      }
    }

    const success = login(cleanUser, p);
    if (!success) {
      setError('ACCESS DENIED — Invalid credentials.');
      triggerShake();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    performLogin(username, password);
  };

  // Instant 1-click login using saved or specific credentials
  const handleQuickLogin = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError('');
    performLogin(u, p);
  };

  // Explicitly save current typed credentials
  const handleSaveCurrentCreds = () => {
    const cleanUser = username.trim();
    if (!cleanUser || !password.trim()) {
      setError('Enter username and password first to save.');
      triggerShake();
      return;
    }

    try {
      const payload = { username: cleanUser, password };
      localStorage.setItem(SAVED_CREDS_KEY, JSON.stringify(payload));
      setSavedCreds(payload);
      setSavedFeedback(true);
      setError('');
      setTimeout(() => setSavedFeedback(false), 2500);
    } catch (err) {
      console.error('Failed to save credentials:', err);
    }
  };

  // Clear saved credentials
  const handleClearSavedCreds = () => {
    localStorage.removeItem(SAVED_CREDS_KEY);
    setSavedCreds(null);
  };

  const triggerShake = () => {
    setShake(true);
    setTimeout(() => setShake(false), 500);
  };

  return (
    <div className="min-h-screen bg-canvas flex flex-col items-center justify-center px-4 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-teal-brand/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-teal-brand/3 rounded-full blur-3xl" />
      </div>

      {/* Theme Toggle (top right) */}
      <button
        onClick={toggleTheme}
        className="absolute top-6 right-6 p-2 rounded-lg bg-surface border border-border hover:border-teal-brand text-text-muted hover:text-teal-brand transition-all"
        title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      >
        {theme === 'dark' ? (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
        )}
      </button>

      {/* Login Card */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className={`relative z-10 w-full max-w-md ${shake ? 'animate-[shake_0.5s_ease-in-out]' : ''}`}
        style={shake ? { animation: 'shake 0.5s ease-in-out' } : {}}
      >
        {/* Branding Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-teal-brand/10 border-2 border-teal-brand/30 flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-teal-brand" />
          </div>
          <h1 className="text-3xl font-bold text-text-primary tracking-tight">
            Sentinel<span className="text-teal-brand">Doc</span>
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Personal Data Leak Detector & Compliance Redactor
          </p>
          <div className="flex items-center justify-center space-x-2 mt-3">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-teal-brand animate-pulse" />
            <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted">
              SECURE AUTHENTICATION REQUIRED
            </span>
          </div>
        </div>

        {/* Form Card */}
        <div className="bg-surface border border-border rounded-xl p-6 shadow-xl">
          {/* ── Saved Credentials 1-Click Instant Login Banner ── */}
          {savedCreds && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-5 p-3 rounded-lg bg-teal-brand/10 border border-teal-brand/30 flex items-center justify-between"
            >
              <div className="flex items-center space-x-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-teal-brand/20 flex items-center justify-center flex-shrink-0">
                  <Zap className="w-4 h-4 text-teal-brand animate-pulse" />
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] font-mono text-text-muted uppercase">Saved Credentials Found</p>
                  <p className="text-xs font-mono font-bold text-teal-brand truncate">
                    {savedCreds.username}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-1.5 flex-shrink-0">
                <button
                  type="button"
                  onClick={() => handleQuickLogin(savedCreds.username, savedCreds.password)}
                  className="px-3 py-1.5 rounded-md bg-teal-brand text-black text-xs font-mono font-bold hover:opacity-90 transition-all flex items-center space-x-1 shadow-sm active:scale-95 cursor-pointer"
                  title="Click to paste saved credentials and login immediately without entering password"
                >
                  <Zap className="w-3.5 h-3.5" />
                  <span>1-Click Login</span>
                </button>
                <button
                  type="button"
                  onClick={handleClearSavedCreds}
                  className="p-1.5 rounded hover:bg-canvas text-text-muted hover:text-crimson-brand transition-colors cursor-pointer"
                  title="Forget saved credentials"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username Field */}
            <div>
              <label className="block text-xs font-mono font-semibold text-text-muted uppercase tracking-wider mb-2">
                Username
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => { setUsername(e.target.value); setError(''); }}
                  placeholder="Enter username"
                  autoComplete="username"
                  className="w-full pl-10 pr-4 py-3 bg-card border border-border rounded-lg text-text-primary placeholder:text-text-muted text-sm focus:outline-none focus:border-teal-brand focus:ring-1 focus:ring-teal-brand/30 transition-all"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-xs font-mono font-semibold text-text-muted uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setError(''); }}
                  placeholder="Enter password"
                  autoComplete="current-password"
                  className="w-full pl-10 pr-12 py-3 bg-card border border-border rounded-lg text-text-primary placeholder:text-text-muted text-sm focus:outline-none focus:border-teal-brand focus:ring-1 focus:ring-teal-brand/30 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* ── Save Credentials Controls ── */}
            <div className="flex items-center justify-between text-xs font-mono pt-1">
              <label className="flex items-center space-x-2 cursor-pointer text-text-secondary select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-3.5 h-3.5 rounded border-border text-teal-brand focus:ring-0 focus:ring-offset-0 bg-card cursor-pointer"
                />
                <span>Save credentials</span>
              </label>

              <button
                type="button"
                onClick={handleSaveCurrentCreds}
                className="flex items-center space-x-1 text-teal-brand hover:underline cursor-pointer"
                title="Save current credentials now for 1-click login"
              >
                {savedFeedback ? (
                  <>
                    <Check className="w-3 h-3 text-teal-brand" />
                    <span className="font-bold text-teal-brand">Saved!</span>
                  </>
                ) : (
                  <>
                    <Bookmark className="w-3 h-3" />
                    <span>Save My Credentials</span>
                  </>
                )}
              </button>
            </div>

            {/* Error Message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className="flex items-center space-x-2 px-3 py-2.5 rounded-lg bg-crimson-subtle border border-crimson-brand/30 text-crimson-brand text-xs font-mono"
                >
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit Button */}
            <button
              type="submit"
              className="w-full flex items-center justify-center space-x-2 py-3 rounded-lg bg-teal-brand text-white font-semibold text-sm hover:opacity-90 transition-all shadow-lg shadow-teal-brand/20 active:scale-[0.98] cursor-pointer"
            >
              <Lock className="w-4 h-4" />
              <span>Authenticate & Enter SOC</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Credential Hint & 1-Click Demo Accounts */}
          <div className="mt-5 pt-4 border-t border-border">
            <button
              type="button"
              onClick={() => setShowHint(!showHint)}
              className="flex items-center space-x-1.5 text-[11px] font-mono text-text-muted hover:text-teal-brand transition-colors mx-auto cursor-pointer"
            >
              <Info className="w-3.5 h-3.5" />
              <span>{showHint ? 'Hide' : 'Show'} 1-click demo credentials</span>
            </button>
            <AnimatePresence>
              {showHint && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="mt-3 p-2.5 rounded-lg bg-card border border-border text-[11px] font-mono space-y-1.5">
                    <p className="text-[10px] text-text-muted uppercase tracking-wider px-1">
                      Click any account to instant login:
                    </p>
                    {DEMO_ACCOUNTS.map((acc) => (
                      <button
                        key={acc.username}
                        type="button"
                        onClick={() => handleQuickLogin(acc.username, acc.password)}
                        className="w-full flex items-center justify-between p-2 rounded hover:bg-surface border border-transparent hover:border-teal-brand/40 transition-all text-left cursor-pointer group"
                      >
                        <div>
                          <span className="font-bold text-text-primary group-hover:text-teal-brand">
                            {acc.displayName}
                          </span>
                          <span className="text-text-muted text-[10px] ml-2 font-mono">
                            ({acc.username} / {acc.password})
                          </span>
                        </div>
                        <span className="text-[10px] font-mono text-teal-brand flex items-center space-x-1 opacity-80 group-hover:opacity-100 font-semibold">
                          <Zap className="w-3 h-3" />
                          <span>Login</span>
                        </span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-[10px] font-mono text-text-muted mt-6">
          SENTINELDOC // IEEE SRM AP HACKATHON — CYBERSECURITY TRACK // TEAM HELIUM
        </p>
      </motion.div>

      {/* Shake animation keyframes */}
      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-4px); }
          20%, 40%, 60%, 80% { transform: translateX(4px); }
        }
      `}</style>
    </div>
  );
};
