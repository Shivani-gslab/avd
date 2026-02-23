# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Base classes for CLI configuration generators."""

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
    Accumulator for building CLI configuration strings.

    Allows incremental building of config by appending lines. Multi-line strings
    are automatically split on newlines.
    """

    def __init__(self) -> None:
        """Initialize empty accumulator."""
        self._lines: list[str] = []

    def append(self, line: str | None) -> None:
        """
        Append a CLI line or multi-line string.

        Multi-line strings are split on newlines. None values are ignored.
        """
        if line:
            if "\n" in line:
                self._lines.extend(line.split("\n"))
            else:
                self._lines.append(line)

    def extend(self, lines: list[str] | None) -> None:
        """Extend with multiple CLI lines. None values are ignored."""
        if lines:
            self._lines.extend(lines)

    def get_config(self) -> str:
        """Return accumulated lines joined with newlines."""
        return "\n".join(self._lines)

    def clear(self) -> None:
        """Clear all accumulated config."""
        self._lines.clear()

    def __str__(self) -> str:
        """Return accumulated config as string."""
        return self.get_config()

    def __bool__(self) -> bool:
        """Return True if any config has been accumulated."""
        return bool(self._lines)


# Overload when assigned with args.
@overload
def cli_config_contributor(
    func: None = None, *, toggle_and_value: tuple[str, bool] | None = None
) -> Callable[[Callable[[T_CliGeneratorSubclass], None]], Callable[[T_CliGeneratorSubclass], None]]: ...


# Overload when assigned without args.
@overload
def cli_config_contributor(func: Callable[[T_CliGeneratorSubclass], None]) -> Callable[[T_CliGeneratorSubclass], None]: ...


def cli_config_contributor(
    func: Callable[[T_CliGeneratorSubclass], None] | None = None, *, toggle_and_value: tuple[str, bool] | None = None
) -> Callable[[T_CliGeneratorSubclass], None] | Callable[[Callable[[T_CliGeneratorSubclass], None]], Callable[[T_CliGeneratorSubclass], None]]:
    """
    Mark methods as CLI config contributors that get called during render().

    Methods should append to self.cli_config instead of returning strings.

    Args:
        func: The method to decorate.
        toggle_and_value: Optional (attribute_path, expected_value) tuple for conditional
            execution. Path can be nested like 'vlan_settings.enabled'. Method only runs
            if self.data.{path} == expected_value.
    """

    def decorator(fnc: Callable[[T_CliGeneratorSubclass], None]) -> Callable[[T_CliGeneratorSubclass], None]:
        fnc._is_cli_config_contributor = True  # pyright: ignore [reportFunctionMemberAccess]

        if toggle_and_value is None:
            return fnc

        toggle, toggle_value = toggle_and_value

        @wraps(fnc)
        def wrapped_func(self: T_CliGeneratorSubclass) -> None:
            # Navigate nested attributes
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
        return decorator(func)

    return decorator


class CliGeneratorProtocol(Protocol):
    """
    Protocol for CLI generators.

    Generators render EOS config sections using contributor methods that append
    to self.cli_config. The render() method executes all contributors and returns
    the final config string.
    """

    data: EosCliConfigGen
    """Structured configuration data."""

    cli_config: CliConfig
    """Config accumulator."""

    def render(self) -> str:
        """
        Execute all contributor methods and return generated config.

        Returns:
            CLI configuration text or empty string if not applicable.
        """
        self.cli_config.clear()

        for method in self.cli_config_methods():
            method(self)

        return self.cli_config.get_config()

    @classmethod
    def cli_config_methods(cls) -> list[Callable[[Self], None]]:
        """Return methods decorated with @cli_config_contributor."""
        methods: list[Callable[[Self], None]] = []
        for key in cls._keys():
            method = getattr(cls, key)
            if getattr(method, "_is_cli_config_contributor", False):
                methods.append(method)
        return methods

    @classmethod
    def _keys(cls) -> list[str]:
        """Return all attribute names of the class."""
        return dir(cls)


class CliGenerator(CliGeneratorProtocol):
    """
    Base class for CLI configuration generators.

    Subclasses define methods decorated with @cli_config_contributor that append
    config to self.cli_config, then call render() to get the final output.
    """

    def __init__(self, structured_config: EosCliConfigGen | dict) -> None:
        """
        Initialize with structured config data.

        Args:
            structured_config: Dict or EosCliConfigGen model. Dicts are converted to the model.
        """
        if isinstance(structured_config, dict):
            self.data = EosCliConfigGen(**structured_config)
        else:
            self.data = structured_config

        self.cli_config = CliConfig()

    def render(self) -> str:
        """
        Execute all contributor methods and return generated config.

        Returns:
            CLI configuration text or empty string if not applicable.
        """
        self.cli_config.clear()

        for method in self.cli_config_methods():
            method(self)

        return self.cli_config.get_config()

    @classmethod
    def cli_config_methods(cls) -> list[Callable[[Self], None]]:
        """Return methods decorated with @cli_config_contributor."""
        methods: list[Callable[[Self], None]] = []
        for key in cls._keys():
            method = getattr(cls, key)
            if getattr(method, "_is_cli_config_contributor", False):
                methods.append(method)
        return methods

    @classmethod
    def _keys(cls) -> list[str]:
        """Return all attribute names. Override to customize contributor execution order."""
        return dir(cls)
