import asyncio
import logging
import uuid
from decimal import Decimal
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.account import Account
from app.models.transaction import LedgerTransaction
from app.models.ledger_entry import LedgerEntry
from app.models.audit_log import AuditLog
from app.services.transfer_engine import TransferEngine

logger = logging.getLogger("uvicorn")

CLEARING_ACCOUNT_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def seed_demo_data():
    """
    Seed initial demonstration users, accounts, and double-entry ledger transactions.
    Ensures mathematical equilibrium: sum(Debits) == sum(Credits) and Total System Balance == 0.
    """
    async with AsyncSessionLocal() as db:
        # Check if users table already contains data
        user_count_result = await db.execute(select(func.count(User.id)))
        user_count = user_count_result.scalar_one()

        if user_count > 0:
            logger.info("Database already seeded with user records. Skipping initial demo seed.")
            return

        logger.info("Initializing LedgerLine demo seed data...")

        # 1. System Clearing Authority (Admin user to own clearing account)
        system_admin = User(
            id=uuid.uuid4(),
            email="system.clearing@ledgerline.internal",
            password_hash="[LOCKED_SYSTEM_ACCOUNT]",
            full_name="LedgerLine Clearing Authority",
            role="ADMIN",
            is_active=True
        )
        db.add(system_admin)

        # 2. Main System Administrator
        root_admin = User(
            id=uuid.uuid4(),
            email="admin.root@example.com",
            password_hash=get_password_hash("AdminMasterPass123!"),
            full_name="Root System Administrator",
            role="ADMIN",
            is_active=True
        )
        db.add(root_admin)

        # 3. Independent Compliance Auditor
        auditor = User(
            id=uuid.uuid4(),
            email="auditor.check@example.com",
            password_hash=get_password_hash("AuditorPass123!"),
            full_name="Independent Financial Auditor",
            role="AUDITOR",
            is_active=True
        )
        db.add(auditor)

        # 4. Client Alice (Account Holder)
        alice = User(
            id=uuid.uuid4(),
            email="client.alice@example.com",
            password_hash=get_password_hash("SecretPassword123!"),
            full_name="Alice Smith",
            role="ACCOUNT_HOLDER",
            is_active=True
        )
        db.add(alice)

        # 5. Client Bob (Account Holder)
        bob = User(
            id=uuid.uuid4(),
            email="client.bob@example.com",
            password_hash=get_password_hash("SecretPassword123!"),
            full_name="Bob Jones",
            role="ACCOUNT_HOLDER",
            is_active=True
        )
        db.add(bob)

        await db.flush()

        # 6. Create SYSTEM_CLEARING Account
        clearing_account = Account(
            id=CLEARING_ACCOUNT_UUID,
            user_id=system_admin.id,
            account_number="SYS-CLEARING-001",
            currency="INR",
            balance=Decimal("0.0000"),
            status="ACTIVE",
            account_type="SYSTEM_CLEARING"
        )
        db.add(clearing_account)

        # 7. Create Accounts for Alice
        alice_checking = Account(
            id=uuid.uuid4(),
            user_id=alice.id,
            account_number="ACC-ALICE-INR-01",
            currency="INR",
            balance=Decimal("0.0000"),
            status="ACTIVE",
            account_type="USER_CHECKING"
        )
        alice_savings = Account(
            id=uuid.uuid4(),
            user_id=alice.id,
            account_number="ACC-ALICE-INR-02",
            currency="INR",
            balance=Decimal("0.0000"),
            status="ACTIVE",
            account_type="USER_SAVINGS"
        )
        db.add(alice_checking)
        db.add(alice_savings)

        # 8. Create Account for Bob
        bob_checking = Account(
            id=uuid.uuid4(),
            user_id=bob.id,
            account_number="ACC-BOB-INR-01",
            currency="INR",
            balance=Decimal("0.0000"),
            status="ACTIVE",
            account_type="USER_CHECKING"
        )
        db.add(bob_checking)

        await db.flush()

        # 9. Execute initial balanced deposits
        # Alice Checking Deposit: +15,000 INR
        await TransferEngine.execute_deposit(
            db=db,
            actor=alice,
            account_id=alice_checking.id,
            amount=Decimal("15000.0000"),
            description="Initial capital onboarding deposit"
        )

        # Alice Savings Deposit: +5,000 INR
        await TransferEngine.execute_deposit(
            db=db,
            actor=alice,
            account_id=alice_savings.id,
            amount=Decimal("5000.0000"),
            description="High-yield savings allocation"
        )

        # Bob Checking Deposit: +5,000 INR
        await TransferEngine.execute_deposit(
            db=db,
            actor=bob,
            account_id=bob_checking.id,
            amount=Decimal("5000.0000"),
            description="Opening merchant balance deposit"
        )

        # 10. Execute an initial transfer from Alice to Bob: 1,500 INR
        await TransferEngine.execute_transfer(
            db=db,
            actor=alice,
            source_account_id=alice_checking.id,
            destination_account_id=bob_checking.id,
            amount=Decimal("1500.0000"),
            description="Invoice payment: Contract settlement #INV-2026-001"
        )

        await db.commit()
        logger.info("LedgerLine demo seed data completed successfully! Demo accounts and transactions are ready.")


async def auto_seed_if_empty():
    """Non-blocking helper for startup lifespan hook."""
    try:
        await seed_demo_data()
    except Exception as e:
        logger.error(f"Auto-seed exception: {e}")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
