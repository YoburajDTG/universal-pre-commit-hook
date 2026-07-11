#!/usr/bin/env python3
"""
Common base classes and context models for language-specific pre-commit validation.
Follows SOLID design principles to enable framework scalability.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from utils import CommandResult

from config import AppConfig


@dataclass(frozen=True)
class ValidationContext:
    """Carries configuration and environment details across checkers."""

    project_root: Path
    config: AppConfig
    log_file: Optional[Path] = None


class BaseChecker(ABC):
    """
    Abstract Base Class for all language-specific project checkers.
    Each language checker must implement detection rules and stages.
    """

    def __init__(self, context: ValidationContext) -> None:
        self.context = context

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the user-friendly name of the language checker."""
        pass

    @abstractmethod
    def detect(self) -> bool:
        """
        Scans the project_root to see if this project contains markers for the language.
        """
        pass

    def run_stage(self, stage_name: str) -> CommandResult:
        """
        Executes a specific stage validation. If the stage is not enabled or
        not implemented by the checker, it returns a skipped placeholder success result.
        """
        # Determine if stage is enabled globally
        stage_enabled = getattr(self.context.config.stages, stage_name, True)
        if not stage_enabled:
            return CommandResult(
                command=f"skip_{self.name}_{stage_name}",
                exit_code=0,
                stdout=f"Stage '{stage_name}' disabled in config.yaml",
                stderr="",
                duration=0.0,
                success=True,
            )

        # Map stage string to execution method
        method_name = f"run_{stage_name}"
        if not hasattr(self, method_name):
            return CommandResult(
                command=f"unimplemented_{self.name}_{stage_name}",
                exit_code=0,
                stdout=f"Stage '{stage_name}' not implemented for {self.name}",
                stderr="",
                duration=0.0,
                success=True,
            )

        method = getattr(self, method_name)
        return method()

    @abstractmethod
    def run_formatter(self) -> CommandResult:
        """Checks/applies code formatting rules."""
        pass

    @abstractmethod
    def run_lint(self) -> CommandResult:
        """Checks/applies static analysis linting rules."""
        pass

    @abstractmethod
    def run_build(self) -> CommandResult:
        """Compiles or builds the software artifact."""
        pass

    @abstractmethod
    def run_tests(self) -> CommandResult:
        """Runs the unit/integration test suites."""
        pass

    @abstractmethod
    def run_security_scan(self) -> CommandResult:
        """Executes dependency auditing or SAST scans."""
        pass

    @abstractmethod
    def run_coverage(self) -> CommandResult:
        """Evaluates test coverage metric checks."""
        pass
