# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pyavd._eos_cli_config_gen.schema import EosCliConfigGen
from pyavd._eos_designs.structured_config.structured_config_generator import structured_config_contributor
from pyavd._errors import AristaAvdInvalidInputsError

if TYPE_CHECKING:
    from pyavd._eos_designs.schema import EosDesigns

    from . import AvdStructuredConfigUnderlayProtocol


class RouterPimSparseModeMixin(Protocol):
    """
    Mixin Class used to generate structured config for one key.

    Class should only be used as Mixin to a AvdStructuredConfig class.
    """

    def _is_anycast_rp_pim_node(self: AvdStructuredConfigUnderlayProtocol, rp_entry: EosDesigns.UnderlayMulticastRpsItem) -> bool:
        """Return True if this node is part of an anycast RP group configured for PIM mode."""
        return len(rp_entry.nodes) >= 2 and self.shared_utils.hostname in rp_entry.nodes and self.inputs.underlay_multicast_anycast_rp.mode == "pim"

    @structured_config_contributor
    def router_pim_sparse_mode(self: AvdStructuredConfigUnderlayProtocol) -> None:
        """
        Set the structured config for router_pim_sparse_mode.

        Used for to configure multicast RPs for the underlay
        """
        if not self.shared_utils.underlay_multicast_pim_sm_enabled or not self.inputs.underlay_multicast_rps:
            return

        for rp_entry in self.inputs.underlay_multicast_rps:
            rp_address = EosCliConfigGen.RouterPimSparseMode.Ipv4.RpAddressesItem(address=rp_entry.rp)
            if rp_entry.groups:
                if rp_entry.access_list_name:
                    rp_address.access_lists.append(rp_entry.access_list_name)
                    # Ensure the ACL exists in structured_config (safe to call multiple times)
                    self.structured_config_utils.set_once_standard_access_list_for_underlay_multicast_rps()
                else:
                    rp_address.groups.extend(rp_entry.groups)

            self.structured_config.router_pim_sparse_mode.ipv4.rp_addresses.append(rp_address)

            if not self._is_anycast_rp_pim_node(rp_entry):
                continue

            # Anycast-RP using PIM (default)
            other_anycast_rp_addresses = EosCliConfigGen.RouterPimSparseMode.Ipv4.AnycastRpsItem.OtherAnycastRpAddresses()
            for node in rp_entry.nodes:
                peer_facts = self.shared_utils.get_peer_facts(node.name)
                if not peer_facts.router_id:
                    msg = f"'router_id' is required but was not found for {node.name}."
                    raise AristaAvdInvalidInputsError(msg)

                other_anycast_rp_addresses.append_new(address=peer_facts.router_id)
            self.structured_config.router_pim_sparse_mode.ipv4.anycast_rps.append_new(
                address=rp_entry.rp, other_anycast_rp_addresses=other_anycast_rp_addresses
            )
