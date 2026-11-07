import React from 'react';

export const LoadingSpinner: React.FC<{ message?: string }> = ({ message = 'Loading...' }) => (
  <div className="flex flex-col items-center justify-center p-12 text-slate-400">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500 mb-3"></div>
    <p className="text-xs font-medium">{message}</p>
  </div>
);
