# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Router BGP CLI configuration generator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyavd._utils.get import get_v2
from pyavd.j2filters import hide_passwords, natural_sort

from .base import CliGenerator, cli_config_contributor

if TYPE_CHECKING:
    from pyavd._eos_cli_config_gen.schema import EosCliConfigGen


class RouterBgpGenerator(CliGenerator):
    """
    Generator for router BGP CLI configuration.

    Migrated from j2templates/eos/router-bgp.j2 (lines 1-500).

    Single contributor method `router_bgp` orchestrates section helpers in EOS
    output order. Each helper maps to one recognisable block in the CLI output.
    """

    # ------------------------------------------------------------------
    # Public contributor - single entry point
    # ------------------------------------------------------------------

    @cli_config_contributor
    def router_bgp(self) -> None:
        """Render the full 'router bgp' block in EOS output order."""
        bgp = self.data.router_bgp
        # `as` is a Python reserved word.
        if (bgp_as := get_v2(bgp, "as")) is None:
            return

        cfg = self.cli_config.router_bgp
        cfg.append(self._SEP)
        cfg.append(f"router bgp {bgp_as}")

        self._render_global_settings(bgp)
        self._render_peer_groups(bgp)
        self._render_neighbors(bgp)
        self._render_redistribute_internal(bgp)
        self._render_aggregate_addresses(bgp)

    # ------------------------------------------------------------------
    # Top-level section helpers
    # ------------------------------------------------------------------

    def _render_global_settings(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """
        Render global BGP settings in EOS output order (J2 lines 10-134).

        Simple flags are inlined; multi-line concepts delegate to sub-helpers.
        """
        cfg = self.cli_config.router_bgp

        if bgp.as_notation is not None:
            cfg.append_l1(f"bgp asn notation {bgp.as_notation}")
        if bgp.router_id is not None:
            cfg.append_l1(f"router-id {bgp.router_id}")
        if bgp.updates.wait_for_convergence is True:
            cfg.append_l1("update wait-for-convergence")
        if bgp.updates.wait_install is True:
            cfg.append_l1("update wait-install")

        self._render_bgp_default_flags(bgp)
        self._render_timers(bgp)
        self._render_distance(bgp)
        self._render_graceful_restart(bgp)

        if bgp.bgp_cluster_id is not None:
            cfg.append_l1(f"bgp cluster-id {bgp.bgp_cluster_id}")

        self._render_graceful_restart_helper(bgp)
        self._render_route_reflector_preserve(bgp)
        self._render_maximum_paths_global(bgp)

        for bgp_default in bgp.bgp_defaults or []:
            cfg.append_l1(bgp_default)

        self._render_additional_paths(bgp)
        self._render_listen_ranges(bgp)

        if bgp.bgp.bestpath.d_path is True:
            cfg.append_l1("bgp bestpath d-path")

        if bgp.neighbor_default.send_community == "all":
            cfg.append_l1("neighbor default send-community")
        elif bgp.neighbor_default.send_community is not None:
            cfg.append_l1(f"neighbor default send-community {bgp.neighbor_default.send_community}")

    def _render_peer_groups(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render all peer-group entries sorted by name (J2 lines 135-307)."""
        for peer_group in natural_sort(bgp.peer_groups or [], sort_key="name"):
            self._render_peer_group(peer_group)

    def _render_peer_group(self, peer_group: EosCliConfigGen.RouterBgp.PeerGroupsItem) -> None:
        """Render a single peer-group block in EOS output order."""
        cfg = self.cli_config.router_bgp
        name = peer_group.name

        cfg.append_l1(f"neighbor {name} peer group")

        if peer_group.remote_as is not None:
            cfg.append_l1(f"neighbor {name} remote-as {peer_group.remote_as}")
        if peer_group.shutdown is True:
            cfg.append_l1(f"neighbor {name} shutdown")

        self._render_next_hop(name, peer_group.next_hop_self, peer_group.next_hop_peer, peer_group.next_hop_unchanged)
        self._render_remove_private_as(name, peer_group.remove_private_as)
        self._render_as_path(name, peer_group.as_path)

        if peer_group.local_as is not None:
            cfg.append_l1(f"neighbor {name} local-as {peer_group.local_as} no-prepend replace-as")
        if peer_group.weight is not None:
            cfg.append_l1(f"neighbor {name} weight {peer_group.weight}")
        if peer_group.passive is True:
            cfg.append_l1(f"neighbor {name} passive")
        if peer_group.update_source is not None:
            cfg.append_l1(f"neighbor {name} update-source {peer_group.update_source}")

        self._render_bfd(name, peer_group.bfd, peer_group.bfd_timers)

        if peer_group.description is not None:
            cfg.append_l1(f"neighbor {name} description {peer_group.description}")

        self._render_allowas_in(name, peer_group.allowas_in)
        self._render_rib_in_pre_policy_retain(name, peer_group.rib_in_pre_policy_retain)

        if peer_group.ebgp_multihop is not None:
            cfg.append_l1(f"neighbor {name} ebgp-multihop {peer_group.ebgp_multihop}")
        if peer_group.ttl_maximum_hops is not None:
            cfg.append_l1(f"neighbor {name} ttl maximum-hops {peer_group.ttl_maximum_hops}")
        if peer_group.route_reflector_client is True:
            cfg.append_l1(f"neighbor {name} route-reflector-client")
        if peer_group.session_tracker is not None:
            cfg.append_l1(f"neighbor {name} session tracker {peer_group.session_tracker}")
        if peer_group.timers is not None:
            cfg.append_l1(f"neighbor {name} timers {peer_group.timers}")

        self._render_route_maps(name, peer_group.route_map_in, peer_group.route_map_out)

        # password key before shared-secret for peer-groups (J2 ordering)
        self._render_password_key(name, peer_group.password, peer_group.password_type)
        self._render_shared_secret(name, peer_group.shared_secret)

        self._render_default_originate(name, peer_group.default_originate)
        self._render_send_community(name, peer_group.send_community)
        self._render_maximum_routes(name, peer_group.maximum_routes, peer_group.maximum_routes_warning_limit, peer_group.maximum_routes_warning_only)

        if peer_group.missing_policy is not None:
            self._render_missing_policy(name, peer_group.missing_policy)

        self._render_peer_tags(name, peer_group.peer_tag_in, peer_group.peer_tag_out_discard)
        self._render_link_bandwidth(name, peer_group.link_bandwidth)
        self._render_remove_private_as_ingress(name, peer_group.remove_private_as_ingress)

    def _render_neighbors(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render all neighbor entries sorted by IP address (J2 lines 308-483)."""
        for neighbor in natural_sort(bgp.neighbors or [], sort_key="ip_address"):
            self._render_neighbor(neighbor)

    def _render_neighbor(self, neighbor: EosCliConfigGen.RouterBgp.NeighborsItem) -> None:
        """
        Render a single neighbor block in EOS output order.

        Differences from peer-group:
        - 'no neighbor X bfd' is valid (inherited bfd can be disabled per neighbor)
        - 'no neighbor X route-reflector-client' is valid
        - shared-secret is rendered before password key (J2 ordering)
        """
        cfg = self.cli_config.router_bgp
        ip = neighbor.ip_address

        if neighbor.peer_group is not None:
            cfg.append_l1(f"neighbor {ip} peer group {neighbor.peer_group}")
        if neighbor.remote_as is not None:
            cfg.append_l1(f"neighbor {ip} remote-as {neighbor.remote_as}")
        if neighbor.shutdown is True:
            cfg.append_l1(f"neighbor {ip} shutdown")

        self._render_next_hop(ip, neighbor.next_hop_self, neighbor.next_hop_peer)
        self._render_remove_private_as(ip, neighbor.remove_private_as)
        self._render_as_path(ip, neighbor.as_path)

        if neighbor.local_as is not None:
            cfg.append_l1(f"neighbor {ip} local-as {neighbor.local_as} no-prepend replace-as")
        if neighbor.weight is not None:
            cfg.append_l1(f"neighbor {ip} weight {neighbor.weight}")
        if neighbor.passive is True:
            cfg.append_l1(f"neighbor {ip} passive")
        if neighbor.update_source is not None:
            cfg.append_l1(f"neighbor {ip} update-source {neighbor.update_source}")

        # Neighbors can disable bfd inherited from a peer-group; peer-groups cannot.
        self._render_bfd(ip, neighbor.bfd, neighbor.bfd_timers, allow_negation=neighbor.peer_group is not None)

        if neighbor.description is not None:
            cfg.append_l1(f"neighbor {ip} description {neighbor.description}")

        self._render_allowas_in(ip, neighbor.allowas_in)
        self._render_rib_in_pre_policy_retain(ip, neighbor.rib_in_pre_policy_retain)

        if neighbor.ebgp_multihop is not None:
            cfg.append_l1(f"neighbor {ip} ebgp-multihop {neighbor.ebgp_multihop}")
        if neighbor.ttl_maximum_hops is not None:
            cfg.append_l1(f"neighbor {ip} ttl maximum-hops {neighbor.ttl_maximum_hops}")

        # Neighbors support negation for route-reflector-client; peer-groups do not.
        if neighbor.route_reflector_client is True:
            cfg.append_l1(f"neighbor {ip} route-reflector-client")
        elif neighbor.route_reflector_client is False:
            cfg.append_l1(f"no neighbor {ip} route-reflector-client")

        if neighbor.session_tracker is not None:
            cfg.append_l1(f"neighbor {ip} session tracker {neighbor.session_tracker}")
        if neighbor.timers is not None:
            cfg.append_l1(f"neighbor {ip} timers {neighbor.timers}")

        self._render_route_maps(ip, neighbor.route_map_in, neighbor.route_map_out)

        # shared-secret before password key for neighbors (J2 ordering)
        self._render_shared_secret(ip, neighbor.shared_secret)
        self._render_password_key(ip, neighbor.password, neighbor.password_type)

        self._render_default_originate(ip, neighbor.default_originate)
        self._render_send_community(ip, neighbor.send_community)
        self._render_maximum_routes(ip, neighbor.maximum_routes, neighbor.maximum_routes_warning_limit, neighbor.maximum_routes_warning_only)

        if neighbor.missing_policy is not None:
            self._render_missing_policy(ip, neighbor.missing_policy)

        self._render_peer_tags(ip, neighbor.peer_tag_in, neighbor.peer_tag_out_discard)
        self._render_link_bandwidth(ip, neighbor.link_bandwidth)
        self._render_remove_private_as_ingress(ip, neighbor.remove_private_as_ingress)

    def _render_redistribute_internal(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp redistribute-internal' or its negation (J2 lines 484-488)."""
        cfg = self.cli_config.router_bgp
        if bgp.bgp.redistribute_internal is True:
            cfg.append_l1("bgp redistribute-internal")
        elif bgp.bgp.redistribute_internal is False:
            cfg.append_l1("no bgp redistribute-internal")

    def _render_aggregate_addresses(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render aggregate-address entries sorted by prefix (J2 lines 489-510)."""
        cfg = self.cli_config.router_bgp
        for agg in natural_sort(bgp.aggregate_addresses or [], sort_key="prefix"):
            agg_cli = f"aggregate-address {agg.prefix}"
            if agg.as_set is True:
                agg_cli += " as-set"
            if agg.summary_only is True:
                agg_cli += " summary-only"
            if agg.attribute_map is not None:
                agg_cli += f" attribute-map {agg.attribute_map}"
            if agg.attribute.rcf is not None:
                agg_cli += f" attribute rcf {agg.attribute.rcf}"
            if agg.match_map is not None:
                agg_cli += f" match-map {agg.match_map}"
            if agg.advertise_only is True:
                agg_cli += " advertise-only"
            cfg.append_l1(agg_cli)

    # ------------------------------------------------------------------
    # Global-settings sub-helpers
    # ------------------------------------------------------------------

    def _render_bgp_default_flags(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp default ipv4-unicast' and 'bgp default ipv4-unicast transport ipv6' flags."""
        cfg = self.cli_config.router_bgp
        if bgp.bgp.default.ipv4_unicast is True:
            cfg.append_l1("bgp default ipv4-unicast")
        elif bgp.bgp.default.ipv4_unicast is False:
            cfg.append_l1("no bgp default ipv4-unicast")

        if bgp.bgp.default.ipv4_unicast_transport_ipv6 is True:
            cfg.append_l1("bgp default ipv4-unicast transport ipv6")
        elif bgp.bgp.default.ipv4_unicast_transport_ipv6 is False:
            cfg.append_l1("no bgp default ipv4-unicast transport ipv6")

    def _render_timers(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'timers bgp keepalive hold [min-hold-time X] [send-failure hold-time Y]'."""
        t = bgp.timers
        if t.keepalive_time is None and t.hold_time is None and t.min_hold_time is None and t.send_failure_hold_time is None:
            return
        timers_cli = "timers bgp"
        if bgp.timers.keepalive_time is not None and bgp.timers.hold_time is not None:
            timers_cli += f" {bgp.timers.keepalive_time} {bgp.timers.hold_time}"
        if bgp.timers.min_hold_time is not None:
            timers_cli += f" min-hold-time {bgp.timers.min_hold_time}"
        if bgp.timers.send_failure_hold_time is not None:
            timers_cli += f" send-failure hold-time {bgp.timers.send_failure_hold_time}"
        self.cli_config.router_bgp.append_l1(timers_cli)

    def _render_distance(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'distance bgp external [internal local]'."""
        if bgp.distance.external_routes is None:
            return
        distance_cli = f"distance bgp {bgp.distance.external_routes}"
        if bgp.distance.internal_routes is not None and bgp.distance.local_routes is not None:
            distance_cli += f" {bgp.distance.internal_routes} {bgp.distance.local_routes}"
        self.cli_config.router_bgp.append_l1(distance_cli)

    def _render_graceful_restart(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """
        Render graceful-restart timers then the enable command.

        Timers must be configured before the 'graceful-restart' enable command.
        """
        if bgp.graceful_restart.enabled is not True:
            return
        cfg = self.cli_config.router_bgp
        if bgp.graceful_restart.restart_time is not None:
            cfg.append_l1(f"graceful-restart restart-time {bgp.graceful_restart.restart_time}")
        if bgp.graceful_restart.stalepath_time is not None:
            cfg.append_l1(f"graceful-restart stalepath-time {bgp.graceful_restart.stalepath_time}")
        cfg.append_l1("graceful-restart")

    def _render_graceful_restart_helper(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'graceful-restart-helper' settings or its negation."""
        cfg = self.cli_config.router_bgp
        if bgp.graceful_restart_helper.enabled is False:
            cfg.append_l1("no graceful-restart-helper")
        elif bgp.graceful_restart_helper.enabled is True:
            if bgp.graceful_restart_helper.restart_time is not None:
                cfg.append_l1(f"graceful-restart-helper restart-time {bgp.graceful_restart_helper.restart_time}")
            elif bgp.graceful_restart_helper.long_lived is True:
                cfg.append_l1("graceful-restart-helper long-lived")

    def _render_route_reflector_preserve(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp route-reflector preserve-attributes [always]'."""
        if bgp.bgp.route_reflector_preserve_attributes.enabled is not True:
            return
        rr_cli = "bgp route-reflector preserve-attributes"
        if bgp.bgp.route_reflector_preserve_attributes.always is True:
            rr_cli += " always"
        self.cli_config.router_bgp.append_l1(rr_cli)

    def _render_maximum_paths_global(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'maximum-paths X [ecmp Y]'."""
        if bgp.maximum_paths.paths is None:
            return
        paths_cli = f"maximum-paths {bgp.maximum_paths.paths}"
        if bgp.maximum_paths.ecmp is not None:
            paths_cli += f" ecmp {bgp.maximum_paths.ecmp}"
        self.cli_config.router_bgp.append_l1(paths_cli)

    def _render_additional_paths(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp additional-paths receive' and 'bgp additional-paths send ...'."""
        cfg = self.cli_config.router_bgp

        if bgp.bgp.additional_paths.receive is True:
            cfg.append_l1("bgp additional-paths receive")
        elif bgp.bgp.additional_paths.receive is False:
            cfg.append_l1("no bgp additional-paths receive")

        send = bgp.bgp.additional_paths.send
        send_limit = bgp.bgp.additional_paths.send_limit
        if send is None:
            return
        if send == "disabled":
            cfg.append_l1("no bgp additional-paths send")
        elif send == "ecmp" and send_limit is not None:
            cfg.append_l1(f"bgp additional-paths send ecmp limit {send_limit}")
        elif send == "limit" and send_limit is not None:
            cfg.append_l1(f"bgp additional-paths send limit {send_limit}")
        else:
            cfg.append_l1(f"bgp additional-paths send {send}")

    def _render_listen_ranges(self, bgp: EosCliConfigGen.RouterBgp) -> None:
        """Render 'bgp listen range' entries sorted by peer-group."""
        cfg = self.cli_config.router_bgp
        for listen_range in natural_sort(bgp.listen_ranges or [], sort_key="peer_group"):
            if listen_range.peer_group is None or listen_range.prefix is None:
                continue
            if listen_range.peer_filter is None and listen_range.remote_as is None:
                continue
            lr_cli = f"bgp listen range {listen_range.prefix}"
            if listen_range.peer_id_include_router_id is True:
                lr_cli += " peer-id include router-id"
            lr_cli += f" peer-group {listen_range.peer_group}"
            if listen_range.peer_filter is not None:
                lr_cli += f" peer-filter {listen_range.peer_filter}"
            elif listen_range.remote_as is not None:
                lr_cli += f" remote-as {listen_range.remote_as}"
            cfg.append_l1(lr_cli)

    # ------------------------------------------------------------------
    # Shared peer-group / neighbor attribute helpers
    # ------------------------------------------------------------------

    def _render_next_hop(
        self,
        entity_id: str,
        next_hop_self: bool | None,
        next_hop_peer: bool | None,
        next_hop_unchanged: bool | None = None,
    ) -> None:
        """Render next-hop-self, next-hop-peer, and (peer-groups only) next-hop-unchanged."""
        cfg = self.cli_config.router_bgp
        if next_hop_self is True:
            cfg.append_l1(f"neighbor {entity_id} next-hop-self")
        if next_hop_peer is True:
            cfg.append_l1(f"neighbor {entity_id} next-hop-peer")
        if next_hop_unchanged is True:
            cfg.append_l1(f"neighbor {entity_id} next-hop-unchanged")

    def _render_as_path(self, entity_id: str, as_path: Any) -> None:
        """Render 'as-path prepend-own disabled' and 'as-path remote-as replace out'."""
        cfg = self.cli_config.router_bgp
        if as_path.prepend_own_disabled is True:
            cfg.append_l1(f"neighbor {entity_id} as-path prepend-own disabled")
        if as_path.remote_as_replace_out is True:
            cfg.append_l1(f"neighbor {entity_id} as-path remote-as replace out")

    def _render_bfd(self, entity_id: str, bfd: bool | None, bfd_timers: Any, *, allow_negation: bool = False) -> None:
        """
        Render BFD configuration for a neighbor or peer-group.

        When allow_negation=True (neighbors only), 'no neighbor X bfd' is rendered
        when bfd is explicitly False, to override a peer-group's bfd=True.
        """
        cfg = self.cli_config.router_bgp
        if bfd is True:
            cfg.append_l1(f"neighbor {entity_id} bfd")
            if bfd_timers.interval is not None and bfd_timers.min_rx is not None and bfd_timers.multiplier is not None:
                cfg.append_l1(f"neighbor {entity_id} bfd interval {bfd_timers.interval} min-rx {bfd_timers.min_rx} multiplier {bfd_timers.multiplier}")
        elif bfd is False and allow_negation:
            cfg.append_l1(f"no neighbor {entity_id} bfd")

    def _render_route_maps(self, entity_id: str, route_map_in: str | None, route_map_out: str | None) -> None:
        """Render inbound and outbound route-map assignments."""
        cfg = self.cli_config.router_bgp
        if route_map_in is not None:
            cfg.append_l1(f"neighbor {entity_id} route-map {route_map_in} in")
        if route_map_out is not None:
            cfg.append_l1(f"neighbor {entity_id} route-map {route_map_out} out")

    def _render_password_key(self, entity_id: str, password: str | None, password_type: str | None) -> None:
        """Render 'neighbor X password [type] key' (type defaults to 7)."""
        if password is None:
            return
        pw_type = password_type if password_type is not None else "7"
        pw = hide_passwords(password, self.data.eos_cli_config_gen_configuration.hide_passwords)
        self.cli_config.router_bgp.append_l1(f"neighbor {entity_id} password {pw_type} {pw}")

    def _render_shared_secret(self, entity_id: str, shared_secret: Any) -> None:
        """Render 'neighbor X password shared-secret profile P algorithm A'."""
        if shared_secret.profile is None or shared_secret.hash_algorithm is None:
            return
        self.cli_config.router_bgp.append_l1(
            f"neighbor {entity_id} password shared-secret profile {shared_secret.profile} algorithm {shared_secret.hash_algorithm}"
        )

    def _render_peer_tags(self, entity_id: str, peer_tag_in: str | None, peer_tag_out_discard: str | None) -> None:
        """Render 'peer-tag in' and 'peer-tag out discard'."""
        cfg = self.cli_config.router_bgp
        if peer_tag_in is not None:
            cfg.append_l1(f"neighbor {entity_id} peer-tag in {peer_tag_in}")
        if peer_tag_out_discard is not None:
            cfg.append_l1(f"neighbor {entity_id} peer-tag out discard {peer_tag_out_discard}")

    def _render_remove_private_as(self, entity_id: str, remove_private_as: Any) -> None:
        """Render 'remove-private-as [all [replace-as]]' or its negation."""
        cfg = self.cli_config.router_bgp
        if remove_private_as.enabled is True:
            rpa_cli = f"neighbor {entity_id} remove-private-as"
            if remove_private_as.all is True:
                rpa_cli += " all"
                if remove_private_as.replace_as is True:
                    rpa_cli += " replace-as"
            cfg.append_l1(rpa_cli)
        elif remove_private_as.enabled is False:
            cfg.append_l1(f"no neighbor {entity_id} remove-private-as")

    def _render_remove_private_as_ingress(self, entity_id: str, remove_private_as_ingress: Any) -> None:
        """Render 'remove-private-as ingress [replace-as]' or its negation."""
        cfg = self.cli_config.router_bgp
        if remove_private_as_ingress.enabled is True:
            rpai_cli = f"neighbor {entity_id} remove-private-as ingress"
            if remove_private_as_ingress.replace_as is True:
                rpai_cli += " replace-as"
            cfg.append_l1(rpai_cli)
        elif remove_private_as_ingress.enabled is False:
            cfg.append_l1(f"no neighbor {entity_id} remove-private-as ingress")

    def _render_allowas_in(self, entity_id: str, allowas_in: Any) -> None:
        """Render 'allowas-in [N]'."""
        if allowas_in.enabled is not True:
            return
        allowas_cli = f"neighbor {entity_id} allowas-in"
        if allowas_in.times is not None:
            allowas_cli += f" {allowas_in.times}"
        self.cli_config.router_bgp.append_l1(allowas_cli)

    def _render_rib_in_pre_policy_retain(self, entity_id: str, rib_in: Any) -> None:
        """Render 'rib-in pre-policy retain [all]' or its negation."""
        cfg = self.cli_config.router_bgp
        if rib_in.enabled is True:
            rib_cli = f"neighbor {entity_id} rib-in pre-policy retain"
            if rib_in.all is True:
                rib_cli += " all"
            cfg.append_l1(rib_cli)
        elif rib_in.enabled is False:
            cfg.append_l1(f"no neighbor {entity_id} rib-in pre-policy retain")

    def _render_default_originate(self, entity_id: str, default_originate: Any) -> None:
        """Render 'default-originate [route-map X] [always]'."""
        if default_originate.enabled is not True:
            return
        do_cli = f"neighbor {entity_id} default-originate"
        if default_originate.route_map is not None:
            do_cli += f" route-map {default_originate.route_map}"
        if default_originate.always is True:
            do_cli += " always"
        self.cli_config.router_bgp.append_l1(do_cli)

    def _render_send_community(self, entity_id: str, send_community: str | None) -> None:
        """Render 'send-community [extended|large|...]' ('all' omits the keyword)."""
        cfg = self.cli_config.router_bgp
        if send_community == "all":
            cfg.append_l1(f"neighbor {entity_id} send-community")
        elif send_community is not None:
            cfg.append_l1(f"neighbor {entity_id} send-community {send_community}")

    def _render_maximum_routes(
        self,
        entity_id: str,
        maximum_routes: int | None,
        warning_limit: int | str | None,
        warning_only: bool | None,
    ) -> None:
        """Render 'maximum-routes N [warning-limit M] [warning-only]'."""
        if maximum_routes is None:
            return
        mr_cli = f"neighbor {entity_id} maximum-routes {maximum_routes}"
        if warning_limit is not None:
            mr_cli += f" warning-limit {warning_limit}"
        if warning_only is True:
            mr_cli += " warning-only"
        self.cli_config.router_bgp.append_l1(mr_cli)

    def _render_missing_policy(self, entity_id: str, missing_policy: Any) -> None:
        """Render 'missing-policy address-family all [include ...] direction {in|out} action X'."""
        cfg = self.cli_config.router_bgp
        for direction in ("in", "out"):
            policy = getattr(missing_policy, f"direction_{direction}", None)
            if policy is None or policy.action is None:
                continue
            mp_cli = f"neighbor {entity_id} missing-policy address-family all"
            includes: list[str] = []
            if policy.include_community_list is True:
                includes.append("community-list")
            if policy.include_prefix_list is True:
                includes.append("prefix-list")
            if policy.include_sub_route_map is True:
                includes.append("sub-route-map")
            if includes:
                mp_cli += " include " + " ".join(includes)
            mp_cli += f" direction {direction} action {policy.action}"
            cfg.append_l1(mp_cli)

    def _render_link_bandwidth(self, entity_id: str, link_bandwidth: Any) -> None:
        """Render 'link-bandwidth [default X]'."""
        if link_bandwidth.enabled is not True:
            return
        lb_cli = f"neighbor {entity_id} link-bandwidth"
        if link_bandwidth.default is not None:
            lb_cli += f" default {link_bandwidth.default}"
        self.cli_config.router_bgp.append_l1(lb_cli)
