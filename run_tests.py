#!/usr/bin/env python3
"""SH-LAB Opaque-Box E2E Test Suite Runner.

Executes tests across Tiers 1-4 with structured reporting.

Usage:
    python run_tests.py              # Run all tiers (Tiers 1-4)
    python run_tests.py --tier 1     # Run Tier 1: Feature Coverage
    python run_tests.py --tier 2     # Run Tier 2: Boundary & Corner Cases
    python run_tests.py --tier 3     # Run Tier 3: Cross-Feature Combinations
    python run_tests.py --tier 4     # Run Tier 4: Real-World Scenarios
    python run_tests.py -v           # Run with verbose pytest output
"""
import sys
import os
import argparse
import time
import pytest

TIER_DIRS = {
    1: "tests/tier1_feature_coverage",
    2: "tests/tier2_boundary_corner",
    3: "tests/tier3_cross_feature",
    4: "tests/tier4_real_world_scenarios",
}

TIER_NAMES = {
    1: "Tier 1: Feature Coverage (R1–R6)",
    2: "Tier 2: Boundary & Corner Cases (R1–R6)",
    3: "Tier 3: Cross-Feature Combinations",
    4: "Tier 4: Real-World Application Scenarios",
}

def parse_args():
    parser = argparse.ArgumentParser(description="SH-LAB E2E Test Suite Runner")
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        help="Run a specific tier (1, 2, 3, or 4). If omitted, runs all tiers.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose pytest output",
    )
    parser.add_argument(
        "-k", "--keyword",
        type=str,
        default=None,
        help="Filter tests by keyword expression",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    print("=" * 70)
    print(" SH-LAB Opaque-Box E2E Test Suite Execution")
    print(f" Target: {os.getenv('SHLAB_API_URL', 'http://localhost:8000')}")
    print("=" * 70)

    tiers_to_run = [args.tier] if args.tier else [1, 2, 3, 4]

    pytest_args = ["-q"]
    if args.verbose:
        pytest_args = ["-v"]

    if args.keyword:
        pytest_args.extend(["-k", args.keyword])

    start_time = time.time()
    overall_exit_code = 0
    results_summary = {}

    for tier_num in tiers_to_run:
        tier_dir = TIER_DIRS[tier_num]
        tier_name = TIER_NAMES[tier_num]
        print(f"\n>>> Executing {tier_name} ({tier_dir})...")
        
        target_args = list(pytest_args) + [tier_dir]
        tier_start = time.time()
        exit_code = pytest.main(target_args)
        tier_duration = time.time() - tier_start
        
        status = "PASSED" if exit_code == 0 else f"FAILED (code {exit_code})"
        results_summary[tier_num] = {
            "name": tier_name,
            "status": status,
            "duration": tier_duration,
            "exit_code": exit_code,
        }
        if exit_code != 0:
            overall_exit_code = exit_code

    total_duration = time.time() - start_time
    print("\n" + "=" * 70)
    print(" E2E Test Suite Execution Summary")
    print("=" * 70)
    for t_num, summary in results_summary.items():
        print(f" Tier {t_num}: {summary['name']:<42} [{summary['status']}] ({summary['duration']:.2f}s)")
    print("-" * 70)
    print(f" Total Duration: {total_duration:.2f}s")
    print(f" Overall Status: {'ALL PASSED' if overall_exit_code == 0 else 'TEST FAILURES DETECTED'}")
    print("=" * 70)

    return overall_exit_code


if __name__ == "__main__":
    sys.exit(main())
