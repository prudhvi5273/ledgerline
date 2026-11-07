import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { Shield, Scale, User as UserIcon } from 'lucide-react';

export const Header: React.FC<{ title: string; subtitle?: string }> = ({ title, subtitle }) => {
  const { user } = useAuth();

  const getRoleBadge = () => {
    switch (user?.role) {
      case 'ADMIN':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/30">
            <Shield size={12} /> Administrator
          </span>
        );
      case 'AUDITOR':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <Scale size={12} /> Auditor (Read-Only)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            <UserIcon size={12} /> Account Holder
          </span>
        );
    }
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-20">
      <div>
        <h2 className="text-lg font-bold text-slate-100">{title}</h2>
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-4">
        {getRoleBadge()}
      </div>
    </header>
  );
};
