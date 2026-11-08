import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/Layout/ProtectedRoute';
import { Sidebar } from './components/Layout/Sidebar';
import { AIChatbot } from './components/AI/AIChatbot';

// Pages
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Accounts } from './pages/Accounts';
import { Transfer } from './pages/Transfer';
import { Deposit } from './pages/Deposit';
import { Withdraw } from './pages/Withdraw';
import { TransactionHistory } from './pages/TransactionHistory';
import { Statements } from './pages/Statements';
import { AdminDashboard } from './pages/AdminDashboard';
import { AuditorDashboard } from './pages/AuditorDashboard';
import { Profile } from './pages/Profile';
import { Unauthorized } from './pages/Unauthorized';
import { NotFound } from './pages/NotFound';

// Layout shell with fixed sidebar
const AppLayout: React.FC = () => (
  <div className="flex min-h-screen bg-slate-950 text-slate-100">
    <div className="print:hidden">
      <Sidebar />
    </div>
    <div className="ml-64 flex-1 flex flex-col min-w-0 print:ml-0">
      <Outlet />
    </div>
    <AIChatbot />
  </div>
);

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/unauthorized" element={<Unauthorized />} />

          {/* Authenticated Layout */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/accounts" element={<Accounts />} />
              <Route path="/transfers" element={<Transfer />} />
              <Route path="/deposit" element={<Deposit />} />
              <Route path="/withdraw" element={<Withdraw />} />
              <Route path="/transactions" element={<TransactionHistory />} />
              <Route path="/statements" element={<Statements />} />
              <Route path="/profile" element={<Profile />} />

              {/* Admin Portal Guard */}
              <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
                <Route path="/admin" element={<AdminDashboard />} />
              </Route>

              {/* Auditor Portal Guard */}
              <Route element={<ProtectedRoute allowedRoles={['AUDITOR', 'ADMIN']} />}>
                <Route path="/auditor" element={<AuditorDashboard />} />
              </Route>
            </Route>
          </Route>

          {/* Fallback 404 */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
