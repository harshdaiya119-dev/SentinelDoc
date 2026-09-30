import React, { useEffect, useState } from 'react';
import { Shield, CheckCircle2, AlertCircle, RefreshCw, Sun, Moon, LogOut, User } from 'lucide-react';
import { checkHealth } from '../../services/api';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';

interface NavbarProps {
  onLaunchDemo?: () => void;
  isDemoActive?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onLaunchDemo, isDemoActive }) => {
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [checking, setChecking] = useState<boolean>(false);

  const verifyHealth = async () => {
    setChecking(true);
    const healthy = await checkHealth();
    setIsBackendHealthy(healthy);
    setChecking(false);
  };

  useEffect(() => {
    verifyHealth();
    const interval = setInterval(verifyHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="w-full bg-surface border-b border-border px-4 lg:px-8 py-3 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-md bg-canvas border border-border flex items-center justify-center text-teal-brand shadow-sm">
          <Shield className="w-5 h-5 text-teal-brand" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-text-primary tracking-tight text-base">
              Sentinel<span className="text-teal-brand">Doc</span>
            </span>
            <span className="text-[10px] uppercase font-mono tracking-widest px-1.5 py-0.5 rounded bg-canvas border border-border text-text-muted">
              v1.0-SOC
            </span>
            {isDemoActive && (
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-brand/15 border border-amber-brand/40 text-amber-brand animate-pulse">
                ⚡ DEMO MODE
              </span>
            )}
          </div>
          <p className="text-xs text-text-secondary">
            Personal Data Leak Detector & Compliance Redactor
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {onLaunchDemo && (
          <button
            onClick={onLaunchDemo}
            type="button"
            title="Preload hackathon evaluation dataset and run automated audit"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-teal-brand/10 border border-teal-brand/40 hover:bg-teal-brand hover:text-canvas text-teal-brand transition-all text-xs font-mono font-semibold cursor-pointer shadow-sm"
          >
            <span>⚡ Run Demo Mode</span>
          </button>
        )}

        <a
          href="/presentation.html"
          target="_blank"
          rel="noopener noreferrer"
          title="Open interactive presentation slides"
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-canvas border border-border hover:border-teal-brand text-text-secondary hover:text-teal-brand transition-all text-xs font-mono font-medium cursor-pointer shadow-sm"
        >
          <span>📑 Pitch Deck</span>
        </a>

        <div className="hidden md:flex items-center space-x-2 text-xs font-mono text-text-muted bg-canvas border border-border px-2.5 py-1.5 rounded-md">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-teal-brand animate-pulse" />
          <span>CYBERSECURITY TRACK // IEEE SRM AP</span>
        </div>

        <button
          onClick={verifyHealth}
          title="Click to re-verify backend connectivity"
          className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-canvas border border-border hover:border-border-focus transition-colors text-xs font-mono"
        >
          {checking ? (
            <RefreshCw className="w-3.5 h-3.5 text-amber-brand animate-spin" />
          ) : isBackendHealthy ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-teal-brand" />
          ) : (
            <AlertCircle className="w-3.5 h-3.5 text-crimson-brand" />
          )}
          <span
            className={
              isBackendHealthy === null
                ? 'text-text-muted'
                : isBackendHealthy
                ? 'text-teal-brand font-medium'
                : 'text-crimson-brand font-medium'
            }
          >
            {isBackendHealthy === null
              ? 'CONNECTING...'
              : isBackendHealthy
              ? 'API LIVE (8000)'
              : 'API OFFLINE'}
          </span>
        </button>

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          type="button"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          className="p-1.5 rounded-md bg-canvas border border-border hover:border-teal-brand text-text-secondary hover:text-teal-brand transition-all cursor-pointer shadow-sm"
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-amber-brand" />
          ) : (
            <Moon className="w-4 h-4 text-teal-brand" />
          )}
        </button>

        {/* User Badge & Logout */}
        {user && (
          <div className="flex items-center space-x-2 pl-2 border-l border-border">
            <div className="hidden sm:flex items-center space-x-1.5 text-xs font-mono text-text-primary px-2 py-1 rounded-md bg-canvas border border-border">
              <User className="w-3.5 h-3.5 text-teal-brand" />
              <span className="font-semibold">{user.displayName}</span>
            </div>
            <button
              onClick={logout}
              type="button"
              title="Log out of SOC Console"
              className="flex items-center space-x-1 p-1.5 rounded-md bg-canvas border border-border hover:border-crimson-brand text-text-muted hover:text-crimson-brand transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="text-[11px] font-mono hidden md:inline">Exit</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
