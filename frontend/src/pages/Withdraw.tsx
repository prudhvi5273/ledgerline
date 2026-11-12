import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiClient, generateIdempotencyKey } from '../api/client';
import { Account, Transaction } from '../types';
import { Card } from '../components/UI/Card';
import { Button } from '../components/UI/Button';
import { ConfirmDialog } from '../components/UI/ConfirmDialog';
import { Header } from '../components/Layout/Header';
import { ErrorBanner } from '../components/Feedback/ErrorBanner';
import { LoadingSpinner } from '../components/Feedback/LoadingSpinner';
import { formatCurrency, formatDate } from '../utils/currency';
import { ArrowUpRight, CheckCircle, ShieldCheck, AlertTriangle } from 'lucide-react';

export const Withdraw: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialAcc = searchParams.get('account') || '';

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState(initialAcc);
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('External withdrawal');
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
      setError('Withdrawal amount must be strictly positive.');
      return;
    }
    if (selectedAccount && numAmount > parseFloat(selectedAccount.balance)) {
      setError(`Cannot withdraw. Available balance is ${formatCurrency(selectedAccount.balance, selectedAccount.currency)}.`);
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
        '/transactions/withdraw',
        {
          account_id: accountId,
          amount: parseFloat(amount).toFixed(4),
          description: description || 'External withdrawal'
        },
        {
          headers: {
            'Idempotency-Key': idempotencyKey
          }
        }
      );
      setSuccessTx(res.data);
      const accRes = await apiClient.get<Account[]>('/accounts');
      setAccounts(accRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Withdrawal failed. Insufficient funds or account locked.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) return <LoadingSpinner message="Loading account balances..." />;

  return (
    <div className="flex-1 min-h-screen bg-slate-950 pb-16">
      <Header
        title="Withdraw Funds"
        subtitle="Debit account balance with row-level overdraft protection"
      />

      <main className="max-w-2xl mx-auto px-6 pt-6 space-y-6">
        <ErrorBanner message={error} onDismiss={() => setError('')} />

        {successTx ? (
          <Card className="border-rose-500/40 bg-slate-900">
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-800">
              <div className="h-10 w-10 rounded-full bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400">
                <CheckCircle size={22} />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Withdrawal Dispatched</h3>
                <p className="text-xs text-slate-400 font-mono">Reference: {successTx.reference_id}</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 mb-6 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">Debited Amount:</span>
                <span className="text-xl font-bold font-mono text-rose-400">
                  {formatCurrency(successTx.total_amount, successTx.currency)}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs pt-2 border-t border-slate-800/60">
                <span className="text-slate-400">Double-Entry Balancing:</span>
                <span className="font-mono text-slate-300">Credited to SYSTEM_CLEARING</span>
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
              Withdraw Again
            </Button>
          </Card>
        ) : (
          <form onSubmit={handleSubmit}>
            <Card title="Withdrawal Request" subtitle="Deducts funds subject to balance check">
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <label className="text-xs font-semibold text-slate-300">From Account</label>
                    {selectedAccount && (
                      <span className="text-xs font-mono text-emerald-400">
                        Available: {formatCurrency(selectedAccount.balance, selectedAccount.currency)}
                      </span>
                    )}
                  </div>
                  {accounts.length === 0 ? (
                    <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300 text-xs">
                      No accounts found. Please go to <Link to="/accounts" className="underline font-bold text-amber-200">My Accounts</Link> to create or view your account.
                    </div>
                  ) : (
                    <select
                      value={accountId}
                      onChange={(e) => setAccountId(e.target.value)}
                      required
                      className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                    >
                      {accounts.map((acc) => (
                        <option key={acc.id} value={acc.id} disabled={acc.status !== 'ACTIVE'}>
                          {acc.account_number} ({acc.currency}) — Balance: {formatCurrency(acc.balance, acc.currency)} {acc.status !== 'ACTIVE' ? `[${acc.status}]` : ''}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Withdrawal Amount ({selectedAccount?.currency || 'INR'})
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
                    placeholder="e.g. ATM withdrawal"
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

                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 flex items-start gap-2">
                  <AlertTriangle size={15} className="shrink-0 mt-0.5 text-amber-400" />
                  <span>The backend acquires a row lock (<code>SELECT FOR UPDATE</code>) on this account. Simultaneous withdrawal attempts exceeding available funds will be rejected.</span>
                </div>

                <Button type="submit" variant="danger" className="w-full gap-2 py-3" isLoading={isSubmitting}>
                  <ArrowUpRight size={16} /> Execute Withdrawal
                </Button>
              </div>
            </Card>
          </form>
        )}

        <ConfirmDialog
          isOpen={showConfirm}
          onClose={() => setShowConfirm(false)}
          onConfirm={handleExecute}
          title="Confirm Withdrawal"
          message={`Are you sure you want to withdraw ${formatCurrency(amount, selectedAccount?.currency || 'INR')} from account ${selectedAccount?.account_number}?`}
          confirmText="Confirm Withdrawal"
          variant="danger"
          isLoading={isSubmitting}
        />
      </main>
    </div>
  );
};
