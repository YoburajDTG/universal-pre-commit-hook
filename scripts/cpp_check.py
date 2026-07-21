import logging
from common import BaseChecker
from utils import CommandResult, run_command

logger = logging.getLogger("universal-precommit")

class CppChecker(BaseChecker):
    """Checker for C/C++ repositories using clang tools."""

    @property
    def name(self) -> str:
        return "C++"

    def detect(self) -> bool:
        """Determines if the directory is a C/C++ project."""
        return (
            (self.context.project_root / "CMakeLists.txt").exists()
            or (self.context.project_root / "Makefile").exists()
        )

    def _get_targets(self) -> list[str]:
        if self.context.changed_files:
            return [f for f in self.context.changed_files if f.endswith((".c", ".cpp", ".h", ".hpp", ".cc", ".cxx"))]
        return ["."]

    def run_formatter(self) -> CommandResult:
        """Runs clang-format in check mode."""
        logger.info("Running clang-format check...")
        targets = self._get_targets()
        if not targets and self.context.changed_files:
            return CommandResult(command="skip", exit_code=0, stdout="No C/C++ files changed.", stderr="", duration=0.0, success=True)
        if targets == ["."]:
            targets = []
            for ext in ("*.c", "*.cpp", "*.h", "*.hpp", "*.cc", "*.cxx"):
                targets.extend([str(p.relative_to(self.context.project_root)) for p in self.context.project_root.rglob(ext)])
            if not targets:
                return CommandResult(command="skip", exit_code=0, stdout="No C/C++ files found.", stderr="", duration=0.0, success=True)

        cmd = self.docker_wrap(["clang-format", "--dry-run", "-Werror"] + targets, "silkeh/clang:latest")
        return run_command(cmd, cwd=self.context.project_root)

    def run_linter(self) -> CommandResult:
        """Runs clang-tidy static code linter."""
        logger.info("Running clang-tidy linter...")
        targets = self._get_targets()
        
        if not targets and self.context.changed_files:
            return CommandResult(command="skip", exit_code=0, stdout="No C/C++ files changed.", stderr="", duration=0.0, success=True)
            
        if targets == ["."]:
            targets = []
            for ext in ("*.c", "*.cpp", "*.h", "*.hpp", "*.cc", "*.cxx"):
                targets.extend([str(p.relative_to(self.context.project_root)) for p in self.context.project_root.rglob(ext)])
            if not targets:
                return CommandResult(command="skip", exit_code=0, stdout="No C/C++ files found.", stderr="", duration=0.0, success=True)

        cmd = self.docker_wrap(["clang-tidy"] + targets, "silkeh/clang:latest")
        return run_command(cmd, cwd=self.context.project_root)

    def run_build(self) -> CommandResult:
        """Build stage - assume make if Makefile exists."""
        if (self.context.project_root / "Makefile").exists():
            cmd = self.docker_wrap(["make", "-j"], "gcc:latest")
            return run_command(cmd, cwd=self.context.project_root)
            
        return CommandResult(
            command="cpp_build",
            exit_code=0,
            stdout="Skipped build - no generic Makefile found.",
            stderr="",
            duration=0.0,
            success=True,
        )

    def run_tests(self) -> CommandResult:
        """Tests stage - assumes make test."""
        if (self.context.project_root / "Makefile").exists():
            cmd = self.docker_wrap(["make", "test"], "gcc:latest")
            return run_command(cmd, cwd=self.context.project_root)
            
        return CommandResult(
            command="cpp_test",
            exit_code=0,
            stdout="Skipped tests - no generic Makefile found.",
            stderr="",
            duration=0.0,
            success=True,
        )