import logging
import sys

from common import BaseChecker
from utils import CommandResult, run_command

logger = logging.getLogger("universal-precommit")


class PythonChecker(BaseChecker):
    """Checker for Python repositories using modern packaging and standard tools."""

    @property
    def name(self) -> str:
        return "Python"

    def detect(self) -> bool:
        """Determines if the current directory is a Python project."""
        return (
            (self.context.project_root / "pyproject.toml").exists()
            or (self.context.project_root / "requirements.txt").exists()
            or (self.context.project_root / "setup.py").exists()
        )

    def _get_python_executable(self) -> str:
        """
        Attempts to locate the virtualenv python executable within the project.
        Falls back to sys.executable if no local virtualenv is discovered.
        """
        for venv_name in [".venv", "venv", "env"]:
            venv_dir = self.context.project_root / venv_name
            if venv_dir.is_dir():
                # Check Windows path structure
                windows_py = venv_dir / "Scripts" / "python.exe"
                if windows_py.exists():
                    return str(windows_py.resolve())

                # Check Unix/macOS path structure
                unix_py = venv_dir / "bin" / "python"
                if unix_py.exists():
                    return str(unix_py.resolve())

        return sys.executable

    def run_formatter(self) -> CommandResult:
        """Runs black and isort in validation/check-only mode."""
        logger.info("Running Python code formatter checks...")
        py_exec = self._get_python_executable()

        # Run Black --check
        black_res = run_command(
            [py_exec, "-m", "black", "--check", "."], cwd=self.context.project_root
        )
        if not black_res.success:
            return black_res

        # Run Isort --check-only
        isort_res = run_command(
            [py_exec, "-m", "isort", "--check-only", "."], cwd=self.context.project_root
        )
        return isort_res

    def run_linter(self) -> CommandResult:
        """Runs Ruff for ultra-fast linting checks."""
        logger.info("Running Python static code linter...")
        py_exec = self._get_python_executable()
        return run_command(
            [py_exec, "-m", "ruff", "check", "."], cwd=self.context.project_root
        )

    def run_build(self) -> CommandResult:
        """
        Verifies Python source file syntax via bytecode compilation.
        Acts as the 'build' stage for interpreted Python.
        """
        logger.info("Verifying Python syntax compile checks...")

        # Find all python files excluding virtual environments and build directories
        py_files = []
        for file_path in self.context.project_root.rglob("*.py"):
            parts = file_path.parts
            if any(p in parts for p in [".venv", "venv", "env", "build", "dist"]):
                continue
            py_files.append(str(file_path.relative_to(self.context.project_root)))

        if not py_files:
            return CommandResult(
                command="py_compile",
                exit_code=0,
                stdout="No python files to verify.",
                stderr="",
                duration=0.0,
                success=True,
            )

        py_exec = self._get_python_executable()
        # Compile all found source files
        return run_command(
            [py_exec, "-m", "py_compile"] + py_files, cwd=self.context.project_root
        )

    def run_tests(self) -> CommandResult:
        """Runs unit and integration tests using pytest."""
        logger.info("Running Python unit test suite...")
        py_exec = self._get_python_executable()
        return run_command([py_exec, "-m", "pytest"], cwd=self.context.project_root)

    def run_security_scan(self) -> CommandResult:
        """Executes security scans using Bandit and pip-audit based on configuration."""
        logger.info("Running Python security scanning stages...")
        config = self.context.config.security
        py_exec = self._get_python_executable()

        # 1. Bandit check (SAST)
        if config.bandit:
            logger.info("Running Bandit security linter...")
            bandit_res = run_command(
                [
                    py_exec,
                    "-m",
                    "bandit",
                    "-r",
                    ".",
                    "-x",
                    "./.venv,./venv,./env,./tests",
                ],
                cwd=self.context.project_root,
            )
            if not bandit_res.success:
                return bandit_res

        # 2. pip-audit check (Dependency vulnerability scanner)
        if config.pip_audit:
            logger.info("Running pip-audit vulnerability checks...")
            pip_audit_cmd = [py_exec, "-m", "pip_audit"]
            if (self.context.project_root / "requirements.txt").exists():
                pip_audit_cmd += ["-r", "requirements.txt"]

            audit_res = run_command(pip_audit_cmd, cwd=self.context.project_root)
            if not audit_res.success:
                return audit_res

        return CommandResult(
            command="python_security_scan",
            exit_code=0,
            stdout="All enabled Python security scans passed successfully.",
            stderr="",
            duration=0.0,
            success=True,
        )
