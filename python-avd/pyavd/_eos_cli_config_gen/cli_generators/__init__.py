# Copyright (c) 2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""
CLI configuration generators for EOS CLI Config Gen.

This package contains Python-based CLI configuration generators that replace Jinja2 templates.
Each generator is a class that inherits from CliGenerator and implements a render() method.
"""

from __future__ import annotations

from .config_comment import ConfigCommentGenerator

__all__ = [
    "ConfigCommentGenerator",
]
