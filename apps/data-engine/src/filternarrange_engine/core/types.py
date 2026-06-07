# SPDX-License-Identifier: Apache-2.0
"""Canonical type tags shared by every plugin."""
from __future__ import annotations
from enum import Enum


class TypeTag(str, Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    NULL = "null"


__all__ = ["TypeTag"]
