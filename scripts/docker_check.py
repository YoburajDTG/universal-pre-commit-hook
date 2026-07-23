import logging

from common import BaseChecker
from utils import CommandResult, run_command

logger = logging.getLogger("universal-precommit")


class DockerChecker(BaseChecker):
    """Checker for Dockerfiles."""

    @property
    def name(self) -> str:
        return "Docker"

    def detect(self) -> bool:
        """Determines if there is a Dockerfile."""
        return (self.context.project_root / "Dockerfile").exists()

    def run_formatter(self) -> CommandResult:
        """No standard docker formatter."""
        return CommandResult(
            command="docker_format",
            exit_code=0,
            stdout="Formatting skipped - no standard Dockerfile formatter used.",
            stderr="",
            duration=0.0,
            success=True,
        )

    def run_linter(self) -> CommandResult:
        """Runs hadolint static code linter."""
        logger.info("Running hadolint linter...")

        if self.context.changed_files:
            targets = [f for f in self.context.changed_files if "Dockerfile" in f]
            if not targets:
                return CommandResult(
                    command="skip",
                    exit_code=0,
                    stdout="No Dockerfiles changed.",
                    stderr="",
                    duration=0.0,
                    success=True,
                )
        else:
            targets = ["Dockerfile"]

        cmd = self.docker_wrap(
            ["hadolint"] + targets, "hadolint/hadolint:latest-debian"
        )
        return run_command(cmd, cwd=self.context.project_root)

    def run_build(self) -> CommandResult:
        """No build stage for Dockerfile checks in pre-commit (too heavy)."""
        return CommandResult(
            command="docker_build",
            exit_code=0,
            stdout="Skipped build for Dockerfile.",
            stderr="",
            duration=0.0,
            success=True,
        )

    def run_tests(self) -> CommandResult:
        """No test stage."""
        return CommandResult(
            command="docker_test",
            exit_code=0,
            stdout="Skipped tests for Dockerfile.",
            stderr="",
            duration=0.0,
            success=True,
        )
