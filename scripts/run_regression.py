#!/usr/bin/env python
"""Week 4 regression test runner.

Runs a suite of smoke / unit tests that don't require Neo4j, then prints a
checklist of manual Neo4j-dependent tests with instructions.

Usage:
    python scripts/run_regression.py [--with-neo4j]

With --with-neo4j: also runs Neo4j-dependent tests (requires bolt://localhost:7687).
"""
import argparse
import subprocess
import sys
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)

# ---------------------------------------------------------------------------
# Test suites
# ---------------------------------------------------------------------------
OFFLINE_TESTS = [
    "tests/test_scanner.py",
    "tests/test_ssh_scanner.py",
    "tests/test_incremental_scanner.py",
    "tests/test_spring_reflection.py",
]

ONLINE_TESTS = [
    "tests/test_neo4j.py",
    "tests/test_ssh_graph.py",
    "tests/test_ssh_external_unknown.py",
    "tests/test_ssh_chain_depth.py",
    "tests/test_ssh_deep_chain.py",
    "tests/test_ssh_graph_generation_diagnostics.py",
]


def run_suite(suite: list[str], label: str) -> tuple[int, int]:
    """Return (passed, failed) counts."""
    passed = failed = 0
    print(f"\n{'='*60}")
    print(f"[TEST] {label}")
    print(f"{'='*60}")
    for test_path in suite:
        rel = test_path
        t0 = time.time()
        result = subprocess.run(
            [str(PYTHON), "-m", "pytest", rel, "-q", "--tb=short"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        elapsed = time.time() - t0
        if result.returncode == 0:
            status = "PASS"
        elif result.returncode == 5:
            status = "SKIP"
        else:
            status = "FAIL"
        # Extract summary line (last non-empty)
        lines = [l for l in (result.stdout + result.stderr).splitlines() if l.strip()]
        summary = lines[-1] if lines else "(no output)"
        print(f"  {status} {rel:<55} {elapsed:.1f}s  |  {summary}")
        if result.returncode == 0:
            passed += 1
        elif result.returncode == 5:
            # pytest exit code 5 = no tests collected — treat as neutral skip
            print(f"      (no tests collected, skipped)")
        else:
            failed += 1
            # Print error detail
            for line in lines[-15:]:
                print(f"      {line}")
    return passed, failed


def print_manual_checklist():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          Neo4j Quality Gate Manual Checklist                 ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Start Neo4j, then run each of these and verify thresholds:  ║
║                                                              ║
║  1. SSH project full regression + quality:                   ║
║     python main.py --neo4j-only --reset-graph                ║
║     python tests/test_graph_quality_thresholds.py \\         ║
║       --max-unknown-ratio 0.80                               ║
║       --min-reachability  0.55                               ║
║       --min-critical-chain-retention 1.0                     ║
║                                                              ║
║  2. SSH unknown breakdown:                                    ║
║     python tests/test_graph_quality_breakdown.py             ║
║     → target: business_unknown < 180 (down from 270)        ║
║                                                              ║
║  3. Incremental consistency check:                           ║
║     python main.py --neo4j-only --reset-graph                ║
║     python main.py --neo4j-only --incremental  (no changes)  ║
║     → Neo4j CALLS count must be identical before/after       ║
║                                                              ║
║  4. Simple fixture smoke:                                     ║
║     PROJECT_PATH=./fixtures/simple python main.py --neo4j-only --reset-graph
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


def main():
    ap = argparse.ArgumentParser(description="Week 4 regression runner")
    ap.add_argument("--with-neo4j", action="store_true", help="Also run Neo4j-dependent tests")
    args = ap.parse_args()

    total_passed = total_failed = 0

    p, f = run_suite(OFFLINE_TESTS, "Offline Tests (no Neo4j required)")
    total_passed += p
    total_failed += f

    if args.with_neo4j:
        p, f = run_suite(ONLINE_TESTS, "Online Tests (requires Neo4j)")
        total_passed += p
        total_failed += f
    else:
        print(f"\n[SKIP] {len(ONLINE_TESTS)} Neo4j-dependent tests (use --with-neo4j to include)")

    print(f"\n{'='*60}")
    print(f"Summary: {total_passed} passed, {total_failed} failed")
    print(f"{'='*60}")

    print_manual_checklist()

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
