# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
Python-based device configuration generator.

This module provides an alternative to the Jinja2-based get_device_config
that uses native Python generators for better performance and maintainability.

It can coexist with the Jinja2 version during the migration period, using
Python generators where available and falling back to Jinja2 templates for
sections that haven't been migrated yet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api.schemas import EOSConfig


def get_device_config_python(structured_config: EOSConfig | dict) -> str:
    """
    Render and return device configuration using Python generators with Jinja2 fallback.

    Python sections are rendered FIRST, then Jinja2 sections for the rest.

    Args:
        structured_config:
            EOSConfig instance or dictionary with the validated structured configuration.

    Returns:
        Device configuration in EOS CLI format.
    """
    from ._eos_cli_config_gen import cli_generators  # noqa: PLC0415
    from .get_device_config import get_device_config  # noqa: PLC0415

    sections = []

    # Render Python sections (order defined in cli_generators.__all__)
    for generator_class_name in cli_generators.__all__:
        generator_class = getattr(cli_generators, generator_class_name)
        generator = generator_class(structured_config)
        if output := generator.render():
            sections.append(output)

    # Render Jinja2 sections
    sections.append(get_device_config(structured_config))

    return "\n".join(section for section in sections if section)
