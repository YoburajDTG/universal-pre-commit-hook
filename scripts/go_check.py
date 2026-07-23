import logging

from common import BaseChecker
from utils import CommandResult, run_command

logger = logging.getLogger("universal-precommit")


class GoChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "Go"

    def detect(self) -> bool:
        # Check for Go project marker file
        return (self.context.project_root / "go.mod").exists()

    def run_formatter(self) -> CommandResult:
        logger.info("Running Go formatter checks...")
        if self.context.changed_files and not self.get_matching_changed_files(
            (".go", "go.mod")
        ):
            return CommandResult(
                command="skip",
                exit_code=0,
                stdout="No Go files changed.",
                stderr="",
                duration=0.0,
                success=True,
            )
        return run_command(["go", "fmt", "./..."], cwd=self.context.project_root)

    def run_linter(self) -> CommandResult:
        logger.info("Running Go static code linter...")
        if self.context.changed_files and not self.get_matching_changed_files(
            (".go", "go.mod")
        ):
            return CommandResult(
                command="skip",
                exit_code=0,
                stdout="No Go files changed.",
                stderr="",
                duration=0.0,
                success=True,
            )
        return run_command(["golangci-lint", "run"], cwd=self.context.project_root)

    def run_build(self) -> CommandResult:
        logger.info("Building Go project...")
        return run_command(["go", "build", "./..."], cwd=self.context.project_root)

    def run_tests(self) -> CommandResult:
        logger.info("Running Go test suite...")
        return run_command(["go", "test", "./..."], cwd=self.context.project_root)

    def run_security_scan(self) -> CommandResult:
        logger.info("Running Go security audit...")
        # e.g., using gosec
        if (self.context.project_root / "go.sum").exists():
            return run_command(["gosec", "./..."], cwd=self.context.project_root)
        else:
            logger.warning("go.sum not found. Skipping Go security audit.")
            return CommandResult(
                command="go_security_scan_skipped",
                exit_code=0,
                stdout="go.sum not found. Skipping gosec scan.",
                stderr="",
                duration=0.0,
                success=True,
            )

    def run_coverage(self) -> CommandResult:
        logger.info("Running Go test coverage analysis...")
        return run_command(
            ["go", "test", "-coverprofile=coverage.out", "./..."],
            cwd=self.context.project_root,
        )
