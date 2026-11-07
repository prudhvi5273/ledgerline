import React from 'react';
import { AlertCircle, X } from 'lucide-react';

interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onDismiss }) => {
  if (!message) return null;

  return (
    <div className="flex items-start justify-between p-3.5 mb-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
      <div className="flex items-start gap-2.5">
        <AlertCircle size={16} className="text-rose-400 shrink-0 mt-0.5" />
        <span className="leading-relaxed font-medium">{message}</span>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-rose-400 hover:text-rose-200 p-0.5 rounded transition-colors ml-2"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
};
