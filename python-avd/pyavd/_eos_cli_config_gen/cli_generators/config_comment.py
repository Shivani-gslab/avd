# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Config comment CLI configuration generator."""

from __future__ import annotations

from pyavd._utils import get_v2

from .base import CliGenerator


class ConfigCommentGenerator(CliGenerator):
    """
    Generator for config comment CLI configuration.

    Renders the config comment section that appears at the beginning of the configuration.
    """

    def render(self) -> str:
        """Render config comment CLI configuration."""
        config_comment = get_v2(self.data, "config_comment")
        if not config_comment:
            return ""

        lines = ["!"]
        lines.extend(f"!{comment_line}" for comment_line in config_comment.split("\n"))

        return "\n".join(lines)
