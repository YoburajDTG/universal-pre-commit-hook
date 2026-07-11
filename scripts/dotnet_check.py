#!/usr/bin/env python3
"""
.NET C# project checker implementation for the Universal Pre-Commit Validation Framework.
Enforces code style (dotnet format), compilation (dotnet build), testing (dotnet test),
and package vulnerability assessments (dotnet list package --vulnerable).
"""

import logging
from common import BaseChecker, ValidationContext
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
        """Invokes dotnet format to fix layout/whitespace/style conventions."""
        logger.info("Running dotnet format to fix styles and layout...")
        return run_command(["dotnet", "format"], cwd=self.context.project_root)

    def run_lint(self) -> CommandResult:
        """Verifies styling and syntax rules without writing changes."""
        logger.info("Running dotnet style verification (linter)...")
        # dotnet format --verify-no-changes acts as formatting check linter
        return run_command(["dotnet", "format", "--verify-no-changes"], cwd=self.context.project_root)

    def run_build(self) -> CommandResult:
        """Compiles the solution or project."""
        logger.info("Running dotnet build...")
        return run_command(["dotnet", "build", "--configuration", "Release"], cwd=self.context.project_root)

    def run_tests(self) -> CommandResult:
        """Runs the unit/integration test suites."""
        logger.info("Running dotnet test suite...")
        return run_command(["dotnet", "test", "--no-build", "--configuration", "Release"], cwd=self.context.project_root)

    def run_security_scan(self) -> CommandResult:
        """Scans packages for known vulnerabilities via dotnet list package."""
        logger.info("Scanning for vulnerable .NET dependencies...")
        
        # Check packages for security warnings (available in modern .NET CLI)
        return run_command(["dotnet", "list", "package", "--vulnerable"], cwd=self.context.project_root)

    def run_coverage(self) -> CommandResult:
        """Evaluates code coverage for dotnet tests."""
        logger.info("Evaluating .NET test coverage metrics...")
        # Collect coverage using standard cross-platform logger or package Coverlet
        return run_command(
            ["dotnet", "test", "--collect:\"XPlat Code Coverage\"", "--configuration", "Release"],
            cwd=self.context.project_root
        )
