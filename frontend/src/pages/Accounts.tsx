import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Account } from '../types';
import { Card } from '../components/UI/Card';
import { Button } from '../components/UI/Button';
import { Badge } from '../components/UI/Badge';
import { Modal } from '../components/UI/Modal';
import { Header } from '../components/Layout/Header';
import { LoadingSpinner } from '../components/Feedback/LoadingSpinner';
import { ErrorBanner } from '../components/Feedback/ErrorBanner';
import { formatCurrency, formatDate } from '../utils/currency';
import { Wallet, PlusCircle, ArrowUpRight, ArrowDownRight, ArrowLeftRight, FileSpreadsheet, Lock } from 'lucide-react';

export const Accounts: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currency, setCurrency] = useState('INR');
  const [accountType, setAccountType] = useState('USER_CHECKING');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchAccounts = async () => {
    setIsLoading(true);
    try {
      const res = await apiClient.get<Account[]>('/accounts');
      setAccounts(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch accounts.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    try {
      await apiClient.post('/accounts', {
        currency,
        account_type: accountType
      });
      setIsModalOpen(false);
      await fetchAccounts();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to open account.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading account balances..." />;
  }

  return (
    <div className="flex-1 min-h-screen bg-slate-950 pb-16">
      <Header
        title="Settlement Accounts"
        subtitle="Manage your segregated accounts and inspect real-time ledger balances"
      />

      <main className="max-w-7xl mx-auto px-6 pt-6 space-y-6">
        <ErrorBanner message={error} onDismiss={() => setError('')} />

        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-400">
            Showing <span className="font-semibold text-slate-200">{accounts.length}</span> active account(s)
          </p>
          <Button
            size="sm"
            onClick={() => setIsModalOpen(true)}
            className="gap-1.5"
          >
            <PlusCircle size={15} /> Open New Account
          </Button>
        </div>

        {/* Accounts Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {accounts.map((acc) => (
            <Card
              key={acc.id}
              className="relative overflow-hidden flex flex-col justify-between hover:border-slate-700 transition-all group"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-mono font-medium text-slate-400 tracking-wider">
                    {acc.account_type.replace('_', ' ')}
                  </span>
                  <Badge
                    variant={acc.status === 'ACTIVE' ? 'success' : acc.status === 'FROZEN' ? 'warning' : 'danger'}
                  >
                    {acc.status}
                  </Badge>
                </div>

                <div className="space-y-1 mb-4">
                  <p className="text-xs text-slate-400">Available Balance</p>
                  <p className="text-2xl font-black text-white font-mono tracking-tight">
                    {formatCurrency(acc.balance, acc.currency)}
                  </p>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 mb-5">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">Account No:</span>
                    <span className="font-bold text-slate-200">{acc.account_number}</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                    <span>Currency:</span>
                    <span className="font-semibold text-emerald-400">{acc.currency}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-800/80 text-xs">
                <Link
                  to={`/transfers?source=${acc.id}`}
                  className="flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                >
                  <ArrowLeftRight size={13} /> Transfer
                </Link>
                <Link
                  to={`/deposit?account=${acc.id}`}
                  className="flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                >
                  <ArrowDownRight size={13} /> Deposit
                </Link>
                <Link
                  to={`/statements?account=${acc.id}`}
                  className="flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                >
                  <FileSpreadsheet size={13} /> Statement
                </Link>
              </div>
            </Card>
          ))}
        </div>

        {/* Account Provisioning Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="Open New Settlement Account"
        >
          <form onSubmit={handleCreateAccount} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Currency
              </label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
              >
                <option value="INR">INR - Indian Rupee (₹)</option>
                <option value="USD">USD - US Dollar ($)</option>
                <option value="EUR">EUR - Euro (€)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Account Type
              </label>
              <select
                value={accountType}
                onChange={(e) => setAccountType(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
              >
                <option value="USER_CHECKING">Standard Checking Account</option>
                <option value="USER_SAVINGS">Savings Account</option>
              </select>
            </div>

            <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 text-xs text-slate-400">
              New accounts start with a balance of ₹0.0000 and are assigned a verified 12-digit account number with database-level non-negative balance checks.
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                variant="primary"
                isLoading={isSubmitting}
              >
                Create Account
              </Button>
            </div>
          </form>
        </Modal>
      </main>
    </div>
  );
};
