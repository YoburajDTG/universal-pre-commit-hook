#!/usr/bin/env python3
"""
React/TypeScript project checker implementation for the Universal Pre-Commit Validation Framework.
Enforces styling (Prettier in validation mode), linting (ESLint), compilation (npm run build),
unit testing (npm test in CI mode), and optional security auditing (npm audit).
"""

import logging
import os

from common import BaseChecker
from utils import CommandResult, run_command

logger = logging.getLogger("universal-precommit")


class ReactChecker(BaseChecker):
    """Checker for React/JavaScript/TypeScript repositories using npm and node tools."""

    @property
    def name(self) -> str:
        return "React"

    def detect(self) -> bool:
        """Determines if the directory is a JavaScript/TypeScript/React project."""
        return (self.context.project_root / "package.json").exists()

    def run_formatter(self) -> CommandResult:
        """Runs Prettier in validation/check mode."""
        logger.info("Running Prettier code formatter check...")
        return run_command(
            ["npx", "prettier", "--check", "."], cwd=self.context.project_root
        )

    def run_linter(self) -> CommandResult:
        """Runs ESLint static code linter."""
        logger.info("Running ESLint code linter...")
        return run_command(["npx", "eslint", "."], cwd=self.context.project_root)

    def run_build(self) -> CommandResult:
        """Compiles the application into a production bundle."""
        logger.info("Running production build checks...")
        return run_command(["npm", "run", "build"], cwd=self.context.project_root)

    def run_tests(self) -> CommandResult:
        """Runs tests in a non-interactive CI mode."""
        logger.info("Running React test suite...")

        # Inject CI=true to prevent Jest/Vitest from starting interactive watch mode
        env = os.environ.copy()
        env["CI"] = "true"

        return run_command(
            ["npm", "test"],
            cwd=self.context.project_root,
            env=env,
        )

    def run_security_scan(self) -> CommandResult:
        """Scans for dependency vulnerabilities using npm audit."""
        logger.info("Running Node dependency security scan...")

        config = self.context.config.security
        if config.npm_audit:
            return run_command(["npm", "audit"], cwd=self.context.project_root)

        return CommandResult(
            command="react_security_scan",
            exit_code=0,
            stdout="npm audit check is disabled or skipped.",
            stderr="",
            duration=0.0,
            success=True,
        )
