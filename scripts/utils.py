#!/usr/bin/env python3
"""
Utility module for the Universal Pre-Commit Validation Framework.
Provides logging setup, colorized CLI helpers, and robust process execution.
"""

import logging
import re
import subprocess  # nosec B404
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored terminal output
colorama.init(autoreset=True)

# Shared framework logger
logger = logging.getLogger("universal-precommit")

# Regex to strip ANSI escape codes
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\(B")


class AnsiStrippingFormatter(logging.Formatter):
    """Logging Formatter that strips ANSI escape codes for file outputs."""

    def format(self, record: logging.LogRecord) -> str:
        # Create a copy of formatting parameters to avoid mutating the log record
        orig_msg = record.msg
        if isinstance(record.msg, str):
            record.msg = ANSI_ESCAPE.sub("", record.msg)
        result = super().format(record)
        record.msg = orig_msg
        return result


@dataclass(frozen=True)
class CommandResult:
    """Represents the results of an executed CLI command."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    success: bool


def setup_logging(log_file: Optional[Path] = None) -> None:
    """Configures the logging system for the validation execution."""
    log_level = logging.INFO
    log_format = "%(asctime)s - %(levelname)s - %(message)s"

    # Use standard Formatter for stream handler (console)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    console_handler.setLevel(log_level)

    handlers = [console_handler]

    if log_file:
        # Ensure parent folder for the log file exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(AnsiStrippingFormatter(log_format))
        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    # Reconfigure root logging
    logging.basicConfig(level=log_level, handlers=handlers, force=True)


def print_success(message: str) -> None:
    """Prints a green-colored success message to the console and logs it."""
    formatted = f"{Fore.GREEN}[SUCCESS] + {message}{Style.RESET_ALL}"
    print(formatted)
    logger.info(f"[SUCCESS] {message}")


def print_error(message: str) -> None:
    """Prints a red-colored error message to the console and logs it."""
    formatted = f"{Fore.RED}[ERROR] - {message}{Style.RESET_ALL}"
    print(formatted)
    logger.error(f"[ERROR] {message}")


def print_warning(message: str) -> None:
    """Prints a yellow-colored warning message to the console and logs it."""
    formatted = f"{Fore.YELLOW}[WARNING] ! {message}{Style.RESET_ALL}"
    print(formatted)
    logger.warning(f"[WARNING] {message}")


def print_info(message: str) -> None:
    """Prints a cyan-colored info message to the console."""
    formatted = f"{Fore.CYAN}[INFO] * {message}{Style.RESET_ALL}"
    print(formatted)
    logger.info(f"[INFO] {message}")


def run_command(
    cmd: Union[str, List[str]],
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
    timeout: Optional[float] = None,
) -> CommandResult:
    """
    Executes a shell command safely, logs details, captures output, and measures execution time.
    """
    cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
    logger.info(f"Running command: {cmd_str} (cwd: {cwd or Path.cwd()})")

    start_time = time.perf_counter()
    is_windows = sys.platform.startswith("win")

    # Use shell execution on Windows for list commands to resolve command script wrappers (e.g. npm, npx, gradle)
    shell_active = isinstance(cmd, str) or (is_windows and isinstance(cmd, list))

    try:
        # Run process via subprocess
        process = subprocess.run(  # nosec B602 B603 B607
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=shell_active,
            timeout=timeout,
        )

        duration = time.perf_counter() - start_time
        exit_code = process.returncode
        stdout = process.stdout or ""
        stderr = process.stderr or ""
        success = exit_code == 0

        # Log command details and output status
        logger.info(
            f"Command '{cmd_str}' finished with exit code {exit_code} in {duration:.2f}s"
        )
        if not success and stderr.strip():
            logger.debug(f"Stderr: {stderr.strip()}")

        return CommandResult(
            command=cmd_str,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            success=success,
        )

    except subprocess.TimeoutExpired as te:
        duration = time.perf_counter() - start_time
        logger.error(f"Command '{cmd_str}' timed out after {timeout} seconds")
        return CommandResult(
            command=cmd_str,
            exit_code=-1,
            stdout=te.stdout or "",
            stderr=te.stderr or "TIMEOUT EXPIRED",
            duration=duration,
            success=False,
        )
    except Exception as e:
        duration = time.perf_counter() - start_time
        logger.error(f"Failed to execute command '{cmd_str}': {e}")
        return CommandResult(
            command=cmd_str,
            exit_code=-2,
            stdout="",
            stderr=str(e),
            duration=duration,
            success=False,
        )

def get_changed_files(cwd: Optional[Path] = None) -> List[str]:
    """Retrieves the list of staged files, modified tracked files, and untracked files using Git."""
    try:
        work_dir = cwd or Path.cwd()
        process_staged = subprocess.run(  # nosec
            ["git", "diff", "--cached", "--name-only"],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        process_modified = subprocess.run(  # nosec
            ["git", "diff", "--name-only"],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        process_untracked = subprocess.run(  # nosec
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        files = []
        if process_staged.returncode == 0:
            files.extend(process_staged.stdout.strip().split("\n"))
        if process_modified.returncode == 0:
            files.extend(process_modified.stdout.strip().split("\n"))
        if process_untracked.returncode == 0:
            files.extend(process_untracked.stdout.strip().split("\n"))

        # Deduplicate and remove empty strings
        return list(set(f for f in files if f.strip()))
    except Exception as e:
        logger.warning(f"Failed to get changed files via git: {e}")
        return []

def get_current_branch(cwd: Optional[Path] = None) -> str:
    """Returns the currently checked out Git branch name."""
    try:
        res = subprocess.run(  # nosec
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd or Path.cwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception as e:
        logger.warning(f"Could not determine current Git branch: {e}")
    return "main"

def generate_commit_message(
    custom_msg: Optional[str] = None,
    commit_prefix: Optional[str] = None,
    cwd: Optional[Path] = None,
) -> str:
    """
    Generates a clear, informative commit message based on changed files.
    If custom_msg is provided, returns custom_msg directly.
    """
    if custom_msg and custom_msg.strip():
        return custom_msg.strip()

    work_dir = cwd or Path.cwd()

    try:
        status_res = subprocess.run(  # nosec
            ["git", "status", "--porcelain"],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if status_res.returncode != 0 or not status_res.stdout.strip():
            return "Update codebase after validation"

        lines = [
            line.rstrip()
            for line in status_res.stdout.strip().split("\n")
            if line.strip()
        ]
    except Exception as e:
        logger.warning(f"Could not analyze git status for commit message: {e}")
        return "Update codebase after validation"

    # Parse status lines into (status_code, relative_filepath)
    changes = []
    for line in lines:
        if len(line) < 4:
            continue
        status_code = line[:2].strip()
        path_str = line[3:].strip()
        # Handle rename format: "R  old -> new"
        if " -> " in path_str:
            path_str = path_str.split(" -> ")[-1].strip()
        # Remove quotes if present
        if path_str.startswith('"') and path_str.endswith('"'):
            path_str = path_str[1:-1]
        changes.append((status_code, path_str))

    if not changes:
        return "Update codebase after validation"

    action_counts = {"add": 0, "delete": 0, "modify": 0}
    file_basenames = []
    component_dirs = []

    for status, filepath in changes:
        p = Path(filepath)
        filename = p.name
        file_basenames.append(filename)

        if len(p.parts) > 1 and p.parts[0] not in component_dirs:
            component_dirs.append(p.parts[0])

        if "A" in status or "?" in status:
            action_counts["add"] += 1
        elif "D" in status:
            action_counts["delete"] += 1
        else:
            action_counts["modify"] += 1

    # Verb determination
    if (
        action_counts["add"] > 0
        and action_counts["modify"] == 0
        and action_counts["delete"] == 0
    ):
        verb = "Add"
    elif (
        action_counts["delete"] > 0
        and action_counts["add"] == 0
        and action_counts["modify"] == 0
    ):
        verb = "Remove"
    else:
        verb = "Update"

    # Format clear message
    if len(file_basenames) == 1:
        return f"{verb} {file_basenames[0]}"
    elif len(file_basenames) <= 3:
        files_str = ", ".join(file_basenames[:-1]) + f" and {file_basenames[-1]}"
        return f"{verb} {files_str}"
    elif component_dirs:
        if len(component_dirs) == 1:
            dirs_str = component_dirs[0]
        elif len(component_dirs) == 2:
            dirs_str = f"{component_dirs[0]} and {component_dirs[1]}"
        else:
            dirs_str = f"{', '.join(component_dirs[:2])}, and {component_dirs[2]}"
        return f"{verb} {dirs_str} ({len(file_basenames)} files updated)"
    else:
        return f"{verb} {len(file_basenames)} files"

def git_commit_and_push(
    remote: str = "origin",
    target_branch: Optional[str] = None,
    auto_commit: bool = True,
    custom_commit_msg: Optional[str] = None,
    commit_prefix: str = "chore: pre-commit validation passed",
    cwd: Optional[Path] = None,
) -> bool:
    """
    Stages, commits, and pushes current codebase changes to the specified remote and branch.
    Returns True if push succeeds, False on error.
    """
    work_dir = cwd or Path.cwd()
    branch = target_branch if target_branch else get_current_branch(work_dir)

    print_info(f"Target Git Branch: {branch} (Remote: {remote})")

    # Check for uncommitted changes (modified, untracked, or staged)
    if auto_commit:
        status_res = subprocess.run(  # nosec
            ["git", "status", "--porcelain"],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if status_res.returncode == 0 and status_res.stdout.strip():
            commit_msg = generate_commit_message(
                custom_msg=custom_commit_msg,
                commit_prefix=commit_prefix,
                cwd=work_dir,
            )

            print_info("Uncommitted changes detected. Staging files (git add .)...")
            add_res = subprocess.run(  # nosec
                ["git", "add", "."],
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if add_res.returncode != 0:
                print_error(f"Failed to stage changes: {add_res.stderr.strip()}")
                return False

            print_info(f"Creating Git commit: '{commit_msg}'...")
            commit_res = subprocess.run(  # nosec
                ["git", "commit", "-m", commit_msg],
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if commit_res.returncode == 0:
                print_success(f"Commit created successfully: '{commit_msg}'")
            else:
                print_warning(
                    f"Git commit output: {commit_res.stderr.strip() or commit_res.stdout.strip()}"
                )
        else:
            print_info("No uncommitted changes detected. Proceeding with push.")

    # Push to remote branch
    print_info(f"Pushing code to {remote}/{branch}...")
    push_res = subprocess.run(  # nosec
        ["git", "push", remote, branch],
        cwd=work_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if push_res.returncode == 0:
        print_success(
            f"Successfully pushed code to {remote}/{branch}! GitHub Actions CI/CD triggered."
        )
        return True
    else:
        err_msg = push_res.stderr.strip() or push_res.stdout.strip()
        print_error(f"Git push failed to {remote}/{branch}: {err_msg}")
        return False