"""Polygon annotation graphics item.

Selectable polygon drawn from vertex list with label badge and semi-transparent fill.
Key: paint (draws polygon + label badge), _apply_style (pen/brush), to_dict (serialize),
color/pen_width/font_size/label_height properties, boundingRect (with label offset).
"""
from __future__ import annotations

import uuid

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QGraphicsPolygonItem, QStyleOptionGraphicsItem, QWidget

from ._common import _HALF_HANDLE, _make_font


class PolygonItem(QGraphicsPolygonItem):
    """Selectable polygon annotation drawn from a small number of vertices."""

    def __init__(
        self,
        poly: QPolygonF,
        annotation_id: str | None = None,
        label: str = "",
        color: str = "#ff3232",
        parent=None,
    ) -> None:
        super().__init__(poly, parent)

        self.annotation_id: str = annotation_id or uuid.uuid4().hex[:8]
        self.label: str = label
        self._color = QColor(color)
        self._pen_width: int = 2
        self._font_size: int = 9
        self._label_height: int = 18

        self.setFlag(QGraphicsPolygonItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(10)
        self._apply_style()

    def _apply_style(self) -> None:
        fill = QColor(self._color)
        fill.setAlpha(50)
        self.setPen(QPen(self._color, self._pen_width))
        self.setBrush(QBrush(fill))

    @property
    def color(self) -> QColor:
        return QColor(self._color)

    @color.setter
    def color(self, value: str | QColor) -> None:
        self._color = QColor(value)
        self._apply_style()

    @property
    def pen_width(self) -> int:
        return self._pen_width

    @pen_width.setter
    def pen_width(self, w: int) -> None:
        self._pen_width = max(1, w)
        self._apply_style()

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, size: int) -> None:
        self._font_size = max(6, size)
        self.update()

    @property
    def label_height(self) -> int:
        return self._label_height

    @label_height.setter
    def label_height(self, h: int) -> None:
        if self._label_height != h:
            self.prepareGeometryChange()
            self._label_height = max(10, h)
            self.update()

    def boundingRect(self) -> QRectF:
        r = self.polygon().boundingRect()
        base = r.adjusted(-_HALF_HANDLE, -_HALF_HANDLE, _HALF_HANDLE, _HALF_HANDLE)
        if self.label:
            base.setTop(base.top() - self._label_height)
        return base

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        super().paint(painter, option, widget)

        if self.label:
            poly_r = self.polygon().boundingRect()
            badge_w = len(self.label) * 8 + 12
            badge = QRectF(poly_r.left(), poly_r.top() - self._label_height, badge_w, self._label_height)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self._color))
            painter.drawRect(badge)

            painter.setFont(_make_font(self._font_size))
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(
                badge,
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                f"  {self.label}",
            )

    def to_dict(self) -> dict:
        poly = self.polygon()
        points = [[round(p.x(), 2), round(p.y(), 2)] for p in poly]
        r = poly.boundingRect()
        return {
            "id": self.annotation_id,
            "type": "poly",
            "label": self.label,
            "color": self._color.name(),
            "points": points,
            "x": round(r.x(), 2),
            "y": round(r.y(), 2),
            "w": round(r.width(), 2),
            "h": round(r.height(), 2),
        }

    def __repr__(self) -> str:
        return f"PolygonItem(id={self.annotation_id}, label={self.label!r})"

