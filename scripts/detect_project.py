#!/usr/bin/env python3
"""
Project detection module for the Universal Pre-Commit Validation Framework.
Scans the workspace to identify Python, React, .NET, or Java projects,
handling monorepos and multi-language structures gracefully.
"""

import logging
from pathlib import Path
from typing import List, Set

from common import BaseChecker, ValidationContext
from python_check import PythonChecker
from react_check import ReactChecker
from dotnet_check import DotNetChecker
from java_check import JavaChecker

logger = logging.getLogger("universal-precommit")

# Directories that should be skipped during project discovery scans
IGNORED_DIRS = {
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".git",
    ".github",
    "bin",
    "obj",
    "target",
    "build",
    ".gradle",
    ".idea",
    ".vscode",
    "dist",
    "out"
}


def detect_projects(context: ValidationContext) -> List[BaseChecker]:
    """
    Scans the repository to identify code bases.
    Returns a list of initialized language checkers with appropriate sub-roots.
    """
    detected_checkers: List[BaseChecker] = []
    root = context.project_root
    
    # Track paths that have already been matched to prevent duplicates
    detected_paths: Set[Path] = set()

    # Define a helper for directory scanning (up to depth 3 to avoid deep tree crawls)
    def scan_dir(current_dir: Path, depth: int = 0) -> None:
        if depth > 3:
            return
            
        try:
            # Check for Python markers
            if (current_dir / "pyproject.toml").exists() or (current_dir / "requirements.txt").exists():
                if current_dir not in detected_paths:
                    logger.info(f"Detected Python project at: {current_dir.relative_to(root) if current_dir != root else '.'}")
                    sub_context = ValidationContext(
                        project_root=current_dir,
                        config=context.config,
                        log_file=context.log_file
                    )
                    detected_checkers.append(PythonChecker(sub_context))
                    detected_paths.add(current_dir)

            # Check for React markers
            if (current_dir / "package.json").exists():
                if current_dir not in detected_paths:
                    logger.info(f"Detected React/JS project at: {current_dir.relative_to(root) if current_dir != root else '.'}")
                    sub_context = ValidationContext(
                        project_root=current_dir,
                        config=context.config,
                        log_file=context.log_file
                    )
                    detected_checkers.append(ReactChecker(sub_context))
                    detected_paths.add(current_dir)

            # Check for .NET markers (check for sln or csproj)
            dotnet_files = list(current_dir.glob("*.csproj")) + list(current_dir.glob("*.sln"))
            if dotnet_files:
                if current_dir not in detected_paths:
                    logger.info(f"Detected .NET project at: {current_dir.relative_to(root) if current_dir != root else '.'}")
                    sub_context = ValidationContext(
                        project_root=current_dir,
                        config=context.config,
                        log_file=context.log_file
                    )
                    detected_checkers.append(DotNetChecker(sub_context))
                    detected_paths.add(current_dir)

            # Check for Java markers (pom.xml or build.gradle)
            if (current_dir / "pom.xml").exists() or (current_dir / "build.gradle").exists() or (current_dir / "build.gradle.kts").exists():
                if current_dir not in detected_paths:
                    logger.info(f"Detected Java project at: {current_dir.relative_to(root) if current_dir != root else '.'}")
                    sub_context = ValidationContext(
                        project_root=current_dir,
                        config=context.config,
                        log_file=context.log_file
                    )
                    detected_checkers.append(JavaChecker(sub_context))
                    detected_paths.add(current_dir)

            # Recurse into children
            for child in current_dir.iterdir():
                if child.is_dir() and child.name not in IGNORED_DIRS and not child.name.startswith("."):
                    scan_dir(child, depth + 1)
                    
        except PermissionError:
            # Safely skip unreadable directories
            pass

    # Start the scanning process from the main repository root
    scan_dir(root)
    
    if not detected_checkers:
        logger.warning("No matching project footprints (Python, React, .NET, or Java) were detected.")

    return detected_checkers
