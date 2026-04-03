"""Load runtime configuration limits from limits.yaml."""

from pathlib import Path
from typing import Any, cast

import yaml


class LimitsConfig:
    """Configuration manager for runtime limits."""

    _instance: "LimitsConfig" | None = None
    _config: dict[str, Any] | None = None

    def __new__(cls) -> "LimitsConfig":
        """Singleton pattern to ensure only one config is loaded."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load limits from limits.yaml."""
        limits_path = Path("config/runtime/limits.yaml")
        with open(limits_path) as f:
            self._config = yaml.safe_load(f) or {}

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            section: Top-level configuration section (e.g., 'github_api')
            key: Configuration key within the section
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if not self._config:
            return default

        section_config = self._config.get(section, {})
        return section_config.get(key, default)

    def get_section(self, section: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section: Configuration section name
            default: Default dictionary if section not found

        Returns:
            Configuration dictionary for the section
        """
        if not self._config:
            return default or {}

        return cast(dict[str, Any], self._config.get(section, default or {}))

    @property
    def github_api(self) -> dict[str, Any]:
        """Get GitHub API limits."""
        return self.get_section("github_api")

    @property
    def discovery(self) -> dict[str, Any]:
        """Get discovery limits."""
        return self.get_section("discovery")

    @property
    def extraction(self) -> dict[str, Any]:
        """Get extraction limits."""
        return self.get_section("extraction")

    @property
    def upload(self) -> dict[str, Any]:
        """Get upload limits."""
        return self.get_section("upload")

    @property
    def validation(self) -> dict[str, Any]:
        """Get validation limits."""
        return self.get_section("validation")


def load_limits() -> LimitsConfig:
    """
    Load and return the global limits configuration.

    Returns:
        LimitsConfig singleton instance
    """
    return LimitsConfig()
