import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Account, AuditLog, User } from '../types';
import { Card } from '../components/UI/Card';
import { Button } from '../components/UI/Button';
import { Badge } from '../components/UI/Badge';
import { Modal } from '../components/UI/Modal';
import { Header } from '../components/Layout/Header';
import { LoadingSpinner } from '../components/Feedback/LoadingSpinner';
import { ErrorBanner } from '../components/Feedback/ErrorBanner';
import { formatCurrency, formatDate } from '../utils/currency';
import {
  ShieldCheck,
  Users,
  Wallet,
  Lock,
  Unlock,
  UserPlus,
  ShieldAlert,
  Search
} from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [activeTab, setActiveTab] = useState<'users' | 'accounts' | 'audit'>('accounts');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Freeze / Unfreeze Modal
  const [selectedAcc, setSelectedAcc] = useState<Account | null>(null);
  const [statusTarget, setStatusTarget] = useState<'ACTIVE' | 'FROZEN' | 'CLOSED'>('FROZEN');
  const [isStatusSubmitting, setIsStatusSubmitting] = useState(false);

  // User Provisioning Modal
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newRole, setNewRole] = useState<'ADMIN' | 'AUDITOR' | 'ACCOUNT_HOLDER'>('AUDITOR');
  const [isUserSubmitting, setIsUserSubmitting] = useState(false);

  const loadAdminData = async () => {
    setIsLoading(true);
    try {
      const [uRes, aRes, logRes] = await Promise.all([
        apiClient.get<User[]>('/admin/users'),
        apiClient.get<Account[]>('/admin/accounts'),
        apiClient.get<AuditLog[]>('/admin/audit-logs?limit=50')
      ]);
      setUsers(uRes.data);
      setAccounts(aRes.data);
      setAuditLogs(logRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load administrator records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const handleUpdateStatus = async () => {
    if (!selectedAcc) return;
    setIsStatusSubmitting(true);
    setError('');
    try {
      await apiClient.patch(`/admin/accounts/${selectedAcc.id}/status`, {
        status: statusTarget
      });
      setSelectedAcc(null);
      await loadAdminData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update account status.');
    } finally {
      setIsStatusSubmitting(false);
    }
  };

  const handleProvisionUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUserSubmitting(true);
    setError('');
    try {
      await apiClient.post('/admin/users', {
        email: newEmail,
        password: newPassword,
        full_name: newFullName,
        role: newRole
      });
      setIsUserModalOpen(false);
      setNewEmail('');
      setNewPassword('');
      setNewFullName('');
      await loadAdminData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to provision user.');
    } finally {
      setIsUserSubmitting(false);
    }
  };

  if (isLoading) return <LoadingSpinner message="Fetching administrative control parameters..." />;

  return (
    <div className="flex-1 min-h-screen bg-slate-950 pb-16">
      <Header
        title="Administrator Portal"
        subtitle="Privilege management, account freeze controls, and compliance oversight"
      />

      <main className="max-w-7xl mx-auto px-6 pt-6 space-y-6">
        <ErrorBanner message={error} onDismiss={() => setError('')} />

        {/* Top Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400">Total Registered Users</span>
              <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
                <Users size={18} />
              </div>
            </div>
            <p className="text-2xl font-black text-white">{users.length}</p>
            <p className="text-[11px] text-slate-400 mt-1">Role-Based Access Guarded</p>
          </Card>

          <Card>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400">Platform Accounts</span>
              <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <Wallet size={18} />
              </div>
            </div>
            <p className="text-2xl font-black text-white">{accounts.length}</p>
            <p className="text-[11px] text-slate-400 mt-1">Active ledger participants</p>
          </Card>

          <Card>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400">Security Audit Logs</span>
              <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ShieldCheck size={18} />
              </div>
            </div>
            <p className="text-2xl font-black text-white">{auditLogs.length}</p>
            <p className="text-[11px] text-slate-400 mt-1">Append-only log records</p>
          </Card>
        </div>

        {/* Tab Switcher & Action */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('accounts')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                activeTab === 'accounts' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Account Controls
            </button>
            <button
              onClick={() => setActiveTab('users')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                activeTab === 'users' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              User Directory
            </button>
            <button
              onClick={() => setActiveTab('audit')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                activeTab === 'audit' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Audit Trail
            </button>
          </div>

          <Button size="sm" variant="primary" onClick={() => setIsUserModalOpen(true)} className="gap-1.5">
            <UserPlus size={15} /> Provision Privileged User
          </Button>
        </div>

        {/* Tab 1: Account Controls */}
        {activeTab === 'accounts' && (
          <Card title="System Accounts & Freeze Controls">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase">
                    <th className="pb-3 pl-2">Account Number</th>
                    <th className="pb-3">Type</th>
                    <th className="pb-3">Balance</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3">Owner User ID</th>
                    <th className="pb-3 pr-2 text-right">Administrative Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {accounts.map((acc) => (
                    <tr key={acc.id} className="hover:bg-slate-800/30">
                      <td className="py-3 pl-2 font-bold text-slate-200">{acc.account_number}</td>
                      <td className="py-3 font-sans text-slate-400">{acc.account_type}</td>
                      <td className="py-3 font-bold text-emerald-400">
                        {formatCurrency(acc.balance, acc.currency)}
                      </td>
                      <td className="py-3">
                        <Badge
                          variant={acc.status === 'ACTIVE' ? 'success' : acc.status === 'FROZEN' ? 'warning' : 'danger'}
                        >
                          {acc.status}
                        </Badge>
                      </td>
                      <td className="py-3 text-slate-400 text-[11px] truncate max-w-[150px]">
                        {acc.user_id}
                      </td>
                      <td className="py-3 pr-2 text-right">
                        {acc.account_type !== 'SYSTEM_CLEARING' && (
                          <button
                            onClick={() => {
                              setSelectedAcc(acc);
                              setStatusTarget(acc.status === 'ACTIVE' ? 'FROZEN' : 'ACTIVE');
                            }}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs transition-colors"
                          >
                            {acc.status === 'ACTIVE' ? (
                              <>
                                <Lock size={12} className="text-amber-400" /> Freeze
                              </>
                            ) : (
                              <>
                                <Unlock size={12} className="text-emerald-400" /> Unfreeze
                              </>
                            )}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* Tab 2: User Directory */}
        {activeTab === 'users' && (
          <Card title="Registered Users">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase">
                    <th className="pb-3 pl-2">Full Name</th>
                    <th className="pb-3">Email Address</th>
                    <th className="pb-3">Assigned Role</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 pr-2 text-right">Created Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-800/30">
                      <td className="py-3 pl-2 font-bold text-slate-200 font-sans">{u.full_name}</td>
                      <td className="py-3 text-slate-300">{u.email}</td>
                      <td className="py-3">
                        <Badge
                          variant={u.role === 'ADMIN' ? 'danger' : u.role === 'AUDITOR' ? 'warning' : 'success'}
                        >
                          {u.role}
                        </Badge>
                      </td>
                      <td className="py-3">
                        <span className="text-emerald-400 font-semibold">{u.is_active ? 'ACTIVE' : 'SUSPENDED'}</span>
                      </td>
                      <td className="py-3 pr-2 text-right text-slate-400 text-[11px]">
                        {formatDate(u.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* Tab 3: System Audit Logs */}
        {activeTab === 'audit' && (
          <Card title="Security & Refusal Audit Events">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase">
                    <th className="pb-3 pl-2">Event Type</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3">Refusal Reason</th>
                    <th className="pb-3">Amount</th>
                    <th className="pb-3 pr-2 text-right">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-800/30">
                      <td className="py-3 pl-2 font-bold text-purple-300">{log.event_type}</td>
                      <td className="py-3">
                        <Badge variant={log.status === 'SUCCESS' ? 'success' : 'danger'}>
                          {log.status}
                        </Badge>
                      </td>
                      <td className="py-3 text-rose-400">{log.refusal_reason || '-'}</td>
                      <td className="py-3 text-slate-300">
                        {log.amount ? formatCurrency(log.amount, 'INR') : '-'}
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
        )}

        {/* Account Status Modal */}
        <Modal
          isOpen={!!selectedAcc}
          onClose={() => setSelectedAcc(null)}
          title="Update Account Operational Status"
        >
          {selectedAcc && (
            <div className="space-y-4">
              <p className="text-xs text-slate-300">
                You are updating the status of account <strong>{selectedAcc.account_number}</strong>.
              </p>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Select New Status:
                </label>
                <select
                  value={statusTarget}
                  onChange={(e: any) => setStatusTarget(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                >
                  <option value="ACTIVE">ACTIVE (Normal Operations Allowed)</option>
                  <option value="FROZEN">FROZEN (Money Movements Blocked)</option>
                  <option value="CLOSED">CLOSED (Account Permanently Decommissioned)</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <Button variant="outline" size="sm" onClick={() => setSelectedAcc(null)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleUpdateStatus}
                  isLoading={isStatusSubmitting}
                >
                  Save Status
                </Button>
              </div>
            </div>
          )}
        </Modal>

        {/* User Provisioning Modal */}
        <Modal
          isOpen={isUserModalOpen}
          onClose={() => setIsUserModalOpen(false)}
          title="Provision Privileged User"
        >
          <form onSubmit={handleProvisionUser} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
              <input
                type="text"
                required
                value={newFullName}
                onChange={(e) => setNewFullName(e.target.value)}
                placeholder="e.g. Audit Lead"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Email</label>
              <input
                type="email"
                required
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="auditor@ledgerline.internal"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Role</label>
              <select
                value={newRole}
                onChange={(e: any) => setNewRole(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              >
                <option value="AUDITOR">AUDITOR (Read-Only Financial Examiner)</option>
                <option value="ADMIN">ADMINISTRATOR (Full Platform Admin)</option>
                <option value="ACCOUNT_HOLDER">ACCOUNT_HOLDER (Standard Client)</option>
              </select>
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsUserModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" isLoading={isUserSubmitting}>
                Provision User
              </Button>
            </div>
          </form>
        </Modal>
      </main>
    </div>
  );
};
