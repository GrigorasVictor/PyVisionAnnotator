"""Rendering helpers for AnnotationCanvas foreground overlays."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsView


def draw_foreground(canvas, painter: QPainter, rect: QRectF) -> None:
    """Draw brush cursor and crosshair overlays in viewport coordinates."""
    QGraphicsView.drawForeground(canvas, painter, rect)

    if canvas._mouse_pos_viewport is None:
        return

    painter.save()
    painter.resetTransform()

    vp = canvas.viewport()
    mx = canvas._mouse_pos_viewport.x()
    my = canvas._mouse_pos_viewport.y()

    # Draw brush / eraser radius under cursor.
    if canvas._current_tool in ("brush", "eraser") and not canvas._space_held:
        radius_scene = canvas._brush_size / 2.0
        scale = canvas.transform().m11()  # pixels per scene unit
        radius_vp = radius_scene * scale

        pen_col = QColor(255, 80, 80) if canvas._current_tool == "eraser" else QColor(255, 255, 255)
        painter.setPen(QPen(pen_col, 1, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(mx, my), radius_vp, radius_vp)

        painter.setPen(QPen(pen_col, 2))
        painter.drawPoint(int(mx), int(my))

    if canvas._crosshair_enabled:
        painter.setPen(QPen(QColor(0, 255, 128, 180), 1, Qt.PenStyle.SolidLine))
        painter.drawLine(0, int(my), vp.width(), int(my))
        painter.drawLine(int(mx), 0, int(mx), vp.height())

    painter.restore()

