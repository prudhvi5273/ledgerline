import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/UI/Card';
import { Badge } from '../components/UI/Badge';
import { Header } from '../components/Layout/Header';
import { formatDate } from '../utils/currency';
import { User, Mail, Shield, Calendar, KeyRound } from 'lucide-react';

export const Profile: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="flex-1 min-h-screen bg-slate-950 pb-16">
      <Header title="User Profile & Security" subtitle="Manage your identity and inspect security attributes" />

      <main className="max-w-3xl mx-auto px-6 pt-6 space-y-6">
        <Card title="Account Information">
          <div className="space-y-4 text-xs">
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
              <div className="flex items-center gap-2.5 text-slate-400">
                <User size={16} className="text-emerald-400" />
                <span>Full Name</span>
              </div>
              <span className="font-bold text-slate-100">{user?.full_name}</span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
              <div className="flex items-center gap-2.5 text-slate-400">
                <Mail size={16} className="text-emerald-400" />
                <span>Email Address</span>
              </div>
              <span className="font-mono text-slate-200">{user?.email}</span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
              <div className="flex items-center gap-2.5 text-slate-400">
                <Shield size={16} className="text-purple-400" />
                <span>Role & Permissions</span>
              </div>
              <Badge variant={user?.role === 'ADMIN' ? 'danger' : user?.role === 'AUDITOR' ? 'warning' : 'success'}>
                {user?.role}
              </Badge>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
              <div className="flex items-center gap-2.5 text-slate-400">
                <Calendar size={16} className="text-cyan-400" />
                <span>Member Since</span>
              </div>
              <span className="text-slate-300">{user ? formatDate(user.created_at) : '-'}</span>
            </div>
          </div>
        </Card>

        <Card title="Security & Cryptographic Standards">
          <div className="space-y-2 text-xs text-slate-400">
            <p className="flex items-center gap-2">
              <KeyRound size={14} className="text-emerald-400" />
              Passwords hashed using adaptive <strong>Bcrypt / Argon2</strong> algorithm.
            </p>
            <p className="flex items-center gap-2">
              <KeyRound size={14} className="text-emerald-400" />
              API requests authenticated using signed <strong>JSON Web Tokens (JWT)</strong> with short-lived expiration.
            </p>
            <p className="flex items-center gap-2">
              <KeyRound size={14} className="text-emerald-400" />
              All money movements enforce <strong>RFC-4122 Idempotency Keys</strong>.
            </p>
          </div>
        </Card>
      </main>
    </div>
  );
};
