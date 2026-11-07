export type UserRole = 'ADMIN' | 'ACCOUNT_HOLDER' | 'AUDITOR';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type AccountStatus = 'ACTIVE' | 'FROZEN' | 'CLOSED';
export type AccountType = 'USER_CHECKING' | 'USER_SAVINGS' | 'SYSTEM_CLEARING';

export interface Account {
  id: string;
  user_id: string;
  account_number: string;
  currency: string;
  balance: string; // decimal string
  status: AccountStatus;
  account_type: AccountType;
  created_at: string;
}

export interface BalanceResponse {
  account_id: string;
  account_number: string;
  currency: string;
  balance: string;
  status: AccountStatus;
  as_of: string;
}

export type TransactionType = 'TRANSFER' | 'DEPOSIT' | 'WITHDRAWAL' | 'REVERSAL';
export type EntryType = 'DEBIT' | 'CREDIT';

export interface LedgerEntry {
  id: string;
  transaction_id: string;
  account_id: string;
  entry_type: EntryType;
  amount: string;
  balance_after: string;
  created_at: string;
}

export interface Transaction {
  id: string;
  reference_id: string;
  transaction_type: TransactionType;
  status: string;
  description: string | null;
  total_amount: string;
  currency: string;
  created_at: string;
  entries: LedgerEntry[];
}

export interface StatementItem {
  entry_id: string;
  transaction_id: string;
  reference_id: string;
  transaction_type: TransactionType;
  entry_type: EntryType;
  amount: string;
  balance_after: string;
  description: string | null;
  created_at: string;
}

export interface StatementResponse {
  account_id: string;
  account_number: string;
  currency: string;
  current_balance: string;
  total_debits: string;
  total_credits: string;
  total_transactions: number;
  items: StatementItem[];
}

export interface AuditLog {
  id: string;
  actor_id: string | null;
  event_type: string;
  status: 'SUCCESS' | 'REFUSED' | 'ERROR';
  refusal_reason: string | null;
  source_account_id: string | null;
  destination_account_id: string | null;
  amount: string | null;
  idempotency_key: string | null;
  metadata_info: Record<string, any> | null;
  created_at: string;
}

export interface ReconciliationReport {
  total_accounts: number;
  total_user_balance: string;
  system_clearing_balance: string;
  total_system_balance: string;
  total_ledger_debits: string;
  total_ledger_credits: string;
  is_balanced: boolean;
  discrepancy: string;
  checked_at: string;
}
