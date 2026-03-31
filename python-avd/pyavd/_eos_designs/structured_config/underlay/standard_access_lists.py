# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pyavd._eos_designs.structured_config.structured_config_generator import structured_config_contributor

if TYPE_CHECKING:
    from . import AvdStructuredConfigUnderlayProtocol


class StandardAccessListsMixin(Protocol):
    """
    Mixin Class used to generate structured config for one key.

    Class should only be used as Mixin to a AvdStructuredConfig class.
    """

    @structured_config_contributor
    def standard_access_lists(self: AvdStructuredConfigUnderlayProtocol) -> None:
        """
        Return structured config for standard_access_lists.

        Used for to configure ACLs used by multicast RPs for the underlay
        """
        if not self.shared_utils.underlay_multicast_pim_sm_enabled or not self.inputs.underlay_multicast_rps:
            return
        self.structured_config_utils.set_once_standard_access_list_for_underlay_multicast_rps()
