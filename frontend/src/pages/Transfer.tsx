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
import {
  ArrowLeftRight,
  ShieldCheck,
  RefreshCw,
  CheckCircle,
  Copy,
  AlertCircle
} from 'lucide-react';

export const Transfer: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialSource = searchParams.get('source') || '';

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [allAccounts, setAllAccounts] = useState<Account[]>([]);
  const [sourceAccountId, setSourceAccountId] = useState(initialSource);
  const [destinationAccountId, setDestinationAccountId] = useState('');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [idempotencyKey, setIdempotencyKey] = useState(generateIdempotencyKey());

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [successTx, setSuccessTx] = useState<Transaction | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);

  useEffect(() => {
    const loadAccounts = async () => {
      setIsLoading(true);
      try {
        const [myRes, recRes] = await Promise.all([
          apiClient.get<Account[]>('/accounts'),
          apiClient.get<Account[]>('/accounts/recipients').catch(() => ({ data: [] as Account[] }))
        ]);
        setAccounts(myRes.data);
        if (!sourceAccountId && myRes.data.length > 0) {
          setSourceAccountId(myRes.data[0].id);
        }
        const combined = [...recRes.data, ...myRes.data];
        setAllAccounts(combined);
      } catch (err: any) {
        setError('Failed to load accounts.');
      } finally {
        setIsLoading(false);
      }
    };
    loadAccounts();
  }, []);

  const selectedSource = accounts.find((a) => a.id === sourceAccountId);
  const selectedDest = allAccounts.find((a) => a.id === destinationAccountId);

  const handleInitiate = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessTx(null);

    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError('Amount must be strictly greater than zero.');
      return;
    }
    if (selectedSource && numAmount > parseFloat(selectedSource.balance)) {
      setError(`Insufficient balance. Maximum transferable amount is ${formatCurrency(selectedSource.balance, selectedSource.currency)}.`);
      return;
    }
    if (sourceAccountId === destinationAccountId) {
      setError('Source and destination accounts must be distinct.');
      return;
    }

    setShowConfirm(true);
  };

  const handleExecuteTransfer = async () => {
    setIsSubmitting(true);
    setError('');
    setShowConfirm(false);

    try {
      const res = await apiClient.post<Transaction>(
        '/transactions/transfer',
        {
          source_account_id: sourceAccountId,
          destination_account_id: destinationAccountId,
          amount: parseFloat(amount).toFixed(4),
          description: description || 'Account transfer'
        },
        {
          headers: {
            'Idempotency-Key': idempotencyKey
          }
        }
      );

      setSuccessTx(res.data);
      // Refresh accounts
      const accRes = await apiClient.get<Account[]>('/accounts');
      setAccounts(accRes.data);
      setAllAccounts(accRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Transfer failed. Check balances and retry.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyKey = () => {
    navigator.clipboard.writeText(idempotencyKey);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleResetForNew = () => {
    setSuccessTx(null);
    setAmount('');
    setDescription('');
    setIdempotencyKey(generateIdempotencyKey());
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading account balances for transfer engine..." />;
  }

  return (
    <div className="flex-1 min-h-screen bg-slate-950 pb-16">
      <Header
        title="Double-Entry Money Transfer"
        subtitle="Deterministic row-level locking with atomic debit/credit balance posting"
      />

      <main className="max-w-4xl mx-auto px-6 pt-6 space-y-6">
        <ErrorBanner message={error} onDismiss={() => setError('')} />

        {successTx ? (
          /* Transfer Success Receipt */
          <Card className="border-emerald-500/40 bg-slate-900">
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-800">
              <div className="h-10 w-10 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <CheckCircle size={22} />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Transfer Completed & Committed</h3>
                <p className="text-xs text-slate-400 font-mono">Reference: {successTx.reference_id}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-950 border border-slate-800 mb-6">
              <div>
                <span className="text-xs text-slate-400">Amount Transferred</span>
                <p className="text-2xl font-black text-emerald-400 font-mono mt-0.5">
                  {formatCurrency(successTx.total_amount, successTx.currency)}
                </p>
              </div>
              <div>
                <span className="text-xs text-slate-400">Committed At</span>
                <p className="text-sm font-semibold text-slate-200 mt-1">
                  {formatDate(successTx.created_at)}
                </p>
              </div>
            </div>

            {/* Double-Entry Ledger Lines */}
            <div className="mb-6">
              <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Double-Entry Ledger Postings:
              </p>
              <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden font-mono text-xs">
                {successTx.entries.map((entry) => (
                  <div key={entry.id} className="flex items-center justify-between p-3 bg-slate-900/60">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded font-bold ${entry.entry_type === 'DEBIT' ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30' : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'}`}>
                        {entry.entry_type}
                      </span>
                      <span className="text-slate-300">Account ID: {entry.account_id.slice(0, 8)}...</span>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-slate-100">{formatCurrency(entry.amount, successTx.currency)}</p>
                      <p className="text-[10px] text-slate-400">Resulting Balance: {formatCurrency(entry.balance_after, successTx.currency)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <Button onClick={handleResetForNew} variant="primary" className="flex-1">
                Make Another Transfer
              </Button>
            </div>
          </Card>
        ) : (
          /* Transfer Form */
          <form onSubmit={handleInitiate}>
            <Card title="Initiate Transfer" subtitle="Move funds with strict transactional equilibrium">
              <div className="space-y-5">
                {/* Source Account */}
                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <label className="text-xs font-semibold text-slate-300">From Account (Source)</label>
                    {selectedSource && (
                      <span className="text-xs font-mono text-emerald-400">
                        Available: {formatCurrency(selectedSource.balance, selectedSource.currency)}
                      </span>
                    )}
                  </div>
                  {accounts.length === 0 ? (
                    <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300 text-xs">
                      No accounts found. Please go to <Link to="/accounts" className="underline font-bold text-amber-200">My Accounts</Link> to create or view your account.
                    </div>
                  ) : (
                    <select
                      value={sourceAccountId}
                      onChange={(e) => setSourceAccountId(e.target.value)}
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

                {/* Destination Account */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    To Account (Destination Account ID or Number)
                  </label>
                  <select
                    value={destinationAccountId}
                    onChange={(e) => setDestinationAccountId(e.target.value)}
                    required
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                  >
                    <option value="">Select destination account...</option>
                    {allAccounts
                      .filter((acc) => acc.id !== sourceAccountId)
                      .map((acc) => (
                        <option key={acc.id} value={acc.id} disabled={acc.status !== 'ACTIVE'}>
                          {acc.account_number} ({acc.currency}) {acc.user_id !== selectedSource?.user_id ? '— Peer Account' : '— My Other Account'}
                        </option>
                      ))}
                  </select>
                </div>

                {/* Amount */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Amount ({selectedSource?.currency || 'INR'})
                  </label>
                  <div className="relative">
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
                </div>

                {/* Description */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Description / Transfer Narrative
                  </label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g. Settlement payment"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                  />
                </div>

                {/* Idempotency Key Control */}
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                      <ShieldCheck size={14} className="text-emerald-400" />
                      Idempotency-Key Header
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleCopyKey}
                        className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center gap-1"
                      >
                        <Copy size={11} /> {copiedKey ? 'Copied!' : 'Copy'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setIdempotencyKey(generateIdempotencyKey())}
                        className="text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                      >
                        <RefreshCw size={11} /> Refresh
                      </button>
                    </div>
                  </div>
                  <p className="text-[11px] font-mono text-slate-400 break-all bg-slate-900 p-2 rounded border border-slate-800/80 mt-1">
                    {idempotencyKey}
                  </p>
                  <p className="text-[10px] text-slate-400 mt-1.5">
                    Submitting multiple times with the same key safely replays the transaction result without moving money twice.
                  </p>
                </div>

                <Button type="submit" variant="primary" className="w-full gap-2 py-3" isLoading={isSubmitting}>
                  <ArrowLeftRight size={16} /> Review & Execute Transfer
                </Button>
              </div>
            </Card>
          </form>
        )}

        {/* Confirmation Dialog */}
        <ConfirmDialog
          isOpen={showConfirm}
          onClose={() => setShowConfirm(false)}
          onConfirm={handleExecuteTransfer}
          title="Confirm Money Movement"
          message={`Are you sure you want to transfer ${formatCurrency(amount, selectedSource?.currency || 'INR')} from account ${selectedSource?.account_number} to account ${selectedDest?.account_number}? Both accounts will be locked and debited/credited atomically.`}
          confirmText="Confirm Transfer"
          isLoading={isSubmitting}
        />
      </main>
    </div>
  );
};
