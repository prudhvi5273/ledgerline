import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Transaction } from '../types';
import { Card } from '../components/UI/Card';
import { Badge } from '../components/UI/Badge';
import { Header } from '../components/Layout/Header';
import { LoadingSpinner } from '../components/Feedback/LoadingSpinner';
import { formatCurrency, formatDate } from '../utils/currency';
import { Search, Filter, ChevronDown, ChevronUp, History } from 'lucide-react';

export const TransactionHistory: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [filterType, setFilterType] = useState('ALL');
  const [searchRef, setSearchRef] = useState('');
  const [expandedTxId, setExpandedTxId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTxs = async () => {
      setIsLoading(true);
      try {
        const res = await apiClient.get<Transaction[]>('/transactions?limit=100');
        setTransactions(res.data);
      } catch (err) {
        console.error('Failed to load transactions', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchTxs();
  }, []);

  const filtered = transactions.filter((tx) => {
    const matchesType = filterType === 'ALL' || tx.transaction_type === filterType;
    const matchesSearch =
      !searchRef ||
      tx.reference_id.toLowerCase().includes(searchRef.toLowerCase()) ||
      (tx.description && tx.description.toLowerCase().includes(searchRef.toLowerCase()));
    return matchesType && matchesSearch;
  });

  const toggleExpand = (id: string) => {
    setExpandedTxId(expandedTxId === id ? null : id);
  };

  if (isLoading) return <LoadingSpinner message="Querying ledger records..." />;

  return (
    <div className="flex-1 min-h-screen bg-slate-950 pb-16">
      <Header
        title="Transaction History"
        subtitle="Verifiable ledger postings with matching double-entry lines"
      />

      <main className="max-w-7xl mx-auto px-6 pt-6 space-y-6">
        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="relative w-full sm:w-80">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search reference ID or description..."
              value={searchRef}
              onChange={(e) => setSearchRef(e.target.value)}
              className="w-full pl-10 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter size={15} className="text-slate-400" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            >
              <option value="ALL">All Types</option>
              <option value="TRANSFER">Transfers</option>
              <option value="DEPOSIT">Deposits</option>
              <option value="WITHDRAWAL">Withdrawals</option>
            </select>
          </div>
        </div>

        {/* Transactions Table */}
        <Card>
          {filtered.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-xs">
              No transactions match your search criteria.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase font-mono tracking-wider">
                    <th className="pb-3 pl-3">Reference ID</th>
                    <th className="pb-3">Type</th>
                    <th className="pb-3">Description</th>
                    <th className="pb-3">Amount</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3">Date</th>
                    <th className="pb-3 pr-3 text-right">Ledger Entries</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {filtered.map((tx) => {
                    const isExpanded = expandedTxId === tx.id;
                    return (
                      <React.Fragment key={tx.id}>
                        <tr
                          onClick={() => toggleExpand(tx.id)}
                          className="hover:bg-slate-800/30 cursor-pointer transition-colors"
                        >
                          <td className="py-3 pl-3 font-bold text-emerald-400">{tx.reference_id}</td>
                          <td className="py-3">
                            <Badge
                              variant={
                                tx.transaction_type === 'DEPOSIT'
                                  ? 'success'
                                  : tx.transaction_type === 'WITHDRAWAL'
                                  ? 'danger'
                                  : 'info'
                              }
                            >
                              {tx.transaction_type}
                            </Badge>
                          </td>
                          <td className="py-3 font-sans text-slate-300 max-w-xs truncate">{tx.description}</td>
                          <td className="py-3 font-semibold text-slate-100">
                            {formatCurrency(tx.total_amount, tx.currency)}
                          </td>
                          <td className="py-3">
                            <Badge variant="success">{tx.status}</Badge>
                          </td>
                          <td className="py-3 text-slate-400 text-[11px]">{formatDate(tx.created_at)}</td>
                          <td className="py-3 pr-3 text-right">
                            <button className="text-slate-400 hover:text-white p-1 rounded inline-flex items-center gap-1">
                              <span className="text-[10px]">{tx.entries.length} lines</span>
                              {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            </button>
                          </td>
                        </tr>

                        {/* Expanded Double-Entry Details */}
                        {isExpanded && (
                          <tr className="bg-slate-950/80">
                            <td colSpan={7} className="p-4 border-t border-slate-800/40">
                              <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3.5 space-y-2">
                                <p className="text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-2">
                                  Atomic Double-Entry Posting Lines:
                                </p>
                                <div className="space-y-1.5">
                                  {tx.entries.map((entry) => (
                                    <div
                                      key={entry.id}
                                      className="flex items-center justify-between p-2 rounded-lg bg-slate-950 border border-slate-800/60 text-xs"
                                    >
                                      <div className="flex items-center gap-3">
                                        <Badge
                                          variant={entry.entry_type === 'DEBIT' ? 'danger' : 'success'}
                                        >
                                          {entry.entry_type}
                                        </Badge>
                                        <span className="text-slate-300">
                                          Account: <code className="text-slate-200">{entry.account_id}</code>
                                        </span>
                                      </div>
                                      <div className="text-right">
                                        <span className="font-bold text-slate-100">
                                          {formatCurrency(entry.amount, tx.currency)}
                                        </span>
                                        <span className="text-[10px] text-slate-400 ml-3">
                                          Balance After: {formatCurrency(entry.balance_after, tx.currency)}
                                        </span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </main>
    </div>
  );
};
