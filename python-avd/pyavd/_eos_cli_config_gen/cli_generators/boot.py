# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Boot secret CLI configuration generator."""

from __future__ import annotations

from pyavd._utils.get import get_v2
from pyavd.j2filters import hide_passwords

from .base import CliGenerator, cli_config_contributor


class BootGenerator(CliGenerator):
    """
    Generator for boot secret CLI configuration.

    Migrated from j2templates/eos/boot.j2
    """

    @cli_config_contributor
    def boot(self) -> None:
        """
        Render boot secret configuration.

        Generates CLI commands for:
        - Boot secret with hash algorithm (md5 -> 5, default -> sha512)
        - Password hiding support via eos_cli_config_gen_configuration.hide_passwords
        """
        if not get_v2(self.data, "boot.secret.key"):
            return

        # Determine hide_passwords setting
        hide_passwords_enabled = get_v2(self.data, "eos_cli_config_gen_configuration.hide_passwords", default=False)

        # Determine hash algorithm
        hash_algorithm = "sha512"  # Default
        if get_v2(self.data, "boot.secret.hash_algorithm") == "md5":
            hash_algorithm = "5"

        # Hide password if needed
        key = hide_passwords(get_v2(self.data, "boot.secret.key"), hide_passwords_enabled)

        self.cli_config.append("!")
        self.cli_config.append(f"boot secret {hash_algorithm} {key}")
