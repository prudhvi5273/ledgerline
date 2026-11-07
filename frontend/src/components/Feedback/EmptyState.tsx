import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ title, description, action }) => (
  <div className="flex flex-col items-center justify-center p-12 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30">
    <div className="h-12 w-12 rounded-2xl bg-slate-800 flex items-center justify-center text-slate-400 mb-4">
      <Inbox size={24} />
    </div>
    <h4 className="text-sm font-semibold text-slate-200 mb-1">{title}</h4>
    <p className="text-xs text-slate-400 max-w-sm mb-4">{description}</p>
    {action}
  </div>
);
