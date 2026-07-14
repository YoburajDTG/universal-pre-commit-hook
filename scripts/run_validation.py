#!/usr/bin/env python3
"""
Orchestrator script for the Universal Pre-Commit Validation Framework.
Loads configuration, triggers project auto-discovery, runs validation stages,
formats terminal reports, and manages exit states.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List

from common import BaseChecker, ValidationContext
from detect_project import detect_projects
from utils import (
    CommandResult,
    print_error,
    print_info,
    setup_logging,
)

from config import load_config


def parse_args() -> argparse.Namespace:
    """Parses command-line configuration arguments."""
    parser = argparse.ArgumentParser(
        description="Universal Pre-Commit Validation Runner."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to the validation configuration YAML file.",
    )
    parser.add_argument(
        "--log",
        type=str,
        default="precommit_validation.log",
        help="Path to save execution logs.",
    )
    parser.add_argument(
        "--stage",
        type=str,
        choices=["formatter", "lint", "build", "tests", "security"],
        help="Execute only a single specific pipeline stage.",
    )
    return parser.parse_args()


def print_overall_summary(
    checkers: List[BaseChecker],
    results: Dict[str, Dict[str, CommandResult]],
    overall_duration: float,
) -> bool:
    """
    Formats and prints a comprehensive execution dashboard report.
    Returns True if all checks passed, False otherwise.
    """
    print("\n" + "=" * 60)
    print("                 VALIDATION EXECUTION SUMMARY")
    print("=" * 60)

    any_failures = False

    for checker in checkers:
        print(f"\nProject: {checker.name} ({checker.context.project_root.name})")
        print("-" * 50)

        checker_results = results.get(checker.name, {})
        for stage, res in checker_results.items():
            duration_str = f"{res.duration:.2f}s"

            # Format outputs based on command status
            if "skipped" in res.command or "unimplemented" in res.command:
                status = "\033[93m[SKIPPED]\033[0m"
                duration_str = "N/A"
            elif res.success:
                status = "\033[92m[PASSED]\033[0m"
            else:
                status = "\033[91m[FAILED]\033[0m"
                any_failures = True

            print(f"  Stage: {stage:<15} {status:<15} Duration: {duration_str}")

    print("\n" + "=" * 60)
    print(f"Overall Duration: {overall_duration:.2f}s")

    if any_failures:
        print("\033[91mOverall Status: FAILED (Some checks did not pass)\033[0m")
    else:
        print("\033[92mOverall Status: PASSED (All validation hooks succeeded)\033[0m")

    print("=" * 60 + "\n")
    return not any_failures


def main() -> int:
    """Main validation orchestration sequence."""
    start_time = time.perf_counter()
    args = parse_args()

    repo_root = Path.cwd().resolve()
    log_path = repo_root / args.log

    # 1. Setup logging
    setup_logging(log_path)
    print_info(f"Initialized Universal Pre-Commit Validation. Log file: {log_path}")

    # 2. Load configurations
    config_path = repo_root / args.config
    config = load_config(config_path)

    # 3. Auto-discover repository languages
    context = ValidationContext(
        project_root=repo_root, config=config, log_file=log_path
    )
    checkers = detect_projects(context)

    if not checkers:
        print_info("No language checkers executed (no project markers detected).")
        return 0

    # 4. Define stages to execute
    if args.stage:
        stages_to_run = [args.stage]
    else:
        stages_to_run = ["formatter", "lint", "build", "tests", "security"]

    # Dictionary to collect results: {checker_name: {stage_name: CommandResult}}
    results: Dict[str, Dict[str, CommandResult]] = {}

    # 5. Execute stages sequentially across detected checkers
    for checker in checkers:
        results[checker.name] = {}
        print_info(
            f"Starting validations for {checker.name} project at: {checker.context.project_root}"
        )

        for stage in stages_to_run:
            # Skip security stage if globally disabled in the security settings block
            if stage == "security" and not config.security.enabled:
                continue

            print_info(f"Executing: {checker.name} -> {stage}")
            res = checker.run_stage(stage)
            results[checker.name][stage] = res

            if not res.success:
                print_error(f"Stage '{stage}' failed for {checker.name} project.")
                # Return immediately as requested for strict pre-commit checks
                overall_duration = time.perf_counter() - start_time
                print_overall_summary(checkers, results, overall_duration)
                return res.exit_code if res.exit_code != 0 else 1

    overall_duration = time.perf_counter() - start_time
    success = print_overall_summary(checkers, results, overall_duration)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
