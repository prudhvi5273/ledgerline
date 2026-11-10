"""
LedgerLine Concurrency Stress & High-Load Benchmark Tool.
Simulates high-velocity concurrent transfers, bidirectional swap races,
and duplicate idempotency attacks while validating mathematical invariants.

Usage:
    python -m app.stress_test
"""

import asyncio
import time
import uuid
from decimal import Decimal
from typing import List, Tuple
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.account import Account
from app.models.user import User
from app.services.transfer_engine import TransferEngine
from app.services.idempotency_service import IdempotencyService
from app.app_verify_system import verify_system if False else None  # type check stub


async def run_stress_test(concurrency_count: int = 50):
    print("=" * 75)
    print(" 🚀 LEDGERLINE CONCURRENCY STRESS & HIGH-LOAD BENCHMARK SUITE")
    print(f"    Target Workers: {concurrency_count} Concurrent Asynchronous Coroutines")
    print("=" * 75)

    async with AsyncSessionLocal() as db:
        # 1. Fetch Alice, Bob and their accounts
        stmt_users = select(User).where(User.email.in_(["client.alice@example.com", "client.bob@example.com"]))
        users = (await db.execute(stmt_users)).scalars().all()
        user_map = {u.email: u for u in users}

        if "client.alice@example.com" not in user_map or "client.bob@example.com" not in user_map:
            print("❌ Demo accounts not found. Please ensure database is seeded (python -m app.seed)")
            return False

        alice = user_map["client.alice@example.com"]
        bob = user_map["client.bob@example.com"]

        stmt_alice_acc = select(Account).where(Account.user_id == alice.id, Account.account_type == "USER_CHECKING")
        stmt_bob_acc = select(Account).where(Account.user_id == bob.id, Account.account_type == "USER_CHECKING")

        acc_alice = (await db.execute(stmt_alice_acc)).scalar_one_or_none()
        acc_bob = (await db.execute(stmt_bob_acc)).scalar_one_or_none()

        if not acc_alice or not acc_bob:
            print("❌ User checking accounts not found for Alice or Bob.")
            return False

        alice_id = acc_alice.id
        bob_id = acc_bob.id

    print(f"\n[Test Setup] Source: Alice ({alice_id}) <===> Destination: Bob ({bob_id})")

    # 2. Benchmark Bidirectional Transfers (25 Alice->Bob, 25 Bob->Alice simultaneously)
    # This specifically stresses the deterministic ascending lock ordering rule!
    print(f"\n[Phase 1/3] Executing {concurrency_count} Concurrent Bidirectional Transfers...")
    print("           (Tests deterministic ascending row locks against circular wait deadlocks)")

    successes = 0
    failures = 0
    deadlocks = 0

    async def execute_single_transfer(worker_id: int, is_alice_sender: bool) -> Tuple[bool, str]:
        sender = alice if is_alice_sender else bob
        src = alice_id if is_alice_sender else bob_id
        dst = bob_id if is_alice_sender else alice_id
        amount = Decimal("10.0000")
        key = f"stress-transfer-{worker_id}-{uuid.uuid4().hex[:8]}"

        async with AsyncSessionLocal() as session:
            try:
                await TransferEngine.execute_transfer(
                    db=session,
                    actor=sender,
                    source_account_id=src,
                    destination_account_id=dst,
                    amount=amount,
                    description=f"Concurrent stress test worker #{worker_id}",
                    idempotency_key=key
                )
                await session.commit()
                return (True, "OK")
            except Exception as e:
                await session.rollback()
                err = str(e).lower()
                if "deadlock" in err:
                    return (False, "DEADLOCK")
                return (False, f"FAILED: {e}")

    start_time = time.perf_counter()
    tasks = [
        execute_single_transfer(i, is_alice_sender=(i % 2 == 0))
        for i in range(concurrency_count)
    ]
    results = await asyncio.gather(*tasks)
    duration = time.perf_counter() - start_time

    for success, reason in results:
        if success:
            successes += 1
        else:
            failures += 1
            if reason == "DEADLOCK":
                deadlocks += 1

    throughput = concurrency_count / duration if duration > 0 else 0
    avg_latency = (duration / concurrency_count) * 1000

    print(f"  • Completed In       : {duration:.3f} seconds")
    print(f"  • Throughput         : {throughput:.1f} transfers/sec")
    print(f"  • Mean Latency       : {avg_latency:.2f} ms/op")
    print(f"  • Successful Transfers: {successes}/{concurrency_count}")
    print(f"  • Deadlocks Detected : {deadlocks} (Must be exactly 0)")

    if deadlocks > 0:
        print("  ❌ CRITICAL CONCURRENCY FAILURE: Circular wait deadlock occurred!")
        return False
    print("  ✅ Concurrency Safety: PERFECT (Zero deadlocks under bidirectional load)")

    # 3. Benchmark Idempotency Race (20 concurrent requests with identical Idempotency-Key)
    print(f"\n[Phase 2/3] Simulating Rapid Duplicate Attack (20 concurrent requests, SAME key)...")
    shared_key = f"idemp-race-{uuid.uuid4().hex}"
    idemp_success = 0
    idemp_cached = 0
    idemp_conflicts = 0

    async def hit_duplicate_endpoint(worker_id: int):
        async with AsyncSessionLocal() as session:
            try:
                # Check idempotency
                hash_val = IdempotencyService.compute_hash({"amount": "50.0000"})
                cached = await IdempotencyService.check_or_reserve(
                    db=session,
                    idempotency_key=shared_key,
                    user_id=alice.id,
                    request_path="/transfers",
                    payload_hash=hash_val
                )
                if cached:
                    return "CACHED"

                # Execute transfer
                await TransferEngine.execute_transfer(
                    db=session,
                    actor=alice,
                    source_account_id=alice_id,
                    destination_account_id=bob_id,
                    amount=Decimal("50.0000"),
                    description="Duplicate race test",
                    idempotency_key=shared_key
                )
                await IdempotencyService.complete_record(
                    db=session,
                    idempotency_key=shared_key,
                    response_code=201,
                    response_body={"status": "TRANSFER_POSTED"}
                )
                await session.commit()
                return "CREATED"
            except Exception as e:
                await session.rollback()
                err_msg = str(e)
                if "409" in err_msg or "Conflict" in err_msg:
                    return "CONFLICT_REJECTED"
                return f"ERR: {e}"

    race_tasks = [hit_duplicate_endpoint(i) for i in range(20)]
    race_results = await asyncio.gather(*race_tasks)

    for res in race_results:
        if res == "CREATED":
            idemp_success += 1
        elif res == "CACHED":
            idemp_cached += 1
        elif res == "CONFLICT_REJECTED":
            idemp_conflicts += 1

    print(f"  • Primary Creation   : {idemp_success} (Must be exactly 1)")
    print(f"  • Cached Replays     : {idemp_cached}")
    print(f"  • Race Rejections    : {idemp_conflicts} (409 Conflict)")

    if idemp_success != 1:
        print(f"  ❌ IDEMPOTENCY FAILURE: Multiple transfers created! ({idemp_success})")
        return False
    print("  ✅ Exact-Once Idempotency: PERFECT (Exactly 1 money movement executed)")

    # 4. Post-Stress System Integrity Audit
    print(f"\n[Phase 3/3] Running Post-Load Mathematical Ledger Verification...")
    from app.verify_system import verify_system
    system_valid = await verify_system()

    if not system_valid:
        print("  ❌ POST-LOAD AUDIT FAILED!")
        return False

    print("\n" + "=" * 75)
    print(" 🌟 CONCURRENCY BENCHMARK COMPLETE: ZERO DEADLOCKS & FULL INTEGRITY")
    print("=" * 75)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_stress_test())
    import sys
    sys.exit(0 if success else 1)
