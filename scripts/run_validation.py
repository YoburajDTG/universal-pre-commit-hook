#!/usr/bin/env python3
"""
Orchestrator script for the Universal Pre-Commit Validation Framework.
Loads configuration, triggers project auto-discovery, runs validation stages,
formats terminal reports, and manages exit states.
"""

import argparse
import concurrent.futures
import sys
import time
from pathlib import Path
from typing import Dict, List

from common import BaseChecker, ValidationContext
from detect_project import detect_projects
from reporter import write_reports
from utils import (
    CommandResult,
    get_changed_files,
    git_commit_and_push,
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
    parser.add_argument(
        "--report-json",
        type=str,
        help="Path to export the execution summary as a JSON file.",
    )
    parser.add_argument(
        "--report-md",
        type=str,
        help="Path to export the execution summary as a Markdown file.",
    )
    parser.add_argument(
        "--report-html",
        type=str,
        help="Path to export the execution summary as an HTML dashboard.",
    )
    parser.add_argument(
        "--push",
        "--auto-push",
        dest="push",
        action="store_true",
        help="Automatically commit changes and push to Git remote on validation success.",
    )
    parser.add_argument(
        "--push-branch",
        type=str,
        help="Target Git branch to push to (defaults to active branch).",
    )
    parser.add_argument(
        "--push-remote",
        type=str,
        default="origin",
        help="Target Git remote (default: origin).",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Skip auto-creating a Git commit before pushing.",
    )
    parser.add_argument(
        "-m",
        "--commit-msg",
        type=str,
        help="Custom commit message to use instead of auto-generating one.",
    )
    parser.add_argument(
        "--fix",
        "--auto-fix",
        dest="fix",
        action="store_true",
        help="Automatically fix code formatting and linting errors when possible.",
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


def run_checker_stages(
    checker: BaseChecker, stages_to_run: List[str], config
) -> Dict[str, CommandResult]:
    """Helper to run stages for a single checker. Used for parallel execution."""
    checker_results = {}
    print_info(
        f"Starting validations for {checker.name} project at: {checker.context.project_root}"
    )
    for stage in stages_to_run:
        if stage == "security" and not config.security.enabled:
            continue

        print_info(f"Executing: {checker.name} -> {stage}")
        res = checker.run_stage(stage)
        checker_results[stage] = res

        if not res.success:
            print_error(f"Stage '{stage}' failed for {checker.name} project.")
            output = res.stderr.strip() or res.stdout.strip()
            if output:
                print(f"\033[91m{output}\033[0m")
            break
    return checker_results


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
    auto_fix = args.fix or config.auto_fix

    changed_files = get_changed_files(repo_root) if config.incremental_checks else []

    # 3. Auto-discover repository languages
    context = ValidationContext(
        project_root=repo_root,
        config=config,
        log_file=log_path,
        changed_files=changed_files,
        auto_fix=auto_fix,
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

    # Define report output paths
    report_paths = {
        "json": args.report_json,
        "md": args.report_md,
        "html": args.report_html,
    }

    # 5. Execute stages
    any_failures = False
    if config.parallel_execution and len(checkers) > 1:
        print_info("Running checkers in parallel mode...")
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(checkers)
        ) as executor:
            future_to_checker = {
                executor.submit(
                    run_checker_stages, checker, stages_to_run, config
                ): checker
                for checker in checkers
            }
            for future in concurrent.futures.as_completed(future_to_checker):
                checker = future_to_checker[future]
                try:
                    checker_results = future.result()
                    results[checker.name] = checker_results
                    for stage, res in checker_results.items():
                        if not res.success:
                            any_failures = True
                except Exception as exc:
                    print_error(f"Checker {checker.name} raised an exception: {exc}")
                    any_failures = True
    else:
        for checker in checkers:
            checker_results = run_checker_stages(checker, stages_to_run, config)
            results[checker.name] = checker_results
            for stage, res in checker_results.items():
                if not res.success:
                    any_failures = True
                    break
            if any_failures:
                break

    overall_duration = time.perf_counter() - start_time
    success = print_overall_summary(checkers, results, overall_duration)
    write_reports(checkers, results, overall_duration, success, report_paths)

    # 6. Execute auto-commit and push if enabled and validation passed
    should_push = args.push or config.git.auto_push
    if success and should_push:
        print_info(
            "All validation checks PASSED. Initiating automated Git commit & push..."
        )
        remote = args.push_remote or config.git.remote
        target_branch = args.push_branch or config.git.target_branch
        auto_commit = False if args.no_commit else config.git.auto_commit
        commit_prefix = config.git.commit_prefix

        push_success = git_commit_and_push(
            remote=remote,
            target_branch=target_branch,
            auto_commit=auto_commit,
            custom_commit_msg=args.commit_msg,
            commit_prefix=commit_prefix,
            cwd=repo_root,
        )
        if not push_success:
            print_error("Automated Git commit & push failed.")
            return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
