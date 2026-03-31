# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Structured Config Utils Module.

This module provides utility classes for structured config generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyavd._eos_cli_config_gen.schema import EosCliConfigGen
from pyavd._eos_designs.structured_config.parent_interfaces import ParentInterfacesTracker
from pyavd._utils.run_once import RunOnceMethodStateHelper, run_once_method

if TYPE_CHECKING:
    from pyavd._eos_designs.schema import EosDesigns
    from pyavd._eos_designs.shared_utils import SharedUtilsProtocol


class StructuredConfigUtils(RunOnceMethodStateHelper):
    """
    Utility class for structured config generation.

    This class holds shared utilities and trackers used across all structured config modules.
    """

    def __init__(
        self,
        structured_config: EosCliConfigGen,
        inputs: EosDesigns,
        shared_utils: SharedUtilsProtocol,
    ) -> None:
        """Initialize the StructuredConfigUtils with a ParentInterfacesTracker instance and structured config instance."""
        super().__init__()
        self.structured_config = structured_config
        self.inputs = inputs
        self.shared_utils = shared_utils
        """The shared structured config instance to write config into."""
        self.parent_interfaces_tracker = ParentInterfacesTracker()
        """Tracker for parent interfaces that need to be created for subinterfaces."""

    def _rp_entry_has_acl(self, rp_entry: EosDesigns.UnderlayMulticastRpsItem) -> bool:
        """Return True if an RP entry has both groups and an access_list_name defined."""
        return bool(rp_entry.groups and rp_entry.access_list_name)

    @run_once_method
    def set_once_standard_access_list_for_underlay_multicast_rps(self) -> None:
        """Build and append standard ACL entries for all underlay multicast RPs."""
        for rp_entry in self.inputs.underlay_multicast_rps:
            if not self._rp_entry_has_acl(rp_entry):
                continue
            acl_name = rp_entry.access_list_name
            if acl_name is None:
                continue
            standard_access_list = EosCliConfigGen.StandardAccessListsItem(name=acl_name)
            for index, group in enumerate(rp_entry.groups):
                standard_access_list.entries.append_new(sequence=(index + 1) * 10, action="permit", source=group)
            self.structured_config.standard_access_lists.append(standard_access_list)


__all__ = ["StructuredConfigUtils"]
