"""
ui/canvas_helpers.py

Internal helper functions used by AnnotationCanvas to keep ui/canvas.py smaller.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPixmap, QPen, QColor, QPolygonF, QImage

from core.annotation import MaskItem

if TYPE_CHECKING:
    from ui.canvas import AnnotationCanvas


def load_image(canvas: "AnnotationCanvas", path: str) -> None:
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return

    old_items = canvas._manager.clear()
    for item in old_items:
        canvas._scene.removeItem(item)
    if canvas._pixmap_item is not None:
        canvas._scene.removeItem(canvas._pixmap_item)

    canvas._original_pixmap = pixmap
    display_pixmap = apply_adjustments(canvas, pixmap)

    from PyQt6.QtWidgets import QGraphicsPixmapItem
    canvas._pixmap_item = QGraphicsPixmapItem(display_pixmap)
    canvas._pixmap_item.setZValue(0)
    canvas._scene.addItem(canvas._pixmap_item)
    canvas._scene.setSceneRect(QRectF(pixmap.rect().toRectF()))

    canvas._manager.image_path = path
    canvas._manager.image_width = pixmap.width()
    canvas._manager.image_height = pixmap.height()

    canvas.resetTransform()
    canvas.fitInView(canvas._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
    canvas.image_loaded.emit(path, pixmap.width(), pixmap.height())


def set_brightness(canvas: "AnnotationCanvas", value: int) -> None:
    canvas._brightness = value
    refresh_display(canvas)


def set_contrast(canvas: "AnnotationCanvas", value: float) -> None:
    canvas._contrast = value
    refresh_display(canvas)


def set_gamma(canvas: "AnnotationCanvas", value: float) -> None:
    canvas._gamma = value
    refresh_display(canvas)


def refresh_display(canvas: "AnnotationCanvas") -> None:
    if canvas._original_pixmap is None or canvas._pixmap_item is None:
        return
    display = apply_adjustments(canvas, canvas._original_pixmap)
    canvas._pixmap_item.setPixmap(display)


def apply_adjustments(canvas: "AnnotationCanvas", source: QPixmap) -> QPixmap:
    if canvas._brightness == 0 and canvas._contrast == 1.0 and canvas._gamma == 1.0:
        return source

    img: QImage = source.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    width, height = img.width(), img.height()

    import array
    lut = array.array("i", [0] * 256)
    for i in range(256):
        g = (i / 255.0) ** (1.0 / canvas._gamma) * 255.0
        c = (g - 128.0) * canvas._contrast + 128.0
        b = c + canvas._brightness
        lut[i] = max(0, min(255, int(b)))

    ptr = img.bits()
    ptr.setsize(width * height * 4)
    buf = bytearray(ptr.asstring(width * height * 4))

    for idx in range(0, len(buf), 4):
        buf[idx] = lut[buf[idx]]
        buf[idx + 1] = lut[buf[idx + 1]]
        buf[idx + 2] = lut[buf[idx + 2]]

    result_img = QImage(bytes(buf), width, height, QImage.Format.Format_ARGB32)
    return QPixmap.fromImage(result_img)


def find_selected_mask(canvas: "AnnotationCanvas") -> Optional[MaskItem]:
    for item in canvas._scene.selectedItems():
        if isinstance(item, MaskItem):
            return item
    return None


def apply_paint(canvas: "AnnotationCanvas", target: MaskItem, scene_pos: QPointF) -> None:
    radius = canvas._brush_size / 2.0
    if canvas._current_tool == "brush":
        target.paint_brush(scene_pos, radius)
    elif canvas._current_tool == "eraser":
        target.erase_brush(scene_pos, radius)


def update_rubber_poly(canvas: "AnnotationCanvas") -> None:
    for line in canvas._rubber_lines:
        canvas._scene.removeItem(line)
    canvas._rubber_lines.clear()
    if len(canvas._poly_points) < 2:
        return
    pen = QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine)
    for i in range(len(canvas._poly_points) - 1):
        a, b = canvas._poly_points[i], canvas._poly_points[i + 1]
        li = canvas._scene.addLine(a.x(), a.y(), b.x(), b.y(), pen)
        li.setZValue(20)
        canvas._rubber_lines.append(li)


def finish_polygon(canvas: "AnnotationCanvas") -> None:
    canvas._drawing = False
    for line in canvas._rubber_lines:
        canvas._scene.removeItem(line)
    canvas._rubber_lines.clear()
    if canvas._rubber_poly:
        canvas._scene.removeItem(canvas._rubber_poly)
        canvas._rubber_poly = None
    if len(canvas._poly_points) > 2:
        poly = QPolygonF()
        for p in canvas._poly_points:
            poly.append(QPointF(p.x(), p.y()))
        item = canvas._manager.add_poly(poly, label=canvas._manager.default_label, color=canvas._manager.default_color)
        canvas._scene.addItem(item)
    canvas._poly_points = []


def cancel_polygon(canvas: "AnnotationCanvas") -> None:
    canvas._drawing = False
    canvas._poly_points = []
    for line in canvas._rubber_lines:
        canvas._scene.removeItem(line)
    canvas._rubber_lines.clear()
    if canvas._rubber_poly:
        canvas._scene.removeItem(canvas._rubber_poly)
        canvas._rubber_poly = None


def autoseg_result_received(canvas: "AnnotationCanvas", data: dict) -> None:
    coords = data.get("coordinates", [])
    if not coords or len(coords) < 3:
        autoseg_reset(canvas)
        return

    label = data.get("label", canvas._manager.default_label)
    color = canvas._manager.default_color

    item = canvas._manager.add_mask(
        coords,
        label=label,
        color=color,
    )
    canvas._scene.addItem(item)
    autoseg_reset(canvas)


def autoseg_error_received(canvas: "AnnotationCanvas", message: str) -> None:
    _ = message
    autoseg_reset(canvas)


def autoseg_reset(canvas: "AnnotationCanvas") -> None:
    canvas._autoseg_busy = False
    remove_autoseg_marker(canvas)


def remove_autoseg_marker(canvas: "AnnotationCanvas") -> None:
    if canvas._autoseg_marker is not None:
        if canvas._autoseg_marker.scene() == canvas._scene:
            canvas._scene.removeItem(canvas._autoseg_marker)
        canvas._autoseg_marker = None


