"""
ui/canvas_events.py

Qt event handlers extracted from AnnotationCanvas to keep ui/canvas.py compact.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QMouseEvent, QWheelEvent, QKeyEvent, QPen, QColor, QBrush
from PyQt6.QtWidgets import QGraphicsView

from core.annotation import BoundingBoxItem, PolygonItem, MaskItem

if TYPE_CHECKING:
    from ui.main_window.canvas import AnnotationCanvas


def wheel_event(canvas: "AnnotationCanvas", event: QWheelEvent) -> None:
    angle = event.angleDelta().y()
    if angle > 0:
        factor = canvas._ZOOM_FACTOR
    elif angle < 0:
        factor = 1.0 / canvas._ZOOM_FACTOR
    else:
        return
    current_scale = canvas.transform().m11()
    new_scale = current_scale * factor
    if new_scale < canvas._ZOOM_MIN or new_scale > canvas._ZOOM_MAX:
        return
    canvas.scale(factor, factor)


def key_press_event(canvas: "AnnotationCanvas", event: QKeyEvent) -> None:
    if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
        canvas._space_held = True
        canvas.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
    elif event.key() == Qt.Key.Key_Delete:
        canvas.delete_selected()
    elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
        if canvas._current_tool == "polygon" and canvas._drawing:
            if len(canvas._poly_points) > 2:
                canvas._finish_polygon()
            else:
                canvas._cancel_polygon()
            event.accept()
            return
    elif event.key() == Qt.Key.Key_Escape:
        if canvas._drawing:
            canvas._cancel_polygon()
            canvas._drawing = False
            if canvas._rubber_band:
                canvas._scene.removeItem(canvas._rubber_band)
                canvas._rubber_band = None
            event.accept()
            return
    else:
        QGraphicsView.keyPressEvent(canvas, event)


def key_release_event(canvas: "AnnotationCanvas", event: QKeyEvent) -> None:
    if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
        canvas._space_held = False
        canvas.viewport().setCursor(Qt.CursorShape.ArrowCursor)
    else:
        QGraphicsView.keyReleaseEvent(canvas, event)


def mouse_press_event(canvas: "AnnotationCanvas", event: QMouseEvent) -> None:
    btn = event.button()

    if btn == Qt.MouseButton.MiddleButton or (
        btn == Qt.MouseButton.LeftButton and canvas._space_held
    ):
        canvas._panning = True
        canvas._pan_start = event.position()
        canvas.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()
        return

    if btn == Qt.MouseButton.LeftButton and not canvas._space_held:
        scene_pos: QPointF = canvas.mapToScene(event.pos())

        if canvas._current_tool in ("brush", "eraser"):
            target = canvas._find_selected_mask()
            if target is None:
                item_under = canvas.itemAt(event.pos())
                if isinstance(item_under, MaskItem):
                    canvas._scene.clearSelection()
                    item_under.setSelected(True)
                    target = item_under
                elif canvas._current_tool == "brush" and canvas._pixmap_item:
                    target = canvas._manager.add_mask(
                        [],
                        label=canvas._manager.default_label,
                        color=canvas._manager.default_color,
                    )
                    canvas._scene.addItem(target)
                    canvas._scene.clearSelection()
                    target.setSelected(True)

            if target is not None:
                canvas._painting = True
                canvas._paint_target = target
                canvas._apply_paint(target, scene_pos)
            event.accept()
            return

        if canvas._current_tool == "automask":
            if canvas._autoseg_busy:
                event.accept()
                return
            if canvas._pixmap_item is None:
                event.accept()
                return
            canvas._remove_autoseg_marker()
            marker_size = 10.0
            pen = QPen(QColor(0, 255, 0), 2)
            brush = QBrush(QColor(0, 255, 0, 120))
            canvas._autoseg_marker = canvas._scene.addEllipse(
                scene_pos.x() - marker_size / 2,
                scene_pos.y() - marker_size / 2,
                marker_size,
                marker_size,
                pen,
                brush,
            )
            canvas._autoseg_marker.setZValue(25)
            canvas._autoseg_busy = True
            canvas.autoseg_requested.emit(scene_pos)
            event.accept()
            return

        if canvas._current_tool == "polygon":
            if canvas._drawing:
                canvas._poly_points.append(scene_pos)
                canvas._update_rubber_poly()
                event.accept()
                return
            item_under = canvas.itemAt(event.pos())
            if isinstance(item_under, (BoundingBoxItem, PolygonItem, MaskItem)):
                QGraphicsView.mousePressEvent(canvas, event)
                return
            canvas._drawing = True
            canvas._poly_points = [scene_pos]
            canvas._update_rubber_poly()
            event.accept()
            return

        if canvas._current_tool == "rectangle":
            item_under = canvas.itemAt(event.pos())
            if isinstance(item_under, (BoundingBoxItem, PolygonItem, MaskItem)):
                QGraphicsView.mousePressEvent(canvas, event)
                return
            canvas._drawing = True
            canvas._draw_origin = scene_pos
            pen = QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine)
            canvas._rubber_band = canvas._scene.addRect(QRectF(scene_pos, scene_pos), pen)
            canvas._rubber_band.setZValue(20)
            event.accept()
            return

    if btn == Qt.MouseButton.RightButton and canvas._current_tool == "polygon" and canvas._drawing:
        if len(canvas._poly_points) > 2:
            canvas._finish_polygon()
        else:
            canvas._cancel_polygon()
        event.accept()
        return

    QGraphicsView.mousePressEvent(canvas, event)


def mouse_move_event(canvas: "AnnotationCanvas", event: QMouseEvent) -> None:
    canvas._mouse_pos_viewport = event.position()
    canvas.viewport().update()

    scene_pos = canvas.mapToScene(event.pos())

    if canvas._painting and canvas._paint_target is not None:
        canvas._apply_paint(canvas._paint_target, scene_pos)
        event.accept()
        return

    if canvas._panning and canvas._pan_start is not None:
        delta = event.position() - canvas._pan_start
        canvas._pan_start = event.position()
        canvas.horizontalScrollBar().setValue(int(canvas.horizontalScrollBar().value() - delta.x()))
        canvas.verticalScrollBar().setValue(int(canvas.verticalScrollBar().value() - delta.y()))
        event.accept()
        return

    if (
        canvas._current_tool == "rectangle"
        and canvas._drawing
        and canvas._draw_origin is not None
        and canvas._rubber_band is not None
    ):
        rect = QRectF(canvas._draw_origin, scene_pos).normalized()
        canvas._rubber_band.setRect(rect)
        event.accept()
        return

    if canvas._current_tool == "polygon" and canvas._drawing and canvas._poly_points:
        for line in canvas._rubber_lines:
            canvas._scene.removeItem(line)
        canvas._rubber_lines.clear()
        pen = QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine)
        for i in range(len(canvas._poly_points) - 1):
            a, b = canvas._poly_points[i], canvas._poly_points[i + 1]
            li = canvas._scene.addLine(a.x(), a.y(), b.x(), b.y(), pen)
            li.setZValue(20)
            canvas._rubber_lines.append(li)
        last = canvas._poly_points[-1]
        li = canvas._scene.addLine(last.x(), last.y(), scene_pos.x(), scene_pos.y(), pen)
        li.setZValue(20)
        canvas._rubber_lines.append(li)
        event.accept()
        return

    QGraphicsView.mouseMoveEvent(canvas, event)


def mouse_release_event(canvas: "AnnotationCanvas", event: QMouseEvent) -> None:
    btn = event.button()

    if canvas._painting and btn == Qt.MouseButton.LeftButton:
        target = canvas._paint_target
        canvas._painting = False
        canvas._paint_target = None
        if target is not None:
            canvas._manager.update_item(target.annotation_id)
        event.accept()
        return

    if canvas._panning and (btn == Qt.MouseButton.MiddleButton or btn == Qt.MouseButton.LeftButton):
        canvas._panning = False
        canvas._pan_start = None
        cursor = Qt.CursorShape.OpenHandCursor if canvas._space_held else Qt.CursorShape.ArrowCursor
        canvas.viewport().setCursor(cursor)
        event.accept()
        return

    if canvas._current_tool == "rectangle" and canvas._drawing and btn == Qt.MouseButton.LeftButton:
        canvas._drawing = False
        if canvas._rubber_band is not None:
            rect: QRectF = canvas._rubber_band.rect()
            canvas._scene.removeItem(canvas._rubber_band)
            canvas._rubber_band = None
            if rect.width() > 4 and rect.height() > 4:
                rect = canvas._clamp_rect_to_image(rect)
                item = canvas._manager.add_rect(
                    rect.x(),
                    rect.y(),
                    rect.width(),
                    rect.height(),
                    label=canvas._manager.default_label,
                    color=canvas._manager.default_color,
                )
                canvas._scene.addItem(item)
        canvas._draw_origin = None
        event.accept()
        return

    QGraphicsView.mouseReleaseEvent(canvas, event)


def mouse_double_click_event(canvas: "AnnotationCanvas", event: QMouseEvent) -> None:
    if canvas._current_tool == "polygon" and canvas._drawing:
        if len(canvas._poly_points) > 2:
            canvas._finish_polygon()
        else:
            canvas._cancel_polygon()
        event.accept()
        return
    QGraphicsView.mouseDoubleClickEvent(canvas, event)


def leave_event(canvas: "AnnotationCanvas", event) -> None:
    canvas._mouse_pos_viewport = None
    canvas.viewport().update()
    QGraphicsView.leaveEvent(canvas, event)

