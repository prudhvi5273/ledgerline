import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiClient, generateIdempotencyKey } from '../api/client';
import { Account, Transaction } from '../types';
import { Card } from '../components/UI/Card';
import { Button } from '../components/UI/Button';
import { ConfirmDialog } from '../components/UI/ConfirmDialog';
import { Header } from '../components/Layout/Header';
import { ErrorBanner } from '../components/Feedback/ErrorBanner';
import { LoadingSpinner } from '../components/Feedback/LoadingSpinner';
import { formatCurrency, formatDate } from '../utils/currency';
import { ArrowDownRight, CheckCircle, ShieldCheck } from 'lucide-react';

export const Deposit: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialAcc = searchParams.get('account') || '';

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState(initialAcc);
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('External deposit');
  const [idempotencyKey, setIdempotencyKey] = useState(generateIdempotencyKey());

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [successTx, setSuccessTx] = useState<Transaction | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    const fetchAccounts = async () => {
      setIsLoading(true);
      try {
        const res = await apiClient.get<Account[]>('/accounts');
        setAccounts(res.data);
        if (!accountId && res.data.length > 0) {
          setAccountId(res.data[0].id);
        }
      } catch (err: any) {
        setError('Failed to load accounts.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchAccounts();
  }, []);

  const selectedAccount = accounts.find((a) => a.id === accountId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError('Deposit amount must be strictly positive.');
      return;
    }
    setShowConfirm(true);
  };

  const handleExecute = async () => {
    setIsSubmitting(true);
    setShowConfirm(false);
    setError('');

    try {
      const res = await apiClient.post<Transaction>(
        '/transactions/deposit',
        {
          account_id: accountId,
          amount: parseFloat(amount).toFixed(4),
          description: description || 'External deposit'
        },
        {
          headers: {
            'Idempotency-Key': idempotencyKey
          }
        }
      );
      setSuccessTx(res.data);
      // Refresh account list
      const accRes = await apiClient.get<Account[]>('/accounts');
      setAccounts(accRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Deposit failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) return <LoadingSpinner message="Loading account balances..." />;

  return (
    <div className="flex-1 min-h-screen bg-slate-950 pb-16">
      <Header
        title="Deposit Funds"
        subtitle="Simulate external inflow with double-entry clearing account balancing"
      />

      <main className="max-w-2xl mx-auto px-6 pt-6 space-y-6">
        <ErrorBanner message={error} onDismiss={() => setError('')} />

        {successTx ? (
          <Card className="border-emerald-500/40 bg-slate-900">
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-800">
              <div className="h-10 w-10 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <CheckCircle size={22} />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Deposit Confirmed</h3>
                <p className="text-xs text-slate-400 font-mono">Reference: {successTx.reference_id}</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 mb-6 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">Credited Amount:</span>
                <span className="text-xl font-bold font-mono text-emerald-400">
                  {formatCurrency(successTx.total_amount, successTx.currency)}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs pt-2 border-t border-slate-800/60">
                <span className="text-slate-400">System Clearing Debited:</span>
                <span className="font-mono text-slate-300">SYSTEM_CLEARING</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">Timestamp:</span>
                <span className="text-slate-300">{formatDate(successTx.created_at)}</span>
              </div>
            </div>

            <Button
              variant="primary"
              className="w-full"
              onClick={() => {
                setSuccessTx(null);
                setAmount('');
                setIdempotencyKey(generateIdempotencyKey());
              }}
            >
              Deposit Again
            </Button>
          </Card>
        ) : (
          <form onSubmit={handleSubmit}>
            <Card title="External Deposit Form" subtitle="Inflow credited to your settlement account">
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Target Account
                  </label>
                  <select
                    value={accountId}
                    onChange={(e) => setAccountId(e.target.value)}
                    required
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                  >
                    {accounts.map((acc) => (
                      <option key={acc.id} value={acc.id}>
                        {acc.account_number} ({acc.currency}) — Balance: {formatCurrency(acc.balance, acc.currency)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Deposit Amount ({selectedAccount?.currency || 'INR'})
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="0.00"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 font-mono text-base focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Description
                  </label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g. Salary deposit"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                  />
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <ShieldCheck size={14} className="text-emerald-400" />
                    Idempotency Key:
                  </span>
                  <span className="font-mono text-[11px] text-slate-300 truncate max-w-[200px]">
                    {idempotencyKey}
                  </span>
                </div>

                <Button type="submit" variant="primary" className="w-full gap-2 py-3" isLoading={isSubmitting}>
                  <ArrowDownRight size={16} /> Execute Deposit
                </Button>
              </div>
            </Card>
          </form>
        )}

        <ConfirmDialog
          isOpen={showConfirm}
          onClose={() => setShowConfirm(false)}
          onConfirm={handleExecute}
          title="Confirm Deposit"
          message={`Are you sure you want to deposit ${formatCurrency(amount, selectedAccount?.currency || 'INR')} into account ${selectedAccount?.account_number}?`}
          confirmText="Confirm Deposit"
          isLoading={isSubmitting}
        />
      </main>
    </div>
  );
};
