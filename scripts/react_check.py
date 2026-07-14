#!/usr/bin/env python3
"""
React/TypeScript project checker implementation for the Universal Pre-Commit Validation Framework.
Enforces styling (Prettier in validation mode), linting (ESLint), compilation (npm run build),
unit testing (npm test in CI mode if configured), and optional security auditing (npm audit).
"""

import json
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
        """Runs tests in a non-interactive CI mode if configured in package.json."""
        logger.info("Running React test suite...")

        # Safely parse package.json to verify if a "test" script is defined
        pkg_json_path = self.context.project_root / "package.json"
        has_test_script = False
        if pkg_json_path.exists():
            try:
                with open(pkg_json_path, "r", encoding="utf-8") as f:
                    pkg_data = json.load(f)
                has_test_script = "test" in pkg_data.get("scripts", {})
            except Exception as e:
                logger.warning(f"Failed to parse package.json in {self.context.project_root}: {e}")

        if not has_test_script:
            logger.info("No 'test' script detected in package.json. Skipping React test stage.")
            return CommandResult(
                command="skip_react_tests",
                exit_code=0,
                stdout="Skipped: No 'test' script defined in package.json.",
                stderr="",
                duration=0.0,
                success=True,
            )

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
