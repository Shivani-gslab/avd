# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Base class for CLI generators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyavd.api.schemas import EOSConfig


class CliGenerator(ABC):
    """
    Base class for EOS CLI configuration generators.

    Each generator is responsible for rendering a specific section of the EOS configuration
    from structured config data.
    """

    def __init__(self, structured_config: EOSConfig | dict) -> None:
        """
        Initialize the CLI generator.

        Args:
            structured_config: The structured configuration data (dict or EosCliConfigGen model).
        """
        # Convert to dict for easier access
        if isinstance(structured_config, dict):
            self.data = structured_config
        else:
            self.data = structured_config._as_dict()

    @abstractmethod
    def render(self) -> str:
        """
        Render the CLI configuration section.

        Returns:
            CLI configuration text for this section, or empty string if not applicable.
        """
