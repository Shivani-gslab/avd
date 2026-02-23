# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Base class for CLI generators."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Protocol, overload

from pyavd._eos_cli_config_gen.schema import EosCliConfigGen

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar

    from typing_extensions import Self

    T_CliGeneratorSubclass = TypeVar("T_CliGeneratorSubclass", bound="CliGeneratorProtocol")


class CliConfig:
    """
    Accumulator for CLI configuration snippets.

    Similar to self.structured_config in eos_designs, this provides a central place
    to append CLI configuration snippets. Each contributor method can add to this
    instead of managing local config_parts lists.

    Example:
        ```python
        @cli_config_contributor
        def render_vlans(self) -> None:
            if self.data.vlans:
                self.cli_config.append("!")
                for vlan in self.data.vlans:
                    self.cli_config.append(f"vlan {vlan.id}")
                    if vlan.name:
                        self.cli_config.append(f"   name {vlan.name}")
        ```
    """

    def __init__(self) -> None:
        """Initialize the CLI config accumulator."""
        self._lines: list[str] = []

    def append(self, line: str | None) -> None:
        """
        Append a single CLI line or multi-line string.

        Args:
            line: CLI configuration line(s) to append. Can be None (will be ignored).
        """
        if line:
            # Handle multi-line strings
            if "\n" in line:
                self._lines.extend(line.split("\n"))
            else:
                self._lines.append(line)

    def extend(self, lines: list[str] | None) -> None:
        """
        Extend with multiple CLI lines.

        Args:
            lines: List of CLI configuration lines to append. Can be None (will be ignored).
        """
        if lines:
            self._lines.extend(lines)

    def get_config(self) -> str:
        """
        Get the accumulated CLI configuration.

        Returns:
            All accumulated CLI lines joined with newlines.
        """
        return "\n".join(self._lines)

    def clear(self) -> None:
        """Clear all accumulated CLI configuration."""
        self._lines.clear()

    def __str__(self) -> str:
        """Return the accumulated CLI configuration as a string."""
        return self.get_config()

    def __bool__(self) -> bool:
        """Return True if any CLI configuration has been accumulated."""
        return bool(self._lines)


# Overload when assigned with args.
@overload
def cli_config_contributor(
    func: None = None, *, toggle_and_value: tuple[str, bool] | None = None
) -> Callable[[Callable[[T_CliGeneratorSubclass], str | None]], Callable[[T_CliGeneratorSubclass], str | None]]: ...


# Overload when assigned without args.
@overload
def cli_config_contributor(func: Callable[[T_CliGeneratorSubclass], str | None]) -> Callable[[T_CliGeneratorSubclass], str | None]: ...


def cli_config_contributor(
    func: Callable[[T_CliGeneratorSubclass], str | None] | None = None, *, toggle_and_value: tuple[str, bool] | None = None
) -> (
    Callable[[T_CliGeneratorSubclass], str | None] | Callable[[Callable[[T_CliGeneratorSubclass], str | None]], Callable[[T_CliGeneratorSubclass], str | None]]
):
    """
    Decorator to mark methods that contribute to the CLI configuration.

    The decorator can be attached with or without args:
        ```
        # Old pattern: return string
        @cli_config_contributor
        def render_vlans(self) -> str:
            return "vlan 10"


        # New pattern: append to self.cli_config
        @cli_config_contributor
        def render_vlans(self) -> None:
            self.cli_config.append("vlan 10")
        ```
        or with toggle:
        ```
        @cli_config_contributor(toggle_and_value=("vlans", True))
        def render_vlans(self) -> None: ...
        ```

    Args:
        func: The method to decorate.
        toggle_and_value: A tuple of attribute path and expected value, deciding if this method should run.
            The path is a string like `vlans` or nested `vlan_settings.enabled`, pointing to the feature toggle.
    """

    def decorator(fnc: Callable[[T_CliGeneratorSubclass], str | None]) -> Callable[[T_CliGeneratorSubclass], str | None]:
        """Inner actual decorator. Nested to handle assignment both with and without args."""
        fnc._is_cli_config_contributor = True  # pyright: ignore [reportFunctionMemberAccess]
        if toggle_and_value is None:
            return fnc

        toggle, toggle_value = toggle_and_value

        @wraps(fnc)
        def wrapped_func(self: T_CliGeneratorSubclass) -> str | None:
            # Navigate nested attributes using getattr
            value = self.data
            for attr in toggle.split("."):
                value = getattr(value, attr, None)
                if value is None:
                    return None

            if value == toggle_value:
                return fnc(self)

            return None

        return wrapped_func

    if func is not None:
        # This is a @cli_config_contributor assignment without args.
        return decorator(func)

    # This is a @cli_config_contributor(...) assignment with args.
    return decorator


