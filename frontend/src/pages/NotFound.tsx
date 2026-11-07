import React from 'react';
import { Link } from 'react-router-dom';
import { FileQuestion, ArrowLeft } from 'lucide-react';
import { Button } from '../components/UI/Button';

export const NotFound: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
      <div className="h-16 w-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 mb-4">
        <FileQuestion size={36} />
      </div>
      <h1 className="text-2xl font-black text-white tracking-tight mb-2">404 – Page Not Found</h1>
      <p className="text-xs text-slate-400 max-w-md mb-6 leading-relaxed">
        The requested ledger endpoint or page does not exist.
      </p>
      <Link to="/">
        <Button variant="primary" size="sm" className="gap-2">
          <ArrowLeft size={14} /> Return to Dashboard
        </Button>
      </Link>
    </div>
  );
};
