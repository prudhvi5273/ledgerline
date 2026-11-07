import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/UI/Button';
import { ErrorBanner } from '../components/Feedback/ErrorBanner';
import { Lock, Mail, ArrowRight, ShieldCheck, Scale, User as UserIcon } from 'lucide-react';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const fillDemo = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="mx-auto h-12 w-12 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-xl shadow-emerald-500/20 text-white font-black text-xl mb-3">
          L
        </div>
        <h2 className="text-2xl font-black tracking-tight text-white">
          Sign in to LedgerLine
        </h2>
        <p className="mt-1 text-xs text-slate-400">
          Verifiable money movement powered by an immutable double-entry ledger
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-slate-900 border border-slate-800 py-8 px-6 shadow-xl rounded-2xl sm:px-10">
          <ErrorBanner message={error} onDismiss={() => setError('')} />

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Mail size={16} />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="block w-full pl-10 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock size={16} />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="block w-full pl-10 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500"
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full mt-2"
              isLoading={isLoading}
            >
              Sign In <ArrowRight size={16} className="ml-1.5" />
            </Button>
          </form>

          {/* Quick Demo Credentials */}
          <div className="mt-6 pt-5 border-t border-slate-800">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 text-center">
              Quick Demo Accounts
            </p>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => fillDemo('client.alice@example.com', 'SecretPassword123!')}
                className="p-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-left transition-colors"
              >
                <div className="flex items-center gap-1 text-[11px] font-bold text-emerald-400">
                  <UserIcon size={12} /> Client
                </div>
                <p className="text-[10px] text-slate-400 truncate">Alice Smith</p>
              </button>

              <button
                type="button"
                onClick={() => fillDemo('admin.root@example.com', 'AdminMasterPass123!')}
                className="p-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-left transition-colors"
              >
                <div className="flex items-center gap-1 text-[11px] font-bold text-purple-400">
                  <ShieldCheck size={12} /> Admin
                </div>
                <p className="text-[10px] text-slate-400 truncate">System Chief</p>
              </button>

              <button
                type="button"
                onClick={() => fillDemo('auditor.check@example.com', 'AuditorPass123!')}
                className="p-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-left transition-colors"
              >
                <div className="flex items-center gap-1 text-[11px] font-bold text-amber-400">
                  <Scale size={12} /> Auditor
                </div>
                <p className="text-[10px] text-slate-400 truncate">Read-Only</p>
              </button>
            </div>
          </div>

          <div className="mt-5 text-center text-xs text-slate-400">
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold text-emerald-400 hover:text-emerald-300">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