class CliGeneratorProtocol(Protocol):
    """
    Protocol for the CliGenerator base class for CLI generators.

    Each generator is responsible for rendering a specific section of the EOS configuration
    from structured config data.
    """

    data: EosCliConfigGen
    """The structured configuration data as a typed model with attribute access."""

    cli_config: CliConfig
    """Accumulator for CLI configuration snippets."""

    def render(self) -> str:
        """
        Execute all class methods marked with @cli_config_contributor decorator.

        Contributors can either:
        1. Return strings (old pattern) - will be joined together
        2. Append to self.cli_config (new pattern) - will be accumulated

        Returns:
            CLI configuration text for this section, or empty string if not applicable.
        """
        # Clear any previous config
        self.cli_config.clear()
        config_parts = []

        # Execute all contributor methods
        for method in self.cli_config_methods():
            result = method(self)
            # If method returns a string, add it to config_parts (old pattern)
            if result:
                config_parts.append(result)

        # Combine returned strings and accumulated cli_config
        if config_parts and self.cli_config:
            return "\n".join(config_parts) + "\n" + self.cli_config.get_config()
        if config_parts:
            return "\n".join(config_parts)
        return self.cli_config.get_config()

    @classmethod
    def cli_config_methods(cls) -> list[Callable[[Self], str | None]]:
        """Return the list of methods decorated with 'cli_config_contributor'."""
        methods: list[Callable[[Self], str | None]] = []
        for key in cls._keys():
            method = getattr(cls, key)
            if getattr(method, "_is_cli_config_contributor", False):
                methods.append(method)
        return methods

    @classmethod
    def _keys(cls) -> list[str]:
        """Return all attribute keys of the class."""
        return dir(cls)


class CliGenerator(CliGeneratorProtocol):
    """
    Base class for EOS CLI configuration generators.

    Each generator is responsible for rendering a specific section of the EOS configuration
    from structured config data.
    """

    def __init__(self, structured_config: EosCliConfigGen | dict) -> None:
        """
        Initialize the CLI generator.

        Args:
            structured_config: The structured configuration data (dict or EosCliConfigGen model).
        """
        # Keep as typed model for attribute access
        if isinstance(structured_config, dict):
            self.data = EosCliConfigGen(**structured_config)
        else:
            self.data = structured_config

        # Initialize CLI config accumulator
        self.cli_config = CliConfig()

    def render(self) -> str:
        """
        Execute all class methods marked with @cli_config_contributor decorator.

        Contributors can either:
        1. Return strings (old pattern) - will be joined together
        2. Append to self.cli_config (new pattern) - will be accumulated

        Returns:
            CLI configuration text for this section, or empty string if not applicable.
        """
        # Clear any previous config
        self.cli_config.clear()
        config_parts = []

        # Execute all contributor methods
        for method in self.cli_config_methods():
            result = method(self)
            # If method returns a string, add it to config_parts (old pattern)
            if result:
                config_parts.append(result)

        # Combine returned strings and accumulated cli_config
        if config_parts and self.cli_config:
            return "\n".join(config_parts) + "\n" + self.cli_config.get_config()
        if config_parts:
            return "\n".join(config_parts)
        return self.cli_config.get_config()

    @classmethod
    def cli_config_methods(cls) -> list[Callable[[Self], str | None]]:
        """Return the list of methods decorated with 'cli_config_contributor'."""
        methods: list[Callable[[Self], str | None]] = []
        for key in cls._keys():
            method = getattr(cls, key)
            if getattr(method, "_is_cli_config_contributor", False):
                methods.append(method)
        return methods

    @classmethod
    def _keys(cls) -> list[str]:
        """Return all attribute keys of the class."""
        return dir(cls)
