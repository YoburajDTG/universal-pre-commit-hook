#!/usr/bin/env python3
"""
Utility module for the Universal Pre-Commit Validation Framework.
Provides logging setup, colorized CLI helpers, and robust process execution.
"""

import logging
import subprocess  # nosec B404
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

    handlers: List[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        # Ensure parent folder for the log file exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=log_level, format=log_format, handlers=handlers, force=True
    )


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

    try:
        # Run process via subprocess
        process = subprocess.run(  # nosec B602 B603 B607
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=isinstance(cmd, str),  # shell=True only if raw string
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
