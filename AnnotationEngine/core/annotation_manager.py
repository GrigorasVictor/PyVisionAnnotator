"""
core/annotation_manager.py — AnnotationManager

Central store that owns every BoundingBoxItem for the current image.
Emits Qt signals so the UI can react to additions / removals.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QPointF
from PyQt6.QtGui import QPolygonF

from core.annotation import BoundingBoxItem, PolygonItem, MaskItem


class AnnotationManager(QObject):
    """Single source of truth for annotations on the active image.

    Signals:
        annotation_added(annotation_id):   Emitted after a box is added.
        annotation_removed(annotation_id): Emitted after a box is removed.
        annotations_cleared():             Emitted when all boxes are removed.
    """

    annotation_added = pyqtSignal(str)
    annotation_removed = pyqtSignal(str)
    annotation_updated = pyqtSignal(str)
    annotations_cleared = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._annotations: dict[str, BoundingBoxItem | PolygonItem | MaskItem] = {}

        # Default properties for NEW annotations
        self.default_label: str = ""
        self.default_color: str = "#ff3232"

        # Color generation
        self._label_colors: dict[str, str] = {}
        # A palette of distinct colors for auto-coloring labels
        self._color_palette = [
            "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
            "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
            "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000",
            "#aaffc3", "#808000", "#ffd8b1", "#000075", "#808080",
            "#ffffff", "#000000"
        ]

        # Global style settings
        self.settings_pen_width: int = 2
        self.settings_font_size: int = 9
        self.settings_label_height: int = 18
        self.settings_mask_opacity: int = 31  # percent (0-100)

        # Current image metadata — updated by the canvas on load
        self.image_path: str = ""
        self.image_width: int = 0
        self.image_height: int = 18

    def get_color_for_label(self, label: str) -> str:
        """Return a consistent color for the given label.

        If the label has been seen before, returns its cached color.
        Otherwise, assigns a new color from the palette based on hash.
        """
        if not label:
            return self.default_color
            
        if label in self._label_colors:
            return self._label_colors[label]

        # Assign a color based on simple hashing
        idx = abs(hash(label)) % len(self._color_palette)
        color = self._color_palette[idx]
        self._label_colors[label] = color
        return color

    # ------------------------------------------------------------------ #
    #  CRUD
    # ------------------------------------------------------------------ #
    def add_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        annotation_id: Optional[str] = None,
        label: str = "",
        color: str = "#ff3232",
    ) -> BoundingBoxItem:
        """Create a new BoundingBoxItem, store it and emit *annotation_added*.

        Returns:
            The newly created ``BoundingBoxItem``.
        """
        item = BoundingBoxItem(
            x, y, w, h,
            annotation_id=annotation_id,
            label=label,
            color=color,
        )
        # Apply global settings
        item.pen_width = self.settings_pen_width
        item.font_size = self.settings_font_size
        item.label_height = self.settings_label_height

        self._annotations[item.annotation_id] = item
        self.annotation_added.emit(item.annotation_id)
        return item

    def add_poly(
        self,
        points: QPolygonF,
        annotation_id: Optional[str] = None,
        label: str = "",
        color: str = "#ff3232",
    ) -> PolygonItem:
        """Create a new PolygonItem from a QPolygonF, store it and emit *annotation_added*."""
        item = PolygonItem(
            points,
            annotation_id=annotation_id,
            label=label,
            color=color,
        )
        # Apply global settings
        item.pen_width = self.settings_pen_width
        item.font_size = self.settings_font_size
        item.label_height = self.settings_label_height

        self._annotations[item.annotation_id] = item
        self.annotation_added.emit(item.annotation_id)
        return item

    def add_mask(
        self,
        points: list[list[float]],
        annotation_id: Optional[str] = None,
        label: str = "",
        color: str = "#ff3232",
        bbox_x: Optional[float] = None,
        bbox_y: Optional[float] = None,
        bbox_w: Optional[float] = None,
        bbox_h: Optional[float] = None,
    ) -> MaskItem:
        """Create a new MaskItem from raw ``[[x,y], …]`` pixel coords (AutoSeg).

        Uses pixel rasterisation for O(1) render regardless of point count.
        """
        item = MaskItem(
            points,
            annotation_id=annotation_id,
            label=label,
            color=color,
        )
        item.pen_width = self.settings_pen_width
        item.font_size = self.settings_font_size
        item.label_height = self.settings_label_height
        item.fill_alpha = self._opacity_percent_to_alpha(self.settings_mask_opacity)
        if None not in (bbox_x, bbox_y, bbox_w, bbox_h):
            item.set_bbox_rect(float(bbox_x), float(bbox_y), float(bbox_w), float(bbox_h))

        self._annotations[item.annotation_id] = item
        self.annotation_added.emit(item.annotation_id)
        return item

    # Kept for backward compatibility, forwards to add_rect
    def add(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        annotation_id: Optional[str] = None,
        label: str = "",
        color: str = "#ff3232",
    ) -> BoundingBoxItem:
        """Legacy alias for add_rect."""
        return self.add_rect(x, y, w, h, annotation_id, label, color)

    def remove(self, annotation_id: str) -> Optional[BoundingBoxItem | PolygonItem | MaskItem]:
        """Remove an annotation by its id.

        Returns:
            The removed ``BoundingBoxItem``, or ``None`` if not found.
        """
        item = self._annotations.pop(annotation_id, None)
        if item is not None:
            self.annotation_removed.emit(annotation_id)
        return item

    def clear(self) -> list[BoundingBoxItem | PolygonItem | MaskItem]:
        """Remove **all** annotations and emit *annotations_cleared*.

        Returns:
            List of removed items (so the canvas can remove them from the scene).
        """
        items = list(self._annotations.values())
        self._annotations.clear()
        self.annotations_cleared.emit()
        return items

    # ------------------------------------------------------------------ #
    #  Queries
    # ------------------------------------------------------------------ #
    def get(self, annotation_id: str) -> Optional[BoundingBoxItem | PolygonItem | MaskItem]:
        """Return a single item by id, or ``None``."""
        return self._annotations.get(annotation_id)

    def get_all(self) -> list[BoundingBoxItem | PolygonItem | MaskItem]:
        """Return a list of every stored BoundingBoxItem."""
        return list(self._annotations.values())

    def get_all_dicts(self) -> list[dict]:
        """Return serialisable dicts for every annotation."""
        return [item.to_dict() for item in self._annotations.values()]

    def count(self) -> int:
        return len(self._annotations)

    def update_item(self, annotation_id: str) -> None:
        """Notify listeners that an annotation has been modified."""
        if annotation_id in self._annotations:
            self.annotation_updated.emit(annotation_id)

    def update_global_settings(self, pen_width: int, font_size: int, label_height: int) -> None:
        """Update style settings for all existing and future annotations."""
        self.settings_pen_width = pen_width
        self.settings_font_size = font_size
        self.settings_label_height = label_height

        for item in self._annotations.values():
            item.pen_width = pen_width
            item.label_height = label_height
            if isinstance(item, (BoundingBoxItem, PolygonItem, MaskItem)):
                item.font_size = font_size

    @staticmethod
    def _opacity_percent_to_alpha(opacity: int) -> int:
        pct = max(0, min(100, int(opacity)))
        return int(round((pct / 100.0) * 255))

    def set_mask_opacity(self, opacity: int) -> None:
        """Update mask fill opacity for existing and future masks (0-100%)."""
        self.settings_mask_opacity = max(0, min(100, int(opacity)))
        alpha = self._opacity_percent_to_alpha(self.settings_mask_opacity)
        for item in self._annotations.values():
            if isinstance(item, MaskItem):
                item.fill_alpha = alpha

    # ------------------------------------------------------------------ #
    #  Bulk loading (e.g. from JSON)
    # ------------------------------------------------------------------ #
    def load_annotations(self, data: list[dict]) -> list[BoundingBoxItem | PolygonItem | MaskItem]:
        """Create Items from a list of dicts.

        Each dict must contain at least ``x, y, w, h`` (for rect),
        ``points`` with ``type=poly`` (QPolygonF), or ``points`` with
        ``type=mask`` (pixel raster).

        Optional keys: ``id``, ``label``, ``color``, ``type``.

        Returns:
            List of created items.
        """
        items: list[BoundingBoxItem | PolygonItem | MaskItem] = []
        for entry in data:
            atype = entry.get("type", "rect")

            if atype == "mask" and "points" in entry:
                item = self.add_mask(
                    entry["points"],
                    annotation_id=entry.get("id"),
                    label=entry.get("label", ""),
                    color=entry.get("color", "#ff3232"),
                    bbox_x=entry.get("x"),
                    bbox_y=entry.get("y"),
                    bbox_w=entry.get("w"),
                    bbox_h=entry.get("h"),
                )
            elif atype == "poly" and "points" in entry:
                poly = QPolygonF()
                for p in entry["points"]:
                    poly.append(QPointF(float(p[0]), float(p[1])))
                item = self.add_poly(
                    poly,
                    annotation_id=entry.get("id"),
                    label=entry.get("label", ""),
                    color=entry.get("color", "#ff3232"),
                )
            else:
                # Default to rect
                item = self.add_rect(
                    x=entry["x"],
                    y=entry["y"],
                    w=entry["w"],
                    h=entry["h"],
                    annotation_id=entry.get("id"),
                    label=entry.get("label", ""),
                    color=entry.get("color", "#ff3232"),
                )
            items.append(item)
        return items

