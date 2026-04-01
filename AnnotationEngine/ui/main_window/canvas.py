"""
ui/canvas.py — AnnotationCanvas

Custom QGraphicsView that supports:
  • Loading an image as a QGraphicsPixmapItem
  • Zoom (mouse wheel, anchored at cursor)
  • Pan  (middle-button drag  **or**  Space + left-click drag)
  • Drawing bounding boxes (left-click drag → BoundingBoxItem)
  • Crosshair overlay (permanent, follows mouse)
  • Live brightness / contrast / gamma adjustment (visual-only, no pixel changes)

All rectangle coordinates are in **scene / image-pixel** space so they
map 1-to-1 with the underlying image regardless of zoom or scroll.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QMouseEvent, QWheelEvent, QKeyEvent, QPixmap,
    QColor, QBrush, QPainter,
)
from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsItem,
)

from core.annotation import BoundingBoxItem, PolygonItem, MaskItem
from utils.canvas_helpers.canvas_helpers import (
    load_image as _load_image,
    set_brightness as _set_brightness,
    set_contrast as _set_contrast,
    set_gamma as _set_gamma,
    refresh_display as _refresh_display,
    apply_adjustments as _apply_adjustments,
    find_selected_mask as _find_selected_mask,
    apply_paint as _apply_paint,
    update_rubber_poly as _update_rubber_poly,
    finish_polygon as _finish_polygon,
    cancel_polygon as _cancel_polygon,
    autoseg_result_received as _autoseg_result_received,
    autoseg_error_received as _autoseg_error_received,
    autoseg_reset as _autoseg_reset,
    remove_autoseg_marker as _remove_autoseg_marker,
)
from utils.canvas_helpers.canvas_events import (
    wheel_event as _wheel_event,
    key_press_event as _key_press_event,
    key_release_event as _key_release_event,
    mouse_press_event as _mouse_press_event,
    mouse_move_event as _mouse_move_event,
    mouse_release_event as _mouse_release_event,
    mouse_double_click_event as _mouse_double_click_event,
    leave_event as _leave_event,
)
from utils.canvas_helpers.canvas_render import draw_foreground as _draw_foreground
from utils.canvas_helpers.canvas_tools import set_tool as _set_tool


class AnnotationCanvas(QGraphicsView):
    """Interactive canvas for viewing images and drawing annotations."""

    # Zoom limits
    _ZOOM_MIN = 0.1
    _ZOOM_MAX = 20.0
    _ZOOM_FACTOR = 1.15

    image_loaded = pyqtSignal(str, int, int)
    autoseg_requested = pyqtSignal(QPointF)      # scene-space click point

    def __init__(self, annotation_manager, parent=None) -> None:
        super().__init__(parent)

        self._manager = annotation_manager
        self._current_tool: str = "rectangle"
        self._autoseg_busy: bool = False
        self._autoseg_marker: Optional[QGraphicsRectItem] = None

        # Brush / spray / eraser state
        self._brush_size: int = 20          # diameter in scene pixels
        self._painting: bool = False
        self._paint_target: Optional[MaskItem] = None

        # Scene
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Pixmap items — _pixmap_item holds the ORIGINAL unmodified pixmap for reference
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._original_pixmap: Optional[QPixmap] = None   # store original for re-applying adjustments

        # Image adjustments (visual only)
        self._brightness: int = 0      # -100 to +100
        self._contrast: float = 1.0    # 0.0 to 3.0
        self._gamma: float = 1.0       # 0.1 to 3.0

        # Crosshair state
        self._crosshair_enabled: bool = True
        self._mouse_pos_viewport: Optional[QPointF] = None
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        # Rubber-band drawing state
        self._drawing: bool = False
        self._draw_origin: Optional[QPointF] = None
        self._rubber_band: Optional[QGraphicsRectItem] = None

        # Polygon drawing state
        self._poly_points: list[QPointF] = []
        self._rubber_poly: Optional[QGraphicsItem] = None
        self._rubber_lines: list = []

        # Pan state
        self._panning: bool = False
        self._pan_start: Optional[QPointF] = None
        self._space_held: bool = False

        # View settings
        from PyQt6.QtGui import QPainter as _QPainter
        self.setRenderHints(
            _QPainter.RenderHint.Antialiasing
            | _QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))

    # ------------------------------------------------------------------ #
    #  Image loading
    # ------------------------------------------------------------------ #
    def load_image(self, path: str) -> None:
        _load_image(self, path)

    # ------------------------------------------------------------------ #
    #  Image adjustments
    # ------------------------------------------------------------------ #
    def set_brightness(self, value: int) -> None:
        """Set brightness offset. Range: -100 to +100."""
        _set_brightness(self, value)

    def set_contrast(self, value: float) -> None:
        """Set contrast multiplier. Range: 0.0 to 3.0."""
        _set_contrast(self, value)

    def set_gamma(self, value: float) -> None:
        """Set gamma correction. Range: 0.1 to 3.0."""
        _set_gamma(self, value)

    def _refresh_display(self) -> None:
        """Re-apply adjustments to the displayed pixmap (does NOT change original)."""
        _refresh_display(self)

    def _apply_adjustments(self, source: QPixmap) -> QPixmap:
        """Apply brightness, contrast and gamma to *source* and return a new QPixmap."""
        return _apply_adjustments(self, source)

    # ------------------------------------------------------------------ #
    #  Crosshair
    # ------------------------------------------------------------------ #
    def set_crosshair(self, enabled: bool) -> None:
        self._crosshair_enabled = enabled
        self.viewport().update()

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        """Draw crosshair + brush-cursor circle on top in viewport space."""
        _draw_foreground(self, painter, rect)

    # ------------------------------------------------------------------ #
    #  Tools
    # ------------------------------------------------------------------ #
    def set_tool(self, tool_mode: str) -> None:
        _set_tool(self, tool_mode)

    def set_brush_size(self, size: int) -> None:
        """Set the brush / eraser diameter in scene pixels."""
        self._brush_size = max(1, size)

    # ------------------------------------------------------------------ #
    #  Zoom
    # ------------------------------------------------------------------ #
    def wheelEvent(self, event: QWheelEvent) -> None:
        _wheel_event(self, event)

    # ------------------------------------------------------------------ #
    #  Key events
    # ------------------------------------------------------------------ #
    def keyPressEvent(self, event: QKeyEvent) -> None:
        _key_press_event(self, event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        _key_release_event(self, event)

    # ------------------------------------------------------------------ #
    #  Mouse events
    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event: QMouseEvent) -> None:
        _mouse_press_event(self, event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        _mouse_move_event(self, event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        _mouse_release_event(self, event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        _mouse_double_click_event(self, event)

    def leaveEvent(self, event) -> None:
        """Hide crosshair when mouse leaves the viewport."""
        _leave_event(self, event)

    # ------------------------------------------------------------------ #
    #  Polygon helpers
    # ------------------------------------------------------------------ #
    def _update_rubber_poly(self) -> None:
        _update_rubber_poly(self)

    def _finish_polygon(self) -> None:
        _finish_polygon(self)

    def _cancel_polygon(self) -> None:
        _cancel_polygon(self)

    # ------------------------------------------------------------------ #
    #  Mask-painting helpers
    # ------------------------------------------------------------------ #
    def _find_selected_mask(self) -> Optional[MaskItem]:
        """Return the first selected MaskItem, or None."""
        return _find_selected_mask(self)

    def _apply_paint(self, target: MaskItem, scene_pos: QPointF) -> None:
        """Dispatch a single paint stroke to the target MaskItem."""
        _apply_paint(self, target, scene_pos)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _clamp_rect_to_image(self, rect: QRectF) -> QRectF:
        if self._pixmap_item is None:
            return rect
        return rect.intersected(self._pixmap_item.boundingRect())

    def delete_selected(self) -> None:
        for item in self._scene.selectedItems():
            if isinstance(item, (BoundingBoxItem, PolygonItem, MaskItem)):
                self._manager.remove(item.annotation_id)
                self._scene.removeItem(item)

    def add_annotation_item(self, item: BoundingBoxItem | PolygonItem | MaskItem) -> None:
        self._scene.addItem(item)

    # ------------------------------------------------------------------ #
    #  AutoSeg helpers
    # ------------------------------------------------------------------ #
    def autoseg_result_received(self, data: dict) -> None:
        """Slot: called when AutoSegWorker finishes successfully.

        Passes the returned pixel coordinates directly to MaskItem for
        rasterised pixel rendering — O(1) regardless of point count.
        """
        _autoseg_result_received(self, data)

    def autoseg_error_received(self, message: str) -> None:
        """Slot: called when AutoSegWorker fails."""
        _autoseg_error_received(self, message)

    def _autoseg_reset(self) -> None:
        """Clear AutoSeg busy flag and remove the click marker."""
        _autoseg_reset(self)

    def _remove_autoseg_marker(self) -> None:
        _remove_autoseg_marker(self)

