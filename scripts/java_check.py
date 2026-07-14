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
            wrapper = "mvnw.cmd" if is_windows else "mvnw"
            wrapper_path = self.context.project_root / wrapper
            if wrapper_path.exists():
                return str(wrapper_path.resolve())
            return "mvn"

        elif tool == "gradle":
            wrapper = "gradlew.bat" if is_windows else "gradlew"
            wrapper_path = self.context.project_root / wrapper
            if wrapper_path.exists():
                return str(wrapper_path.resolve())
            return "gradle"

        return tool

    def run_formatter(self) -> CommandResult:
        """Executes spotless validation check-only style checks."""
        logger.info("Running Spotless code formatter checks...")
        if self._is_maven():
            exec_tool = self._get_executable("maven")
            return run_command(
                [exec_tool, "spotless:check"], cwd=self.context.project_root
            )
        else:
            exec_tool = self._get_executable("gradle")
            return run_command(
                [exec_tool, "spotlessCheck"], cwd=self.context.project_root
            )

    def run_linter(self) -> CommandResult:
        """Executes linting via Checkstyle."""
        logger.info("Running Java static code lint checkstyle analysis...")
        if self._is_maven():
            exec_tool = self._get_executable("maven")
            return run_command(
                [exec_tool, "checkstyle:check"], cwd=self.context.project_root
            )
        else:
            exec_tool = self._get_executable("gradle")
            return run_command(
                [exec_tool, "checkstyleMain"], cwd=self.context.project_root
            )

    def run_build(self) -> CommandResult:
        """Compiles classes and resources."""
        logger.info("Compiling Java classes...")
        if self._is_maven():
            exec_tool = self._get_executable("maven")
            return run_command([exec_tool, "compile"], cwd=self.context.project_root)
        else:
            exec_tool = self._get_executable("gradle")
            return run_command([exec_tool, "assemble"], cwd=self.context.project_root)

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
