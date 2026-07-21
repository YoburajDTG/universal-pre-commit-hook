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
class AppConfig:
    stages: StagesConfig = field(default_factory=StagesConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    use_docker: bool = False
    parallel_execution: bool = True
    incremental_checks: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        return cls(
            stages=StagesConfig.from_dict(data.get("stages", {})),
            security=SecurityConfig.from_dict(data.get("security", {})),
            use_docker=data.get("use_docker", False),
            parallel_execution=data.get("parallel_execution", True),
            incremental_checks=data.get("incremental_checks", True),
        )

    def merge_overrides(self, override_data: Dict[str, Any]) -> "AppConfig":
        """Returns a new AppConfig merged with the override data."""
        # Simple top-level merge for scalar fields
        new_use_docker = override_data.get("use_docker", self.use_docker)
        new_parallel = override_data.get("parallel_execution", self.parallel_execution)
        new_incremental = override_data.get("incremental_checks", self.incremental_checks)

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
            owasp_dependency_check=sec_data.get("owasp_dependency_check", self.security.owasp_dependency_check),
        )

        return AppConfig(
            stages=new_stages,
            security=new_security,
            use_docker=new_use_docker,
            parallel_execution=new_parallel,
            incremental_checks=new_incremental
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
