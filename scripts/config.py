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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        return cls(
            stages=StagesConfig.from_dict(data.get("stages", {})),
            security=SecurityConfig.from_dict(data.get("security", {})),
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
