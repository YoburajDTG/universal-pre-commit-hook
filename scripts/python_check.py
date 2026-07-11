#!/usr/bin/env python3
"""
Python project checker implementation for the Universal Pre-Commit Validation Framework.
Enforces PEP8, styling (Black/Isort), linting (Ruff), unit testing (Pytest),
security auditing (Bandit/pip-audit), and coverage.
"""

import logging
from common import BaseChecker, ValidationContext
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

    def run_formatter(self) -> CommandResult:
        """Runs black and isort to format Python code."""
        logger.info("Running Python code formatter checks...")
        
        # Run Black
        black_res = run_command(["black", "."], cwd=self.context.project_root)
        if not black_res.success:
            return black_res
            
        # Run Isort
        isort_res = run_command(["isort", "."], cwd=self.context.project_root)
        return isort_res

    def run_lint(self) -> CommandResult:
        """Runs Ruff for ultra-fast linting checks."""
        logger.info("Running Python static code linter...")
        return run_command(["ruff", "check", "."], cwd=self.context.project_root)

    def run_build(self) -> CommandResult:
        """
        Verifies Python source file syntax via bytecode compilation.
        Acts as the 'build' stage for interpreted Python.
        """
        logger.info("Verifying Python syntax compile checks...")
        
        # Find all python files excluding virtual environments
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
                success=True
            )
            
        # Compile all found source files
        return run_command(["python", "-m", "py_compile"] + py_files, cwd=self.context.project_root)

    def run_tests(self) -> CommandResult:
        """Runs unit and integration tests using pytest."""
        logger.info("Running Python unit test suite...")
        return run_command(["pytest"], cwd=self.context.project_root)

    def run_security_scan(self) -> CommandResult:
        """Executes security scans using Bandit and pip-audit based on configuration."""
        logger.info("Running Python security scanning stages...")
        config = self.context.config.security

        # 1. Bandit check (SAST)
        if config.bandit:
            logger.info("Running Bandit security linter...")
            bandit_res = run_command(["bandit", "-r", "."], cwd=self.context.project_root)
            if not bandit_res.success:
                return bandit_res

        # 2. pip-audit check (Dependency vulnerability scanner)
        if config.pip_audit:
            logger.info("Running pip-audit vulnerability checks...")
            # Run pip-audit against current virtualenv or requirements.txt
            pip_audit_cmd = ["pip-audit"]
            if (self.context.project_root / "requirements.txt").exists():
                pip_audit_cmd += ["-r", "requirements.txt"]
            
            audit_res = run_command(pip_audit_cmd, cwd=self.context.project_root)
            if not audit_res.success:
                return audit_res

        return CommandResult(
            command="python_security_scan",
            exit_code=0,
            stdout="All enabled Python security scans passed successfully.",
            stderr="",
            duration=0.0,
            success=True
        )

    def run_coverage(self) -> CommandResult:
        """Runs pytest with coverage reports enabled."""
        logger.info("Checking Python test coverage reports...")
        return run_command(["pytest", "--cov=.", "--cov-report=term-missing"], cwd=self.context.project_root)
