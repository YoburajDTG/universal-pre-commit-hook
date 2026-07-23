import logging

from common import BaseChecker
from utils import CommandResult, run_command

logger = logging.getLogger("universal-precommit")


class RustChecker(BaseChecker):
    @property
    def name(self) -> str:
        return "Rust"

    def detect(self) -> bool:
        # Check for Cargo project marker file
        return (self.context.project_root / "Cargo.toml").exists()

    def run_formatter(self) -> CommandResult:
        logger.info("Running Rust formatter checks...")
        # Formats the codebase using rustfmt
        return run_command(
            ["cargo", "fmt", "--", "--check"], cwd=self.context.project_root
        )

    def run_linter(self) -> CommandResult:
        logger.info("Running Rust static code linter...")
        # Lint checking using clippy
        return run_command(
            ["cargo", "clippy", "--", "-D", "warnings"], cwd=self.context.project_root
        )

    def run_build(self) -> CommandResult:
        logger.info("Building Rust project...")
        # Compiles the cargo package
        return run_command(["cargo", "build", "--check"], cwd=self.context.project_root)

    def run_tests(self) -> CommandResult:
        logger.info("Running Rust test suite...")
        # Runs the unit and integration tests
        return run_command(["cargo", "test"], cwd=self.context.project_root)

    def run_security_scan(self) -> CommandResult:
        logger.info("Running Rust security audit...")
        # Audits Cargo.lock files for vulnerable dependencies (requires cargo-audit)
        if (self.context.project_root / "Cargo.lock").exists():
            return run_command(["cargo", "audit"], cwd=self.context.project_root)
        else:
            logger.warning("Cargo.lock not found. Skipping Rust security audit.")
            return CommandResult(
                command="rust_security_scan_skipped",
                exit_code=0,
                stdout="Cargo.lock not found. Skipping cargo audit.",
                stderr="",
                duration=0.0,
                success=True,
            )

    def run_coverage(self) -> CommandResult:
        logger.info("Running Rust test coverage analysis...")
        # e.g., using cargo-tarpaulin or cargo-llvm-cov
        return run_command(["cargo", "tarpaulin"], cwd=self.context.project_root)
