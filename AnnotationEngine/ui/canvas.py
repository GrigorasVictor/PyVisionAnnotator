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
    QPen, QColor, QBrush, QPolygonF, QPainter,
    QImage,
)
from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsItem,
)

from core.annotation import BoundingBoxItem, PolygonItem, MaskItem


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
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return

        old_items = self._manager.clear()
        for item in old_items:
            self._scene.removeItem(item)
        if self._pixmap_item is not None:
            self._scene.removeItem(self._pixmap_item)

        self._original_pixmap = pixmap
        display_pixmap = self._apply_adjustments(pixmap)

        self._pixmap_item = QGraphicsPixmapItem(display_pixmap)
        self._pixmap_item.setZValue(0)
        self._scene.addItem(self._pixmap_item)
        self._scene.setSceneRect(QRectF(pixmap.rect().toRectF()))

        self._manager.image_path = path
        self._manager.image_width = pixmap.width()
        self._manager.image_height = pixmap.height()

        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.image_loaded.emit(path, pixmap.width(), pixmap.height())

    # ------------------------------------------------------------------ #
    #  Image adjustments
    # ------------------------------------------------------------------ #
    def set_brightness(self, value: int) -> None:
        """Set brightness offset. Range: -100 to +100."""
        self._brightness = value
        self._refresh_display()

    def set_contrast(self, value: float) -> None:
        """Set contrast multiplier. Range: 0.0 to 3.0."""
        self._contrast = value
        self._refresh_display()

    def set_gamma(self, value: float) -> None:
        """Set gamma correction. Range: 0.1 to 3.0."""
        self._gamma = value
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Re-apply adjustments to the displayed pixmap (does NOT change original)."""
        if self._original_pixmap is None or self._pixmap_item is None:
            return
        display = self._apply_adjustments(self._original_pixmap)
        self._pixmap_item.setPixmap(display)

    def _apply_adjustments(self, source: QPixmap) -> QPixmap:
        """Apply brightness, contrast and gamma to *source* and return a new QPixmap."""
        if self._brightness == 0 and self._contrast == 1.0 and self._gamma == 1.0:
            return source

        img: QImage = source.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        width, height = img.width(), img.height()

        # Build lookup table for 0-255
        import array
        lut = array.array('i', [0] * 256)
        for i in range(256):
            # 1. Gamma
            g = (i / 255.0) ** (1.0 / self._gamma) * 255.0
            # 2. Contrast (around mid-grey 128)
            c = (g - 128.0) * self._contrast + 128.0
            # 3. Brightness
            b = c + self._brightness
            lut[i] = max(0, min(255, int(b)))

        # Apply per-pixel using bits() buffer
        ptr = img.bits()
        ptr.setsize(width * height * 4)
        buf = bytearray(ptr)

        for idx in range(0, len(buf), 4):
            buf[idx]     = lut[buf[idx]]      # B
            buf[idx + 1] = lut[buf[idx + 1]]  # G
            buf[idx + 2] = lut[buf[idx + 2]]  # R
            # buf[idx + 3] = Alpha, untouched

        result_img = QImage(bytes(buf), width, height, QImage.Format.Format_ARGB32)
        return QPixmap.fromImage(result_img)

    # ------------------------------------------------------------------ #
    #  Crosshair
    # ------------------------------------------------------------------ #
    def set_crosshair(self, enabled: bool) -> None:
        self._crosshair_enabled = enabled
        self.viewport().update()

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        """Draw crosshair + brush-cursor circle on top in viewport space."""
        super().drawForeground(painter, rect)

        if self._mouse_pos_viewport is None:
            return

        painter.save()
        painter.resetTransform()

        vp   = self.viewport()
        mx   = self._mouse_pos_viewport.x()
        my   = self._mouse_pos_viewport.y()

        # ---- brush / eraser circle cursor -------------------- #
        if self._current_tool in ("brush", "eraser") and not self._space_held:
            radius_scene = self._brush_size / 2.0
            scale        = self.transform().m11()          # pixels-per-scene-unit
            radius_vp    = radius_scene * scale

            if self._current_tool == "eraser":
                pen_col = QColor(255, 80, 80)
            else:
                pen_col = QColor(255, 255, 255)

            painter.setPen(QPen(pen_col, 1, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            from PyQt6.QtCore import QPointF as _QPointF
            painter.drawEllipse(_QPointF(mx, my), radius_vp, radius_vp)

            # small centre dot
            painter.setPen(QPen(pen_col, 2))
            painter.drawPoint(int(mx), int(my))

        # ---- crosshair ----------------------------------------------- #
        if self._crosshair_enabled:
            pen = QPen(QColor(0, 255, 128, 180), 1, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawLine(0, int(my), vp.width(), int(my))
            painter.drawLine(int(mx), 0, int(mx), vp.height())

        painter.restore()

    # ------------------------------------------------------------------ #
    #  Tools
    # ------------------------------------------------------------------ #
    def set_tool(self, tool_mode: str) -> None:
        self._current_tool = tool_mode
        self._painting = False
        self._paint_target = None
        self._drawing = False
        self._poly_points = []
        if self._rubber_band:
            if self._rubber_band.scene() == self._scene:
                self._scene.removeItem(self._rubber_band)
            self._rubber_band = None
        if hasattr(self, '_rubber_lines'):
            for line in self._rubber_lines:
                if line.scene() == self._scene:
                    self._scene.removeItem(line)
            self._rubber_lines.clear()
        if self._rubber_poly:
            if self._rubber_poly.scene() == self._scene:
                self._scene.removeItem(self._rubber_poly)
            self._rubber_poly = None

    def set_brush_size(self, size: int) -> None:
        """Set the brush / eraser diameter in scene pixels."""
        self._brush_size = max(1, size)

    # ------------------------------------------------------------------ #
    #  Zoom
    # ------------------------------------------------------------------ #
    def wheelEvent(self, event: QWheelEvent) -> None:
        angle = event.angleDelta().y()
        if angle > 0:
            factor = self._ZOOM_FACTOR
        elif angle < 0:
            factor = 1.0 / self._ZOOM_FACTOR
        else:
            return
        current_scale = self.transform().m11()
        new_scale = current_scale * factor
        if new_scale < self._ZOOM_MIN or new_scale > self._ZOOM_MAX:
            return
        self.scale(factor, factor)

    # ------------------------------------------------------------------ #
    #  Key events
    # ------------------------------------------------------------------ #
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = True
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        elif event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._current_tool == "polygon" and self._drawing:
                if len(self._poly_points) > 2:
                    self._finish_polygon()
                else:
                    self._cancel_polygon()
                event.accept()
                return
        elif event.key() == Qt.Key.Key_Escape:
            if self._drawing:
                self._cancel_polygon()
                self._drawing = False
                if self._rubber_band:
                    self._scene.removeItem(self._rubber_band)
                    self._rubber_band = None
                event.accept()
                return
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = False
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().keyReleaseEvent(event)

    # ------------------------------------------------------------------ #
    #  Mouse events
    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event: QMouseEvent) -> None:
        btn = event.button()

        if btn == Qt.MouseButton.MiddleButton or (
            btn == Qt.MouseButton.LeftButton and self._space_held
        ):
            self._panning = True
            self._pan_start = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if btn == Qt.MouseButton.LeftButton and not self._space_held:
            scene_pos: QPointF = self.mapToScene(event.pos())

            # ---- brush / eraser -------------------------------- #
            if self._current_tool in ("brush", "eraser"):
                target = self._find_selected_mask()
                if target is None:
                    # Try clicking directly on a MaskItem
                    item_under = self.itemAt(event.pos())
                    if isinstance(item_under, MaskItem):
                        self._scene.clearSelection()
                        item_under.setSelected(True)
                        target = item_under
                if target is not None:
                    self._painting = True
                    self._paint_target = target
                    self._apply_paint(target, scene_pos)
                event.accept()
                return

            if self._current_tool == "autoseg":
                if self._autoseg_busy:
                    event.accept()
                    return
                if self._pixmap_item is None:
                    event.accept()
                    return
                # Show a visual click marker
                self._remove_autoseg_marker()
                marker_size = 10.0
                pen = QPen(QColor(0, 255, 0), 2)
                brush = QBrush(QColor(0, 255, 0, 120))
                self._autoseg_marker = self._scene.addEllipse(
                    scene_pos.x() - marker_size / 2,
                    scene_pos.y() - marker_size / 2,
                    marker_size, marker_size, pen, brush,
                )
                self._autoseg_marker.setZValue(25)
                self._autoseg_busy = True
                self.autoseg_requested.emit(scene_pos)
                event.accept()
                return

            if self._current_tool == "polygon":
                if self._drawing:
                    self._poly_points.append(scene_pos)
                    self._update_rubber_poly()
                    event.accept()
                    return
                else:
                    item_under = self.itemAt(event.pos())
                    if isinstance(item_under, (BoundingBoxItem, PolygonItem, MaskItem)):
                        super().mousePressEvent(event)
                        return
                    self._drawing = True
                    self._poly_points = [scene_pos]
                    self._update_rubber_poly()
                    event.accept()
                    return

            elif self._current_tool == "rectangle":
                item_under = self.itemAt(event.pos())
                if isinstance(item_under, (BoundingBoxItem, PolygonItem, MaskItem)):
                    super().mousePressEvent(event)
                    return
                self._drawing = True
                self._draw_origin = scene_pos
                pen = QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine)
                self._rubber_band = self._scene.addRect(QRectF(scene_pos, scene_pos), pen)
                self._rubber_band.setZValue(20)
                event.accept()
                return

        if btn == Qt.MouseButton.RightButton and self._current_tool == "polygon" and self._drawing:
            if len(self._poly_points) > 2:
                self._finish_polygon()
            else:
                self._cancel_polygon()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        # Update crosshair / brush cursor
        self._mouse_pos_viewport = event.position()
        self.viewport().update()

        scene_pos = self.mapToScene(event.pos())

        # ---- painting tools ------------------------------------------ #
        if self._painting and self._paint_target is not None:
            self._apply_paint(self._paint_target, scene_pos)
            event.accept()
            return

        if self._panning and self._pan_start is not None:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y()))
            event.accept()
            return

        if (self._current_tool == "rectangle" and self._drawing
                and self._draw_origin is not None
                and self._rubber_band is not None):
            rect = QRectF(self._draw_origin, scene_pos).normalized()
            self._rubber_band.setRect(rect)
            event.accept()
            return

        if self._current_tool == "polygon" and self._drawing and self._poly_points:
            for line in self._rubber_lines:
                self._scene.removeItem(line)
            self._rubber_lines.clear()
            pen = QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine)
            for i in range(len(self._poly_points) - 1):
                a, b = self._poly_points[i], self._poly_points[i + 1]
                li = self._scene.addLine(a.x(), a.y(), b.x(), b.y(), pen)
                li.setZValue(20)
                self._rubber_lines.append(li)
            last = self._poly_points[-1]
            li = self._scene.addLine(
                last.x(), last.y(), scene_pos.x(), scene_pos.y(), pen)
            li.setZValue(20)
            self._rubber_lines.append(li)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        btn = event.button()

        # Stop painting
        if self._painting and btn == Qt.MouseButton.LeftButton:
            self._painting = False
            self._paint_target = None
            event.accept()
            return

        if self._panning and (btn == Qt.MouseButton.MiddleButton or btn == Qt.MouseButton.LeftButton):
            self._panning = False
            self._pan_start = None
            cursor = Qt.CursorShape.OpenHandCursor if self._space_held else Qt.CursorShape.ArrowCursor
            self.viewport().setCursor(cursor)
            event.accept()
            return

        if self._current_tool == "rectangle" and self._drawing and btn == Qt.MouseButton.LeftButton:
            self._drawing = False
            if self._rubber_band is not None:
                rect: QRectF = self._rubber_band.rect()
                self._scene.removeItem(self._rubber_band)
                self._rubber_band = None
                if rect.width() > 4 and rect.height() > 4:
                    rect = self._clamp_rect_to_image(rect)
                    item = self._manager.add_rect(
                        rect.x(), rect.y(), rect.width(), rect.height(),
                        label=self._manager.default_label,
                        color=self._manager.default_color,
                    )
                    self._scene.addItem(item)
            self._draw_origin = None
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._current_tool == "polygon" and self._drawing:
            if len(self._poly_points) > 2:
                self._finish_polygon()
            else:
                self._cancel_polygon()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event) -> None:
        """Hide crosshair when mouse leaves the viewport."""
        self._mouse_pos_viewport = None
        self.viewport().update()
        super().leaveEvent(event)

    # ------------------------------------------------------------------ #
    #  Polygon helpers
    # ------------------------------------------------------------------ #
    def _update_rubber_poly(self) -> None:
        for line in self._rubber_lines:
            self._scene.removeItem(line)
        self._rubber_lines.clear()
        if len(self._poly_points) < 2:
            return
        pen = QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine)
        for i in range(len(self._poly_points) - 1):
            a, b = self._poly_points[i], self._poly_points[i + 1]
            li = self._scene.addLine(a.x(), a.y(), b.x(), b.y(), pen)
            li.setZValue(20)
            self._rubber_lines.append(li)

    def _finish_polygon(self) -> None:
        self._drawing = False
        for line in self._rubber_lines:
            self._scene.removeItem(line)
        self._rubber_lines.clear()
        if self._rubber_poly:
            self._scene.removeItem(self._rubber_poly)
            self._rubber_poly = None
        if len(self._poly_points) > 2:
            poly = QPolygonF()
            for p in self._poly_points:
                poly.append(QPointF(p.x(), p.y()))
            item = self._manager.add_poly(poly, label=self._manager.default_label, color=self._manager.default_color)
            self._scene.addItem(item)
        self._poly_points = []

    def _cancel_polygon(self) -> None:
        self._drawing = False
        self._poly_points = []
        for line in self._rubber_lines:
            self._scene.removeItem(line)
        self._rubber_lines.clear()
        if self._rubber_poly:
            self._scene.removeItem(self._rubber_poly)
            self._rubber_poly = None

    # ------------------------------------------------------------------ #
    #  Mask-painting helpers
    # ------------------------------------------------------------------ #
    def _find_selected_mask(self) -> Optional[MaskItem]:
        """Return the first selected MaskItem, or None."""
        for item in self._scene.selectedItems():
            if isinstance(item, MaskItem):
                return item
        return None

    def _apply_paint(self, target: MaskItem, scene_pos: QPointF) -> None:
        """Dispatch a single paint stroke to the target MaskItem."""
        radius = self._brush_size / 2.0
        if self._current_tool == "brush":
            target.paint_brush(scene_pos, radius)
        elif self._current_tool == "eraser":
            target.erase_brush(scene_pos, radius)

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
        coords = data.get("coordinates", [])
        if not coords or len(coords) < 3:
            self._autoseg_reset()
            return

        label = data.get("label", self._manager.default_label)
        color = self._manager.default_color

        item = self._manager.add_mask(
            coords,
            label=label,
            color=color,
        )
        self._scene.addItem(item)
        self._autoseg_reset()

    def autoseg_error_received(self, message: str) -> None:
        """Slot: called when AutoSegWorker fails."""
        self._autoseg_reset()

    def _autoseg_reset(self) -> None:
        """Clear AutoSeg busy flag and remove the click marker."""
        self._autoseg_busy = False
        self._remove_autoseg_marker()

    def _remove_autoseg_marker(self) -> None:
        if self._autoseg_marker is not None:
            if self._autoseg_marker.scene() == self._scene:
                self._scene.removeItem(self._autoseg_marker)
            self._autoseg_marker = None

