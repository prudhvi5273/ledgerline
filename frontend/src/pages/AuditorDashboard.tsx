import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { AuditLog, ReconciliationReport, Transaction } from '../types';
import { Card } from '../components/UI/Card';
import { Button } from '../components/UI/Button';
import { Badge } from '../components/UI/Badge';
import { Header } from '../components/Layout/Header';
import { LoadingSpinner } from '../components/Feedback/LoadingSpinner';
import { formatCurrency, formatDate } from '../utils/currency';
import {
  Scale,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileCheck2,
  ShieldCheck,
  Search,
  Lock
} from 'lucide-react';

export const AuditorDashboard: React.FC = () => {
  const [report, setReport] = useState<ReconciliationReport | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterRefusal, setFilterRefusal] = useState(false);

  const fetchAuditData = async () => {
    setIsLoading(true);
    try {
      const [reconRes, logRes, txRes] = await Promise.all([
        apiClient.get<ReconciliationReport>('/auditor/reconciliation'),
        apiClient.get<AuditLog[]>('/auditor/audit-logs?limit=50'),
        apiClient.get<Transaction[]>('/transactions?limit=20')
      ]);
      setReport(reconRes.data);
      setAuditLogs(logRes.data);
      setTransactions(txRes.data);
    } catch (err) {
      console.error('Failed to load auditor data', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditData();
  }, []);

  const displayedLogs = filterRefusal
    ? auditLogs.filter((l) => l.status === 'REFUSED')
    : auditLogs;

  if (isLoading && !report) {
    return <LoadingSpinner message="Executing global double-entry reconciliation across all accounts..." />;
  }

  return (
    <div className="flex-1 min-h-screen bg-slate-950 pb-16">
      <Header
        title="Auditor Reconciliation Portal"
        subtitle="Independent read-only verification of ledger equilibrium and financial conservation"
      />

      <main className="max-w-7xl mx-auto px-6 pt-6 space-y-6">
        {/* Read-Only Notice */}
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
          <div className="flex items-center gap-2.5">
            <Lock size={16} className="text-amber-400 shrink-0" />
            <span className="font-medium">
              Auditor session active: Server-side RBAC dependencies prevent modifying, creating, or deleting accounts, transfers, or entries.
            </span>
          </div>
          <Button size="sm" variant="outline" onClick={fetchAuditData} className="gap-1.5 text-xs py-1">
            <RefreshCw size={13} /> Re-Verify Ledger
          </Button>
        </div>

        {/* Real-Time Double-Entry Reconciliation Card */}
        {report && (
          <Card
            className={`border ${
              report.is_balanced ? 'border-emerald-500/40 bg-slate-900' : 'border-rose-500/40 bg-rose-950/20'
            }`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 mb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div
                  className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                    report.is_balanced
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                      : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                  }`}
                >
                  {report.is_balanced ? <CheckCircle2 size={24} /> : <AlertTriangle size={24} />}
                </div>
                <div>
                  <h3 className="text-base font-black text-white flex items-center gap-2">
                    Ledger Double-Entry Equilibrium:{' '}
                    <span className={report.is_balanced ? 'text-emerald-400' : 'text-rose-400'}>
                      {report.is_balanced ? 'PROVEN & BALANCED' : 'IMBALANCE DETECTED'}
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Reconciled at: {formatDate(report.checked_at)} across {report.total_accounts} accounts
                  </p>
                </div>
              </div>

              <div className="text-right">
                <span className="text-xs text-slate-400">Discrepancy (Debits - Credits)</span>
                <p
                  className={`text-2xl font-black font-mono ${
                    report.is_balanced ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  ₹{parseFloat(report.discrepancy).toFixed(4)}
                </p>
              </div>
            </div>

            {/* Reconciliation Breakdown Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-[11px] text-slate-400 font-sans">Total Ledger Debits</span>
                <p className="text-base font-bold text-rose-400 mt-0.5">
                  ₹{parseFloat(report.total_ledger_debits).toFixed(4)}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-[11px] text-slate-400 font-sans">Total Ledger Credits</span>
                <p className="text-base font-bold text-emerald-400 mt-0.5">
                  ₹{parseFloat(report.total_ledger_credits).toFixed(4)}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-[11px] text-slate-400 font-sans">User Accounts Balance</span>
                <p className="text-base font-bold text-slate-100 mt-0.5">
                  ₹{parseFloat(report.total_user_balance).toFixed(4)}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-[11px] text-slate-400 font-sans">System Clearing Balance</span>
                <p className="text-base font-bold text-amber-400 mt-0.5">
                  ₹{parseFloat(report.system_clearing_balance).toFixed(4)}
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Security & Refusal Audit Events Explorer */}
        <Card
          title="Cryptographic Audit Trail"
          subtitle="Append-only log of successful, failed, and refused financial transactions"
          action={
            <div className="flex items-center gap-2">
              <button
                onClick={() => setFilterRefusal(!filterRefusal)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                  filterRefusal
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                    : 'bg-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                {filterRefusal ? 'Showing Refused Only' : 'Show All Events'}
              </button>
            </div>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase">
                  <th className="pb-3 pl-2">Event</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Refusal Reason</th>
                  <th className="pb-3">Amount</th>
                  <th className="pb-3">Idempotency Key</th>
                  <th className="pb-3 pr-2 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {displayedLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/30">
                    <td className="py-3 pl-2 font-bold text-amber-300">{log.event_type}</td>
                    <td className="py-3">
                      <Badge variant={log.status === 'SUCCESS' ? 'success' : 'danger'}>
                        {log.status}
                      </Badge>
                    </td>
                    <td className="py-3 text-rose-400">{log.refusal_reason || '-'}</td>
                    <td className="py-3 text-slate-300">
                      {log.amount ? formatCurrency(log.amount, 'INR') : '-'}
                    </td>
                    <td className="py-3 text-slate-400 text-[10px] truncate max-w-[120px]">
                      {log.idempotency_key || '-'}
                    </td>
                    <td className="py-3 pr-2 text-right text-slate-400 text-[11px]">
                      {formatDate(log.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </main>
    </div>
  );
};
