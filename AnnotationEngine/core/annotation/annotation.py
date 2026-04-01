"""
Backwards-compatible exports for annotation graphics items.

This module is intentionally kept as a facade so existing imports like
`from core.annotation.annotation import BoundingBoxItem` continue to work
after splitting item implementations into dedicated files.
"""
from __future__ import annotations

from .bounding_box_item import BoundingBoxItem
from .mask_item import MaskItem
from .polygon_item import PolygonItem

__all__ = ["BoundingBoxItem", "PolygonItem", "MaskItem"]
