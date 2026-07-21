#!/usr/bin/env python3
"""
Python project checker implementation for the Universal Pre-Commit Validation Framework.
Enforces styling (Black/Isort in validation mode), linting (Ruff), unit testing (Pytest),
and optional security auditing (Bandit/pip-audit).
"""

import logging
import sys

from common import BaseChecker
from utils import CommandResult, run_command

logger = logging.getLogger("universal-precommit")


class PythonChecker(BaseChecker):
    """Checker for Python repositories using modern packaging and standard tools."""

    @property
    def name(self) -> str:
        return "Python"

    def detect(self) -> bool:
        """Determines if the current directory is a Python project."""
        return (
            (self.context.project_root / "pyproject.toml").exists()
            or (self.context.project_root / "requirements.txt").exists()
            or (self.context.project_root / "setup.py").exists()
        )

    def _get_python_executable(self) -> str:
        """
        Attempts to locate the virtualenv python executable within the project.
        Falls back to sys.executable if no local virtualenv is discovered.
        """
        if self.context.config.use_docker:
            return "python"
            
        for venv_name in [".venv", "venv", "env"]:
            venv_dir = self.context.project_root / venv_name
            if venv_dir.is_dir():
                # Check Windows path structure
                windows_py = venv_dir / "Scripts" / "python.exe"
                if windows_py.exists():
                    return str(windows_py.resolve())

                # Check Unix/macOS path structure
                unix_py = venv_dir / "bin" / "python"
                if unix_py.exists():
                    return str(unix_py.resolve())

        return sys.executable

    def _get_base_python(self) -> str:
        if self.context.config.use_docker:
            return "python"
        return sys.executable

    def _get_targets(self) -> list[str]:
        if self.context.changed_files:
            targets = [f for f in self.context.changed_files if f.endswith(".py")]
            return targets
        return ["."]

    def run_formatter(self) -> CommandResult:
        """Runs black and isort in validation/check-only mode using pre-commit's environment python."""
        logger.info("Running Python code formatter checks...")
        py_exec = self._get_base_python()
        targets = self._get_targets()
        
        if not targets and self.context.changed_files:
            return CommandResult(command="skip", exit_code=0, stdout="No python files changed.", stderr="", duration=0.0, success=True)

        cmd_black = self.docker_wrap([py_exec, "-m", "black", "--check"] + targets, "python:3.12-slim")
        black_res = run_command(cmd_black, cwd=self.context.project_root)
        if not black_res.success:
            return black_res

        cmd_isort = self.docker_wrap([py_exec, "-m", "isort", "--check-only"] + targets, "python:3.12-slim")
        return run_command(cmd_isort, cwd=self.context.project_root)

    def run_linter(self) -> CommandResult:
        """Runs Ruff for ultra-fast linting checks using pre-commit's environment python."""
        logger.info("Running Python static code linter...")
        py_exec = self._get_base_python()
        targets = self._get_targets()

        if not targets and self.context.changed_files:
            return CommandResult(command="skip", exit_code=0, stdout="No python files changed.", stderr="", duration=0.0, success=True)

        cmd_ruff = self.docker_wrap([py_exec, "-m", "ruff", "check"] + targets, "python:3.12-slim")
        return run_command(cmd_ruff, cwd=self.context.project_root)

    def run_build(self) -> CommandResult:
        """
        Verifies Python source file syntax via bytecode compilation using the project's Python runtime.
        Acts as the 'build' stage for interpreted Python.
        """
        logger.info("Verifying Python syntax compile checks...")

        # Find all python files excluding virtual environments and build directories
        py_files = []
        for file_path in self.context.project_root.rglob("*.py"):
            parts = file_path.parts
            if any(p in parts for p in [".venv", "venv", "env", "build", "dist"]):
                continue
            py_files.append(str(file_path.relative_to(self.context.project_root)))

        if not py_files:
            return CommandResult(
                command="py_compile",
                exit_code=0,
                stdout="No python files to verify.",
                stderr="",
                duration=0.0,
                success=True,
            )

        py_exec = self._get_python_executable()
        cmd_compile = self.docker_wrap([py_exec, "-m", "py_compile"] + py_files, "python:3.12-slim")
        return run_command(cmd_compile, cwd=self.context.project_root)

    def run_tests(self) -> CommandResult:
        """Runs unit and integration tests using pytest within the project's Python runtime."""
        logger.info("Running Python unit test suite...")
        py_exec = self._get_python_executable()
        cmd_pytest = self.docker_wrap([py_exec, "-m", "pytest"], "python:3.12-slim")
        res = run_command(cmd_pytest, cwd=self.context.project_root)
        
        # Pytest exit code 5 means "no tests were collected", which is safe to treat as success in pre-commit hooks
        if res.exit_code == 5:
            return CommandResult(
                command=res.command,
                exit_code=0,
                stdout=res.stdout,
                stderr=res.stderr,
                duration=res.duration,
                success=True,
            )
        return res

    def run_security_scan(self) -> CommandResult:
        """Executes security scans using Bandit and pip-audit based on configuration."""
        logger.info("Running Python security scanning stages...")
        config = self.context.config.security
        py_exec = self._get_base_python()

        # 1. Bandit check (SAST)
        if config.bandit:
            logger.info("Running Bandit security linter...")
            cmd_bandit = self.docker_wrap([
                py_exec, "-m", "bandit", "-r", ".", "-x", "./.venv,./venv,./env,./tests"
            ], "python:3.12-slim")
            bandit_res = run_command(cmd_bandit, cwd=self.context.project_root)
            if not bandit_res.success:
                return bandit_res

        # 2. pip-audit check (Dependency vulnerability scanner)
        if config.pip_audit:
            logger.info("Running pip-audit vulnerability checks...")
            pip_audit_cmd = [py_exec, "-m", "pip_audit"]
            if (self.context.project_root / "requirements.txt").exists():
                pip_audit_cmd += ["-r", "requirements.txt"]

            cmd_audit = self.docker_wrap(pip_audit_cmd, "python:3.12-slim")
            audit_res = run_command(cmd_audit, cwd=self.context.project_root)
            if not audit_res.success:
                return audit_res

        return CommandResult(
            command="python_security_scan",
            exit_code=0,
            stdout="All enabled Python security scans passed successfully.",
            stderr="",
            duration=0.0,
            success=True,
        )