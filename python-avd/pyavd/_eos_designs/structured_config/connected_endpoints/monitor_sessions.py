# Copyright (c) 2023-2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
from __future__ import annotations

import re
from functools import cached_property
from typing import TYPE_CHECKING, Protocol

from pyavd._eos_cli_config_gen.schema import EosCliConfigGen
from pyavd._errors import AristaAvdInvalidInputsError
from pyavd._eos_designs.structured_config.structured_config_generator import structured_config_contributor

from pyavd._utils import append_if_not_duplicate, groupby_obj, strip_null_from_data
from pyavd.j2filters import range_expand

if TYPE_CHECKING:
    from pyavd._eos_designs.schema import EosDesigns

    from . import AvdStructuredConfigConnectedEndpointsProtocol


class MonitorSessionsMixin(Protocol):
    """
    Mixin Class used to generate structured config for one key.

    Class should only be used as Mixin to a AvdStructuredConfig class.
    """

    @structured_config_contributor
    def monitor_sessions(self: AvdStructuredConfigConnectedEndpointsProtocol) -> None:
        """Set the structured_config for monitor_sessions."""
        # monitor_session_configs = EosCliConfigGen.MonitorSessions()
        monitor_session_configs = []
        for connected_endpoint in self._filtered_connected_endpoints:
            for adapter in connected_endpoint.adapters:
                if not adapter.monitor_sessions:
                    continue

                # Monitor session on Port-channel interface
                if adapter.port_channel.mode:
                    default_channel_group_id = int("".join(re.findall(r"\d", adapter.switch_ports[0])))
                    channel_group_id = adapter.port_channel.channel_id or default_channel_group_id

                    port_channel_interface_name = f"Port-Channel{channel_group_id}"
                    for monitor_session in adapter.monitor_sessions:
                        per_interface_monitor_session = monitor_session._deepcopy()
                        # per_interface_monitor_session = per_interface_monitor_session._cast_as(EosCliConfigGen.MonitorSessionsItem)
                        per_interface_monitor_session._interface = port_channel_interface_name
                        per_interface_monitor_session._context = adapter._context
                        monitor_session_configs.append(per_interface_monitor_session)
                    continue

                # Monitor session on Ethernet interface
                for node_index, node_name in enumerate(adapter.switches):
                    if node_name != self.shared_utils.hostname:
                        continue

                    ethernet_interface_name = adapter.switch_ports[node_index]
                    for monitor_session in adapter.monitor_sessions:
                        per_interface_monitor_session = monitor_session._deepcopy()
                        # per_interface_monitor_session = per_interface_monitor_session._cast_as(EosCliConfigGen.MonitorSessionsItem)
                        per_interface_monitor_session._interface = ethernet_interface_name
                        per_interface_monitor_session._context = adapter._context
                        monitor_session_configs.append(per_interface_monitor_session)

        for network_port in self._filtered_network_ports:
            if not network_port.monitor_sessions:
                continue

            for ethernet_interface_name in range_expand(network_port.switch_ports):
                # Monitor session on Port-channel interface
                if network_port.port_channel and network_port.port_channel.mode is not None:
                    default_channel_group_id = int("".join(re.findall(r"\d", ethernet_interface_name)))
                    channel_group_id = network_port.port_channel.channel_id or default_channel_group_id

                    port_channel_interface_name = f"Port-Channel{channel_group_id}"
                    for monitor_session in network_port.monitor_sessions:
                        per_interface_monitor_session = monitor_session._deepcopy()
                        # per_interface_monitor_session = per_interface_monitor_session._cast_as(EosCliConfigGen.MonitorSessionsItem)
                        per_interface_monitor_session._interface = port_channel_interface_name
                        per_interface_monitor_session._context = network_port._context
                        monitor_session_configs.append(per_interface_monitor_session)
                    continue

                # Monitor session on Ethernet interface
                for monitor_session in network_port.monitor_sessions:
                    per_interface_monitor_session = monitor_session._deepcopy()
                    # per_interface_monitor_session = per_interface_monitor_session._cast_as(EosCliConfigGen.MonitorSessionsItem)
                    per_interface_monitor_session._interface = ethernet_interface_name
                    per_interface_monitor_session._context = network_port._context
                    monitor_session_configs.append(per_interface_monitor_session)

        for session_name, session_configs in groupby_obj(monitor_session_configs, "name"):
            # Convert iterator to list since we can only access it once.
            session_configs_list = list(session_configs)
            merged_settings = session_configs_list[0]._deepcopy()
            for session_config in session_configs_list[1:]:
                merged_settings._deepmerge(session_config)

            if merged_settings.session_settings.access_group:
                for session in session_configs_list:
                    if session.source_settings.access_group:
                        msg = (
                            f"Cannot set an ACL for both `session_settings` and `source_settings`"
                            f" under the monitor session '{session.name}' for {session._context}."
                        )
                        raise AristaAvdInvalidInputsError(msg)

            monitor_session = EosCliConfigGen.MonitorSessionsItem(name=session_name)
            for session in session_configs_list:
                if session.role == "destination":
                     monitor_session.destinations.append(session._interface)

            source_sessions = [session for session in session_configs_list if session.role == "source"]

            for session in source_sessions:
                source = EosCliConfigGen.MonitorSessionsItem.SourcesItem(
                    name=session._interface,
                    direction=session.source_settings.direction,
                )
                if session.source_settings.access_group.name is not None:
                    source.access_group._update(
                        type=session.source_settings.access_group.type,
                        name=session.source_settings.access_group.name,
                        priority=session.source_settings.access_group.priority,
                    )
                monitor_session.sources.append(source)

            if session_settings := merged_settings.session_settings:
                monitor_session._update(encapsulation_gre_metadata_tx=session_settings.encapsulation_gre_metadata_tx,
                                        header_remove_size=session_settings.header_remove_size,
                                        access_group=session_settings.access_group,
                                        rate_limit_per_ingress_chip=session_settings.rate_limit_per_ingress_chip,
                                        rate_limit_per_egress_chip=session_settings.rate_limit_per_egress_chip,
                                        sample=session_settings.sample,
                                        truncate=session_settings.truncate
                                        )

            self.structured_config.monitor_sessions.append(monitor_session)
