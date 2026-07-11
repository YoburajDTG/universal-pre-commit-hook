#!/usr/bin/env python3
"""
Orchestrator script for the Universal Pre-Commit Validation Framework.
Loads configuration, triggers project auto-discovery, runs validation stages,
handles global git checks, formats terminal reports, and manages exit states.
"""

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from common import BaseChecker, ValidationContext
from detect_project import detect_projects
from utils import (CommandResult, print_error, print_info, print_success,
                   print_warning, run_command, setup_logging)

from config import load_config

# Regex to validate Conventional Commits format
CONVENTIONAL_COMMIT_REGEX = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\([a-zA-Z0-9_\-\/\s]+\))?!?: .+$"
)


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
        choices=["formatter", "lint", "build", "tests", "security_scan", "coverage"],
        help="Execute only a single specific pipeline stage.",
    )
    parser.add_argument(
        "commit_msg_file",
        nargs="?",
        default=None,
        help="Path to git commit message file (passed by commit-msg hook).",
    )
    return parser.parse_args()


def validate_conventional_commit(
    commit_msg_file: Optional[str], repo_root: Path
) -> bool:
    """
    Validates if the commit message conforms to Conventional Commits standard.
    Checks the temporary pre-commit message, .git/COMMIT_EDITMSG, or last commit history.
    """
    msg: Optional[str] = None

    # 1. Read from commit-msg hook argument
    if commit_msg_file and Path(commit_msg_file).exists():
        with open(commit_msg_file, "r", encoding="utf-8") as f:
            msg = f.read().strip()

    # 2. Fallback to .git/COMMIT_EDITMSG
    if not msg:
        commit_edit_msg = repo_root / ".git" / "COMMIT_EDITMSG"
        if commit_edit_msg.exists():
            with open(commit_edit_msg, "r", encoding="utf-8") as f:
                msg = f.read().strip()

    # 3. Fallback to reading last git commit log message
    if not msg:
        res = run_command(["git", "log", "-1", "--pretty=%B"], cwd=repo_root)
        if res.success:
            msg = res.stdout.strip()

    if not msg:
        print_warning("Could not find any commit message to validate.")
        return True

    # Filter out git comments (starting with #)
    lines = [line for line in msg.splitlines() if not line.strip().startswith("#")]
    if not lines:
        return True
    first_line = lines[0].strip()

    # Skip merge commits or auto-generated release commits
    if first_line.startswith("Merge branch ") or first_line.startswith(
        "Merge pull request "
    ):
        return True

    if CONVENTIONAL_COMMIT_REGEX.match(first_line):
        print_success(f"Commit message matches conventional standards: '{first_line}'")
        return True
    else:
        print_error(
            f"Commit message fails conventional commit guidelines: '{first_line}'\n"
            "Format must follow: <type>(<scope>)!: <subject>\n"
            "Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert\n"
            "Example: feat(auth): add login credentials field"
        )
        return False


def check_branch_protection(repo_root: Path) -> None:
    """
    Retrieves the current working branch and lists safety warnings
    if committing directly to core production branches.
    """
    res = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    if not res.success:
        return

    branch_name = res.stdout.strip()
    protected_branches = {"main", "master", "develop", "prod", "production"}

    if branch_name in protected_branches:
        print_warning(
            f"You are directly on a protected branch: '{branch_name}'.\n"
            "Recommended Branch Protection Guidelines:\n"
            "  1. Configure branch rules to restrict direct commits to main/master.\n"
            "  2. Require Pull Request reviews before merging.\n"
            "  3. Configure GitHub Actions or CI gates to require status checks to pass."
        )


def run_gitleaks(repo_root: Path) -> bool:
    """Executes Gitleaks secrets scanner if Gitleaks is installed in PATH."""
    print_info("Checking for secret exposure risks via Gitleaks...")

    # Check if gitleaks is installed in PATH
    verify_install = run_command(["gitleaks", "version"], cwd=repo_root)
    if not verify_install.success:
        print_warning(
            "Gitleaks binary is not installed in the system PATH. Skipping secret scan."
        )
        return True

    # Run gitleaks detect
    leaks_res = run_command(["gitleaks", "detect", "--verbose"], cwd=repo_root)
    if leaks_res.exit_code == 0:
        print_success("No credentials or secrets leaked in codebase.")
        return True
    elif leaks_res.exit_code == 1:
        print_error("Credentials or passwords leaked! See detail in the outputs above.")
        return False
    else:
        print_warning("Gitleaks scan skipped or failed to run correctly.")
        return True


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

    # 3. Global git workflow validations
    commit_success = True
    if config.git.conventional_commits:
        commit_success = validate_conventional_commit(args.commit_msg_file, repo_root)

    if config.git.branch_protection:
        check_branch_protection(repo_root)

    gitleaks_success = True
    if config.security.gitleaks:
        gitleaks_success = run_gitleaks(repo_root)

    # If global checks fail, stop early
    if not commit_success or not gitleaks_success:
        print_error("Aborting pre-commit validation due to global hooks failures.")
        return 1

    # 4. Auto-discover repository languages
    context = ValidationContext(
        project_root=repo_root, config=config, log_file=log_path
    )
    checkers = detect_projects(context)

    if not checkers:
        print_info("No language checkers executed (no project markers detected).")
        return 0

    # 5. Define stages to execute
    if args.stage:
        stages_to_run = [args.stage]
    else:
        stages_to_run = [
            "formatter",
            "lint",
            "build",
            "tests",
            "security_scan",
            "coverage",
        ]

    # Dictionary to collect results: {checker_name: {stage_name: CommandResult}}
    results: Dict[str, Dict[str, CommandResult]] = {}

    # 6. Execute stages sequentially across detected checkers
    for checker in checkers:
        results[checker.name] = {}
        print_info(
            f"Starting validations for {checker.name} project at: {checker.context.project_root}"
        )

        for stage in stages_to_run:
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
