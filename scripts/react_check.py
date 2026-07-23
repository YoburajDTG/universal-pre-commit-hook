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

    def _get_targets(self) -> list[str]:
        if self.context.changed_files:
            return [
                f
                for f in self.context.changed_files
                if f.endswith((".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".scss"))
            ]
        return ["."]

    def run_formatter(self) -> CommandResult:
        """Runs Prettier in validation/check mode."""
        logger.info("Running Prettier code formatter check...")
        targets = self._get_targets()
        if not targets and self.context.changed_files:
            return CommandResult(
                command="skip",
                exit_code=0,
                stdout="No matching files changed.",
                stderr="",
                duration=0.0,
                success=True,
            )

        prettier_mode = "--write" if self.context.auto_fix else "--check"
        cmd = self.docker_wrap(
            ["npx", "-y", "prettier", prettier_mode] + targets, "node:18-alpine"
        )
        return run_command(cmd, cwd=self.context.project_root)

    def run_linter(self) -> CommandResult:
        """Runs ESLint static code linter."""
        logger.info("Running ESLint code linter...")
        targets = self._get_targets()
        if self.context.changed_files:
            targets = [
                f
                for f in self.context.changed_files
                if f.endswith((".js", ".jsx", ".ts", ".tsx"))
            ]
            if not targets:
                return CommandResult(
                    command="skip",
                    exit_code=0,
                    stdout="No JS/TS files changed.",
                    stderr="",
                    duration=0.0,
                    success=True,
                )

        eslint_cmd = ["npx", "-y", "eslint"]
        if self.context.auto_fix:
            eslint_cmd.append("--fix")
        cmd = self.docker_wrap(eslint_cmd + targets, "node:18-alpine")
        res = run_command(cmd, cwd=self.context.project_root)

        if not res.success and self.context.allow_lint_warnings:
            logger.warning(
                "ESLint auto-fix executed. Proceeding with pipeline (allow_lint_warnings=True)..."
            )
            return CommandResult(
                command=res.command,
                exit_code=0,
                stdout=res.stdout,
                stderr=res.stderr,
                duration=res.duration,
                success=True,
            )
        return res

    def run_build(self) -> CommandResult:
        """Compiles the application into a production bundle with automatic cache recovery."""
        logger.info("Running production build checks...")
        next_dev_cache = self.context.project_root / ".next" / "dev"
        if next_dev_cache.exists():
            try:
                import shutil

                shutil.rmtree(next_dev_cache, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Could not remove stale .next/dev cache: {e}")

        cmd = self.docker_wrap(["npm", "run", "build"], "node:18-alpine")
        res = run_command(cmd, cwd=self.context.project_root)

        if not res.success and (
            ".next" in (res.stdout or res.stderr)
            or "routes.d.ts" in (res.stdout or res.stderr)
        ):
            logger.info(
                "Stale Next.js build cache detected. Purging .next and retrying build..."
            )
            next_dir = self.context.project_root / ".next"
            if next_dir.exists():
                try:
                    import shutil

                    shutil.rmtree(next_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Could not purge .next directory: {e}")
            res = run_command(cmd, cwd=self.context.project_root)

        return res

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
                logger.warning(
                    f"Failed to parse package.json in {self.context.project_root}: {e}"
                )

        if not has_test_script:
            logger.info(
                "No 'test' script detected in package.json. Skipping React test stage."
            )
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

        cmd = self.docker_wrap(["npm", "test"], "node:18-alpine")
        return run_command(
            cmd,
            cwd=self.context.project_root,
            env=env,
        )

    def run_security_scan(self) -> CommandResult:
        """Scans for dependency vulnerabilities using npm audit."""
        logger.info("Running Node dependency security scan...")

        config = self.context.config.security
        if config.npm_audit:
            cmd = self.docker_wrap(["npm", "audit"], "node:18-alpine")
            return run_command(cmd, cwd=self.context.project_root)

        return CommandResult(
            command="react_security_scan",
            exit_code=0,
            stdout="npm audit check is disabled or skipped.",
            stderr="",
            duration=0.0,
            success=True,
        )
