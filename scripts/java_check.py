#!/usr/bin/env python3
"""
Java project checker implementation for the Universal Pre-Commit Validation Framework.
Supports both Maven and Gradle build tools. Enforces Spotless formatting, Checkstyle linting,
compilation, test executions, OWASP dependency vulnerability scans, and JaCoCo coverage.
"""

import logging
import sys

from common import BaseChecker
from utils import CommandResult, run_command

logger = logging.getLogger("universal-precommit")


class JavaChecker(BaseChecker):
    """Checker for Java projects with Maven or Gradle configuration."""

    @property
    def name(self) -> str:
        return "Java"

    def detect(self) -> bool:
        """Determines if the directory contains Java build configurations."""
        return (
            (self.context.project_root / "pom.xml").exists()
            or (self.context.project_root / "build.gradle").exists()
            or (self.context.project_root / "build.gradle.kts").exists()
        )

    def _is_maven(self) -> bool:
        """Helper to check if Maven is the build tool of choice."""
        return (self.context.project_root / "pom.xml").exists()

    def _get_executable(self, tool: str) -> str:
        """
        Determines the correct binary execution string (including wrapper support)
        adapted to the runtime host operating system (Windows vs Unix-like).
        """
        is_windows = sys.platform.startswith("win")

        if tool == "maven":
            wrapper = "mvnw.cmd" if is_windows else "./mvnw"
            if (
                self.context.project_root / ("mvnw.cmd" if is_windows else "mvnw")
            ).exists():
                return wrapper
            return "mvn"

        elif tool == "gradle":
            wrapper = "gradlew.bat" if is_windows else "./gradlew"
            if (
                self.context.project_root / ("gradlew.bat" if is_windows else "gradlew")
            ).exists():
                return wrapper
            return "gradle"

        return tool

    def run_formatter(self) -> CommandResult:
        """Executes spotless validation / auto-formatting code style checks."""
        logger.info("Running Spotless code formatter...")
        if self._is_maven():
            exec_tool = self._get_executable("maven")
            return run_command(
                [exec_tool, "spotless:apply"], cwd=self.context.project_root
            )
        else:
            exec_tool = self._get_executable("gradle")
            return run_command(
                [exec_tool, "spotlessApply"], cwd=self.context.project_root
            )

    def run_lint(self) -> CommandResult:
        """Executes linting via Checkstyle (Maven) or standard validation check tasks (Gradle)."""
        logger.info("Running Java static code lint checkstyle analysis...")
        if self._is_maven():
            exec_tool = self._get_executable("maven")
            return run_command(
                [exec_tool, "checkstyle:check"], cwd=self.context.project_root
            )
        else:
            exec_tool = self._get_executable("gradle")
            return run_command([exec_tool, "check"], cwd=self.context.project_root)

    def run_build(self) -> CommandResult:
        """Compiles classes and resources without running test suites."""
        logger.info("Compiling Java classes...")
        if self._is_maven():
            exec_tool = self._get_executable("maven")
            # Maven package compiling without test phases
            return run_command(
                [exec_tool, "compile", "test-compile"], cwd=self.context.project_root
            )
        else:
            exec_tool = self._get_executable("gradle")
            return run_command(
                [exec_tool, "build", "-x", "test"], cwd=self.context.project_root
            )

    def run_tests(self) -> CommandResult:
        """Runs JUnit unit and integration tests."""
        logger.info("Running Java unit test suite...")
        if self._is_maven():
            exec_tool = self._get_executable("maven")
            return run_command([exec_tool, "test"], cwd=self.context.project_root)
        else:
            exec_tool = self._get_executable("gradle")
            return run_command([exec_tool, "test"], cwd=self.context.project_root)

    def run_security_scan(self) -> CommandResult:
        """Runs dependency security analysis using OWASP Dependency Check if enabled."""
        config = self.context.config.security
        if not config.owasp_dependency_check:
            return CommandResult(
                command="java_security_scan",
                exit_code=0,
                stdout="Java OWASP dependency check is disabled or skipped.",
                stderr="",
                duration=0.0,
                success=True,
            )

        logger.info("Running OWASP dependency check vulnerability scan...")
        if self._is_maven():
            exec_tool = self._get_executable("maven")
            return run_command(
                [exec_tool, "dependency-check:check"], cwd=self.context.project_root
            )
        else:
            exec_tool = self._get_executable("gradle")
            return run_command(
                [exec_tool, "dependencyCheckAnalyze"], cwd=self.context.project_root
            )

    def run_coverage(self) -> CommandResult:
        """Runs coverage report generation (requires JaCoCo configured)."""
        logger.info("Running JaCoCo test coverage reports...")
        if self._is_maven():
            exec_tool = self._get_executable("maven")
            return run_command(
                [exec_tool, "jacoco:report"], cwd=self.context.project_root
            )
        else:
            exec_tool = self._get_executable("gradle")
            return run_command(
                [exec_tool, "jacocoTestReport"], cwd=self.context.project_root
            )
