import React, { createContext, useContext, useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { AuthResponse, User } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  isAdmin: boolean;
  isAuditor: boolean;
  isAccountHolder: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    try {
      const res = await apiClient.get<User>('/auth/me');
      setUser(res.data);
      localStorage.setItem('user', JSON.stringify(res.data));
    } catch {
      setUser(null);
      localStorage.removeItem('user');
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('access_token');
      if (savedToken) {
        await refreshUser();
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await apiClient.post<AuthResponse>('/auth/login', { email, password });
    localStorage.setItem('access_token', res.data.access_token);
    localStorage.setItem('refresh_token', res.data.refresh_token);
    setToken(res.data.access_token);

    const userRes = await apiClient.get<User>('/auth/me');
    setUser(userRes.data);
    localStorage.setItem('user', JSON.stringify(userRes.data));
  };

  const register = async (email: string, password: string, fullName: string) => {
    await apiClient.post('/auth/register', {
      email,
      password,
      full_name: fullName,
      role: 'ACCOUNT_HOLDER'
    });
    // Auto-login after registration
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setUser(null);
    setToken(null);
    window.location.href = '/login';
  };

  const isAdmin = user?.role === 'ADMIN';
  const isAuditor = user?.role === 'AUDITOR';
  const isAccountHolder = user?.role === 'ACCOUNT_HOLDER';

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
        isAdmin,
        isAuditor,
        isAccountHolder,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
