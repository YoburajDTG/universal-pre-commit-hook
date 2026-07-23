#!/usr/bin/env python3
"""
Configuration module for the Universal Pre-Commit Validation Framework.
Parses config.yaml and loads settings into strongly-typed dataclasses.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger("universal-precommit")


@dataclass(frozen=True)
class StagesConfig:
    formatter: bool = True
    lint: bool = True
    build: bool = True
    tests: bool = True
    security: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StagesConfig":
        return cls(
            formatter=data.get("formatter", True),
            lint=data.get("lint", True),
            build=data.get("build", True),
            tests=data.get("tests", True),
            security=data.get("security", False),
        )


@dataclass(frozen=True)
class SecurityConfig:
    enabled: bool = False
    bandit: bool = True
    pip_audit: bool = True
    npm_audit: bool = True
    owasp_dependency_check: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecurityConfig":
        return cls(
            enabled=data.get("enabled", False),
            bandit=data.get("bandit", True),
            pip_audit=data.get("pip_audit", True),
            npm_audit=data.get("npm_audit", True),
            owasp_dependency_check=data.get("owasp_dependency_check", False),
        )


@dataclass(frozen=True)
class GitConfig:
    auto_push: bool = True
    auto_commit: bool = True
    remote: str = "origin"
    target_branch: str = ""
    commit_prefix: str = "chore: pre-commit validation passed"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitConfig":
        return cls(
            auto_push=data.get("auto_push", True),
            auto_commit=data.get("auto_commit", True),
            remote=data.get("remote", "origin"),
            target_branch=data.get("target_branch", ""),
            commit_prefix=data.get(
                "commit_prefix", "chore: pre-commit validation passed"
            ),
        )


@dataclass(frozen=True)
class AppConfig:
    stages: StagesConfig = field(default_factory=StagesConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    git: GitConfig = field(default_factory=GitConfig)
    use_docker: bool = False
    parallel_execution: bool = True
    incremental_checks: bool = True
    auto_fix: bool = True
    allow_lint_warnings: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        return cls(
            stages=StagesConfig.from_dict(data.get("stages", {})),
            security=SecurityConfig.from_dict(data.get("security", {})),
            git=GitConfig.from_dict(data.get("git", {})),
            use_docker=data.get("use_docker", False),
            parallel_execution=data.get("parallel_execution", True),
            incremental_checks=data.get("incremental_checks", True),
            auto_fix=data.get("auto_fix", True),
            allow_lint_warnings=data.get("allow_lint_warnings", True),
        )

    def merge_overrides(self, override_data: Dict[str, Any]) -> "AppConfig":
        """Returns a new AppConfig merged with the override data."""
        # Simple top-level merge for scalar fields
        new_use_docker = override_data.get("use_docker", self.use_docker)
        new_parallel = override_data.get("parallel_execution", self.parallel_execution)
        new_incremental = override_data.get(
            "incremental_checks", self.incremental_checks
        )
        new_auto_fix = override_data.get("auto_fix", self.auto_fix)
        new_allow_lint_warnings = override_data.get(
            "allow_lint_warnings", self.allow_lint_warnings
        )

        # Merge nested stages config
        stages_data = override_data.get("stages", {})
        new_stages = StagesConfig(
            formatter=stages_data.get("formatter", self.stages.formatter),
            lint=stages_data.get("lint", self.stages.lint),
            build=stages_data.get("build", self.stages.build),
            tests=stages_data.get("tests", self.stages.tests),
            security=stages_data.get("security", self.stages.security),
        )

        # Merge nested security config
        sec_data = override_data.get("security", {})
        new_security = SecurityConfig(
            enabled=sec_data.get("enabled", self.security.enabled),
            bandit=sec_data.get("bandit", self.security.bandit),
            pip_audit=sec_data.get("pip_audit", self.security.pip_audit),
            npm_audit=sec_data.get("npm_audit", self.security.npm_audit),
            owasp_dependency_check=sec_data.get(
                "owasp_dependency_check", self.security.owasp_dependency_check
            ),
        )

        # Merge nested git config
        git_data = override_data.get("git", {})
        new_git = GitConfig(
            auto_push=git_data.get("auto_push", self.git.auto_push),
            auto_commit=git_data.get("auto_commit", self.git.auto_commit),
            remote=git_data.get("remote", self.git.remote),
            target_branch=git_data.get("target_branch", self.git.target_branch),
            commit_prefix=git_data.get("commit_prefix", self.git.commit_prefix),
        )

        return AppConfig(
            stages=new_stages,
            security=new_security,
            git=new_git,
            use_docker=new_use_docker,
            parallel_execution=new_parallel,
            incremental_checks=new_incremental,
            auto_fix=new_auto_fix,
            allow_lint_warnings=new_allow_lint_warnings,
        )


def load_config(config_path: Path) -> AppConfig:
    """
    Loads and parses the configuration YAML file.
    If the file is missing or invalid, it returns default configurations with warnings.
    """
    if not config_path.exists():
        logger.warning(
            f"Config file not found at {config_path}. Using default configuration."
        )
        return AppConfig()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if not isinstance(data, dict):
            logger.error(
                f"Invalid yaml format in {config_path}. Expected dictionary structure."
            )
            return AppConfig()

        return AppConfig.from_dict(data)
    except Exception as e:
        logger.error(
            f"Error reading configuration file {config_path}: {e}. Falling back to default settings."
        )
        return AppConfig()
