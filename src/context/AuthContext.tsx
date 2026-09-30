import React, { createContext, useContext, useState } from 'react';

interface User {
  username: string;
  displayName: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  login: (username: string, password: string) => boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const VALID_CREDENTIALS = [
  { username: 'admin', password: 'sentinel2026', displayName: 'Admin' },
  { username: 'judge', password: 'ieee2026', displayName: 'Judge' },
  { username: 'helium', password: 'helium123', displayName: 'Team Helium' },
];

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const stored = sessionStorage.getItem('sentineldoc-user');
    if (stored) {
      try { return JSON.parse(stored); } catch { return null; }
    }
    return null;
  });

  const isAuthenticated = user !== null;

  const login = (username: string, password: string): boolean => {
    const match = VALID_CREDENTIALS.find(
      (c) => c.username.toLowerCase() === username.toLowerCase() && c.password === password
    );
    if (match) {
      const u: User = { username: match.username, displayName: match.displayName };
      setUser(u);
      sessionStorage.setItem('sentineldoc-user', JSON.stringify(u));
      return true;
    }
    return false;
  };

  const logout = () => {
    setUser(null);
    sessionStorage.removeItem('sentineldoc-user');
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
