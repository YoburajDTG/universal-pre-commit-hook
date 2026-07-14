import logging

from common import BaseChecker
from utils import CommandResult, run_command

logger = logging.getLogger("universal-precommit")


class DotNetChecker(BaseChecker):
    """Checker for .NET applications using dotnet CLI."""

    @property
    def name(self) -> str:
        return ".NET"

    def detect(self) -> bool:
        """Determines if the directory is a .NET project by checking for solutions/projects."""
        csproj_files = list(self.context.project_root.glob("*.csproj"))
        sln_files = list(self.context.project_root.glob("*.sln"))
        return len(csproj_files) > 0 or len(sln_files) > 0

    def run_formatter(self) -> CommandResult:
        """Invokes dotnet format in check-only validation mode."""
        logger.info("Running dotnet format verification...")
        return run_command(
            ["dotnet", "format", "--verify-no-changes"], cwd=self.context.project_root
        )

    def run_linter(self) -> CommandResult:
        """Skips the linter stage since no dedicated C# linter is configured (Roslyn runs during build)."""
        logger.info("Skipping dotnet linter stage (no dedicated linter configured).")
        return CommandResult(
            command="skip_dotnet_linter",
            exit_code=0,
            stdout="Skipped: No dedicated C# standalone linter configured.",
            stderr="",
            duration=0.0,
            success=True,
        )

    def run_build(self) -> CommandResult:
        """Compiles the solution or project."""
        logger.info("Running dotnet build...")
        return run_command(["dotnet", "build"], cwd=self.context.project_root)

    def run_tests(self) -> CommandResult:
        """Runs the unit/integration test suites."""
        logger.info("Running dotnet test suite...")
        return run_command(["dotnet", "test"], cwd=self.context.project_root)

    def run_security_scan(self) -> CommandResult:
        """Skips dependency auditing for .NET as no default tool is requested."""
        return CommandResult(
            command="skip_dotnet_security",
            exit_code=0,
            stdout="Skipped: No .NET security auditing tool configured.",
            stderr="",
            duration=0.0,
            success=True,
        )
