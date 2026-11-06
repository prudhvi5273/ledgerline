"""0001_initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-06 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='ACCOUNT_HOLDER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("role IN ('ADMIN', 'ACCOUNT_HOLDER', 'AUDITOR')", name='chk_users_role_valid')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=True)
    op.create_index('idx_users_role', 'users', ['role'])

    # 2. accounts table
    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_number', sa.String(length=32), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='INR'),
        sa.Column('balance', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0000'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('account_type', sa.String(length=30), nullable=False, server_default='USER_CHECKING'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_number'),
        sa.CheckConstraint("account_type = 'SYSTEM_CLEARING' OR balance >= 0", name='chk_accounts_balance_positive'),
        sa.CheckConstraint("status IN ('ACTIVE', 'FROZEN', 'CLOSED')", name='chk_accounts_status_valid'),
        sa.CheckConstraint("account_type IN ('USER_CHECKING', 'USER_SAVINGS', 'SYSTEM_CLEARING')", name='chk_accounts_type_valid')
    )
    op.create_index('idx_accounts_user_id', 'accounts', ['user_id'])
    op.create_index('idx_accounts_status', 'accounts', ['status'])

    # 3. ledger_transactions table
    op.create_table(
        'ledger_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reference_id', sa.String(length=64), nullable=False),
        sa.Column('transaction_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='POSTED'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='INR'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reference_id'),
        sa.CheckConstraint('total_amount > 0', name='chk_ledger_tx_amount_positive'),
        sa.CheckConstraint("transaction_type IN ('TRANSFER', 'DEPOSIT', 'WITHDRAWAL', 'REVERSAL')", name='chk_ledger_tx_type_valid')
    )
    op.create_index('idx_ledger_tx_created', 'ledger_transactions', ['created_at'])
    op.create_index('idx_ledger_tx_type', 'ledger_transactions', ['transaction_type'])

    # 4. ledger_entries table
    op.create_table(
        'ledger_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entry_type', sa.String(length=10), nullable=False),
        sa.Column('amount', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('balance_after', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['transaction_id'], ['ledger_transactions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('amount > 0', name='chk_ledger_entries_amount_positive'),
        sa.CheckConstraint("entry_type IN ('DEBIT', 'CREDIT')", name='chk_ledger_entries_type_valid')
    )
    op.create_index('idx_ledger_entries_account_created', 'ledger_entries', ['account_id', 'created_at'])
    op.create_index('idx_ledger_entries_tx_id', 'ledger_entries', ['transaction_id'])

    # 5. idempotency_records table
    op.create_table(
        'idempotency_records',
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_path', sa.String(length=255), nullable=False),
        sa.Column('request_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('response_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('idempotency_key'),
        sa.CheckConstraint("status IN ('PENDING', 'COMPLETED', 'FAILED')", name='chk_idemp_status_valid')
    )
    op.create_index('idx_idemp_user_created', 'idempotency_records', ['user_id', 'created_at'])

    # 6. audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('refusal_reason', sa.String(length=100), nullable=True),
        sa.Column('source_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('destination_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['destination_account_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_account_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('SUCCESS', 'REFUSED', 'ERROR')", name='chk_audit_status_valid')
    )
    op.create_index('idx_audit_created_event', 'audit_logs', ['created_at', 'event_type'])

    # 7. Immutability Trigger on ledger_entries
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_fn_prevent_ledger_tampering()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Ledger entries are strictly immutable. UPDATE and DELETE operations are forbidden.';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_ledger_entries_immutability
        BEFORE UPDATE OR DELETE ON ledger_entries
        FOR EACH ROW EXECUTE FUNCTION trg_fn_prevent_ledger_tampering();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_ledger_entries_immutability ON ledger_entries;")
    op.execute("DROP FUNCTION IF EXISTS trg_fn_prevent_ledger_tampering();")
    op.drop_table('audit_logs')
    op.drop_table('idempotency_records')
    op.drop_table('ledger_entries')
    op.drop_table('ledger_transactions')
    op.drop_table('accounts')
    op.drop_table('users')
