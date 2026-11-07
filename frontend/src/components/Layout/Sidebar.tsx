import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Wallet,
  ArrowLeftRight,
  ArrowDownToLine,
  ArrowUpFromLine,
  History,
  FileSpreadsheet,
  ShieldCheck,
  Scale,
  UserCheck,
  LogOut
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { user, logout, isAdmin, isAuditor } = useAuth();

  const navItemClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
        : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
    }`;

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-screen fixed left-0 top-0 z-30">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800 flex items-center gap-3">
        <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white font-bold text-lg">
          L
        </div>
        <div>
          <h1 className="font-extrabold text-white text-base tracking-tight flex items-center gap-1.5">
            LedgerLine
            <span className="text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold px-1.5 py-0.5 rounded border border-emerald-500/30">
              v1.0
            </span>
          </h1>
          <p className="text-[11px] text-slate-400">Verifiable Financial Ledger</p>
        </div>
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 p-3 space-y-6 overflow-y-auto">
        {/* Core Banking */}
        <div>
          <p className="text-[11px] font-bold text-slate-300 uppercase tracking-wider px-3 mb-2">
            Banking Core
          </p>
          <div className="space-y-1">
            <NavLink to="/" end className={navItemClass}>
              <LayoutDashboard size={18} />
              Dashboard
            </NavLink>
            <NavLink to="/accounts" className={navItemClass}>
              <Wallet size={18} />
              My Accounts
            </NavLink>
            <NavLink to="/transfers" className={navItemClass}>
              <ArrowLeftRight size={18} />
              Transfer Money
            </NavLink>
            <NavLink to="/deposit" className={navItemClass}>
              <ArrowDownToLine size={18} />
              Deposit
            </NavLink>
            <NavLink to="/withdraw" className={navItemClass}>
              <ArrowUpFromLine size={18} />
              Withdraw
            </NavLink>
          </div>
        </div>

        {/* Ledger & Statements */}
        <div>
          <p className="text-[11px] font-bold text-slate-300 uppercase tracking-wider px-3 mb-2">
            Ledger & Records
          </p>
          <div className="space-y-1">
            <NavLink to="/transactions" className={navItemClass}>
              <History size={18} />
              Transaction History
            </NavLink>
            <NavLink to="/statements" className={navItemClass}>
              <FileSpreadsheet size={18} />
              Account Statements
            </NavLink>
          </div>
        </div>

        {/* Role Specific Portals */}
        {(isAdmin || isAuditor) && (
          <div>
            <p className="text-[11px] font-bold text-slate-300 uppercase tracking-wider px-3 mb-2">
              Compliance & Security
            </p>
            <div className="space-y-1">
              {isAdmin && (
                <NavLink to="/admin" className={navItemClass}>
                  <ShieldCheck size={18} className="text-purple-400" />
                  Admin Portal
                </NavLink>
              )}
              <NavLink to="/auditor" className={navItemClass}>
                <Scale size={18} className="text-amber-400" />
                Auditor Portal
              </NavLink>
            </div>
          </div>
        )}
      </nav>

      {/* User Footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-900/50">
        <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="h-8 w-8 rounded-lg bg-slate-700 flex items-center justify-center text-xs font-semibold text-slate-200">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-medium text-slate-200 truncate">{user?.full_name}</p>
              <p className="text-[10px] text-slate-300 font-mono truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Sign Out"
            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-md transition-colors"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
};
