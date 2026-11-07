import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Account, StatementResponse } from '../types';
import { Card } from '../components/UI/Card';
import { Button } from '../components/UI/Button';
import { Badge } from '../components/UI/Badge';
import { Header } from '../components/Layout/Header';
import { LoadingSpinner } from '../components/Feedback/LoadingSpinner';
import { formatCurrency, formatDate } from '../utils/currency';
import { Printer, FileSpreadsheet, ArrowDownLeft, ArrowUpRight } from 'lucide-react';

export const Statements: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialAccId = searchParams.get('account') || '';

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState(initialAccId);
  const [statement, setStatement] = useState<StatementResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadAccounts = async () => {
      try {
        const res = await apiClient.get<Account[]>('/accounts');
        setAccounts(res.data);
        if (!selectedAccountId && res.data.length > 0) {
          setSelectedAccountId(res.data[0].id);
        }
      } catch (err) {
        console.error('Failed to load accounts', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadAccounts();
  }, []);

  useEffect(() => {
    if (!selectedAccountId) return;
    const fetchStatement = async () => {
      setIsLoading(true);
      try {
        const res = await apiClient.get<StatementResponse>(`/accounts/${selectedAccountId}/statement`);
        setStatement(res.data);
      } catch (err) {
        console.error('Failed to load statement', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchStatement();
  }, [selectedAccountId]);

  const handlePrint = () => {
    window.print();
  };

  if (isLoading && !statement) {
    return <LoadingSpinner message="Calculating running balances from immutable ledger entries..." />;
  }

  return (
    <div className="flex-1 min-h-screen bg-slate-950 pb-16 print:bg-white print:text-black">
      <div className="print:hidden">
        <Header
          title="Account Statements"
          subtitle="Verifiable chronological ledger history with continuous running balances"
        />
      </div>

      <main className="max-w-7xl mx-auto px-6 pt-6 space-y-6">
        {/* Selector & Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800 print:hidden">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <span className="text-xs font-semibold text-slate-300">Select Account:</span>
            <select
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            >
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.account_number} ({acc.currency}) — Balance: {formatCurrency(acc.balance, acc.currency)}
                </option>
              ))}
            </select>
          </div>

          <Button size="sm" variant="outline" onClick={handlePrint} className="gap-1.5 w-full sm:w-auto">
            <Printer size={15} /> Print / Export Statement
          </Button>
        </div>

        {statement && (
          <>
            {/* Statement Summary Card */}
            <Card className="print:border-none print:shadow-none">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800 print:border-black">
                <div>
                  <h3 className="text-base font-bold text-slate-100 print:text-black">Official Account Statement</h3>
                  <p className="text-xs text-slate-400 print:text-gray-600 font-mono">
                    Account: {statement.account_number} | Currency: {statement.currency}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-400 print:text-gray-600">Current Authoritative Balance</span>
                  <p className="text-2xl font-black text-emerald-400 print:text-black font-mono">
                    {formatCurrency(statement.current_balance, statement.currency)}
                  </p>
                </div>
              </div>

              {/* Financial Totals */}
              <div className="grid grid-cols-3 gap-4 pt-4 text-center">
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 print:border-gray-300">
                  <span className="text-[11px] text-slate-400 print:text-gray-600">Total Credits (Inflow)</span>
                  <p className="text-sm font-bold text-emerald-400 print:text-green-700 font-mono mt-0.5">
                    +{formatCurrency(statement.total_credits, statement.currency)}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 print:border-gray-300">
                  <span className="text-[11px] text-slate-400 print:text-gray-600">Total Debits (Outflow)</span>
                  <p className="text-sm font-bold text-rose-400 print:text-red-700 font-mono mt-0.5">
                    -{formatCurrency(statement.total_debits, statement.currency)}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 print:border-gray-300">
                  <span className="text-[11px] text-slate-400 print:text-gray-600">Ledger Postings</span>
                  <p className="text-sm font-bold text-slate-200 print:text-black font-mono mt-0.5">
                    {statement.total_transactions}
                  </p>
                </div>
              </div>
            </Card>

            {/* Chronological Running Balance Table */}
            <Card className="print:border-none print:shadow-none">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 print:border-black text-slate-400 print:text-black uppercase">
                      <th className="pb-3 pl-2">Posting Date</th>
                      <th className="pb-3">Reference</th>
                      <th className="pb-3">Type</th>
                      <th className="pb-3 font-sans">Description</th>
                      <th className="pb-3 text-right">Debit (-)</th>
                      <th className="pb-3 text-right">Credit (+)</th>
                      <th className="pb-3 pr-2 text-right">Running Balance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 print:divide-gray-300">
                    {statement.items.map((item) => (
                      <tr key={item.entry_id} className="hover:bg-slate-800/30">
                        <td className="py-3 pl-2 text-slate-400 print:text-black">{formatDate(item.created_at)}</td>
                        <td className="py-3 font-semibold text-emerald-400 print:text-black">{item.reference_id}</td>
                        <td className="py-3">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              item.entry_type === 'CREDIT'
                                ? 'bg-emerald-500/15 text-emerald-400 print:text-green-700'
                                : 'bg-rose-500/15 text-rose-400 print:text-red-700'
                            }`}
                          >
                            {item.entry_type}
                          </span>
                        </td>
                        <td className="py-3 font-sans text-slate-300 print:text-black max-w-xs truncate">
                          {item.description || item.transaction_type}
                        </td>
                        <td className="py-3 text-right text-rose-400 print:text-red-700 font-bold">
                          {item.entry_type === 'DEBIT' ? formatCurrency(item.amount, statement.currency) : '-'}
                        </td>
                        <td className="py-3 text-right text-emerald-400 print:text-green-700 font-bold">
                          {item.entry_type === 'CREDIT' ? formatCurrency(item.amount, statement.currency) : '-'}
                        </td>
                        <td className="py-3 pr-2 text-right font-black text-slate-100 print:text-black">
                          {formatCurrency(item.balance_after, statement.currency)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        )}
      </main>
    </div>
  );
};
