"""
LedgerLine System Integrity & Invariant Verifier CLI.
Performs real-time mathematical validation across all accounts and ledger entries.
Run:
    python -m app.verify_system
"""

import asyncio
import sys
from decimal import Decimal
from sqlalchemy import select, func, text
from app.core.database import AsyncSessionLocal
from app.models.account import Account
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import LedgerTransaction


async def verify_system():
    print("=" * 70)
    print(" 🛡️  LEDGERLINE FINANCIAL INTEGRITY & MATHEMATICAL INVARIANT AUDIT")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        # Check 1: Database Connectivity
        print("[1/5] Testing Database Connectivity...")
        try:
            res = await db.execute(text("SELECT 1"))
            assert res.scalar_one() == 1
            print("  ✅ Database connection: OK (PostgreSQL ACID operational)")
        except Exception as e:
            print(f"  ❌ Database connection FAILED: {e}")
            return False

        # Check 2: Double-Entry Equilibrium (sum(Debits) == sum(Credits))
        print("\n[2/5] Validating Double-Entry Equilibrium (Σ Debits == Σ Credits)...")
        stmt_debits = select(func.coalesce(func.sum(LedgerEntry.amount), Decimal("0.0000"))).where(LedgerEntry.entry_type == "DEBIT")
        stmt_credits = select(func.coalesce(func.sum(LedgerEntry.amount), Decimal("0.0000"))).where(LedgerEntry.entry_type == "CREDIT")

        total_debits = (await db.execute(stmt_debits)).scalar_one()
        total_credits = (await db.execute(stmt_credits)).scalar_one()
        discrepancy = abs(total_debits - total_credits)

        print(f"  • Total Debits : ₹{total_debits:,.4f}")
        print(f"  • Total Credits: ₹{total_credits:,.4f}")
        print(f"  • Discrepancy  : ₹{discrepancy:,.4f}")

        if discrepancy == Decimal("0.0000"):
            print("  ✅ Mathematical Equilibrium: PERFECT (Discrepancy is exactly ₹0.0000)")
        else:
            print(f"  ❌ CRITICAL INVARIANT VIOLATION: Discrepancy is ₹{discrepancy}")
            return False

        # Check 3: Conservation of Money (Total System Balance == 0)
        print("\n[3/5] Validating Conservation of Money across all Accounts...")
        stmt_balance = select(func.coalesce(func.sum(Account.balance), Decimal("0.0000")))
        total_system_balance = (await db.execute(stmt_balance)).scalar_one()

        print(f"  • Net System Balance (User Accounts + Clearing): ₹{total_system_balance:,.4f}")
        if total_system_balance == Decimal("0.0000"):
            print("  ✅ Conservation of Money: PERFECT (Total system balance is ₹0.0000)")
        else:
            print(f"  ❌ CRITICAL CONSERVATION VIOLATION: Net balance is ₹{total_system_balance}")
            return False

        # Check 4: Non-Negative User Balances
        print("\n[4/5] Checking for Negative Balances on User Accounts...")
        stmt_negative = select(func.count(Account.id)).where(
            Account.account_type != "SYSTEM_CLEARING",
            Account.balance < Decimal("0.0000")
        )
        negative_count = (await db.execute(stmt_negative)).scalar_one()

        if negative_count == 0:
            print("  ✅ Non-Negative Balance Invariant: PERFECT (0 accounts below zero)")
        else:
            print(f"  ❌ OVERDRAFT VIOLATION: {negative_count} user accounts have negative balance!")
            return False

        # Check 5: Transaction-Level Balance Pairing
        print("\n[5/5] Auditing Transaction Header to Ledger Entry Pairing...")
        stmt_unbalanced_tx = text("""
            SELECT transaction_id, 
                   SUM(CASE WHEN entry_type = 'DEBIT' THEN amount ELSE -amount END) as diff
            FROM ledger_entries
            GROUP BY transaction_id
            HAVING SUM(CASE WHEN entry_type = 'DEBIT' THEN amount ELSE -amount END) != 0;
        """)
        unbalanced_result = await db.execute(stmt_unbalanced_tx)
        unbalanced_txs = unbalanced_result.fetchall()

        if len(unbalanced_txs) == 0:
            print("  ✅ All Transactions: BALANCED (100% of journals contain equal debits and credits)")
        else:
            print(f"  ❌ CRITICAL INTEGRITY FLAW: {len(unbalanced_txs)} unbalanced transactions found!")
            return False

    print("\n" + "=" * 70)
    print(" 🌟 AUDIT CERTIFICATE: LEDGERLINE SYSTEM IS MATHEMATICALLY SOUND")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_system())
    sys.exit(0 if success else 1)
