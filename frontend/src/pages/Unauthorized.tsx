import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { Button } from '../components/UI/Button';

export const Unauthorized: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
      <div className="h-16 w-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 mb-4">
        <ShieldAlert size={36} />
      </div>
      <h1 className="text-2xl font-black text-white tracking-tight mb-2">403 – Access Forbidden</h1>
      <p className="text-xs text-slate-400 max-w-md mb-6 leading-relaxed">
        Your current role does not possess the requisite authorization to view or manipulate this resource. Financial security controls prohibit unauthorized access.
      </p>
      <Link to="/">
        <Button variant="primary" size="sm" className="gap-2">
          <ArrowLeft size={14} /> Return to Dashboard
        </Button>
      </Link>
    </div>
  );
};
