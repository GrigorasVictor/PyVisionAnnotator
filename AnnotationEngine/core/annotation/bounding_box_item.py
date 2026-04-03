"""Bounding box annotation graphics item."""
from __future__ import annotations

import uuid
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from ._common import (
    _HANDLE_CURSORS,
    _HANDLE_SIZE,
    _HALF_HANDLE,
    _MIN_DIMENSION,
    _HandlePosition,
    _make_font,
)


class BoundingBoxItem(QGraphicsRectItem):
    """Selectable, resizable bounding-box."""

    _SEL_COLOR = QColor(50, 255, 50)

    def __init__(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        annotation_id: Optional[str] = None,
        label: str = "",
        color: QColor | str = QColor(255, 50, 50),
        parent=None,
    ) -> None:
        super().__init__(x, y, w, h, parent)

        self.annotation_id: str = annotation_id or uuid.uuid4().hex[:8]
        self.label: str = label
        self._color = QColor(color) if isinstance(color, str) else QColor(color)

        self._pen_width: int = 2
        self._font_size: int = 9
        self._label_height: int = 18

        self._active_handle: _HandlePosition = _HandlePosition.NONE
        self._drag_origin: Optional[QPointF] = None
        self._drag_rect_origin: Optional[QRectF] = None

        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self._rebuild_pens()

    def _rebuild_pens(self) -> None:
        fill = QColor(self._color)
        fill.setAlpha(35)
        self._brush = QBrush(fill)
        self._default_pen = QPen(self._color, self._pen_width)
        self._selected_pen = QPen(self._SEL_COLOR, self._pen_width)
        self.setPen(self._default_pen)
        self.setBrush(self._brush)
        self.update()

    @property
    def color(self) -> QColor:
        return QColor(self._color)

    @color.setter
    def color(self, value: QColor | str) -> None:
        self._color = QColor(value) if isinstance(value, str) else QColor(value)
        self._rebuild_pens()

    @property
    def pen_width(self) -> int:
        return self._pen_width

    @pen_width.setter
    def pen_width(self, w: int) -> None:
        self._pen_width = max(1, w)
        self._rebuild_pens()

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
        base = self.rect().adjusted(-_HALF_HANDLE, -_HALF_HANDLE, _HALF_HANDLE, _HALF_HANDLE)
        if self.label:
            base.setTop(base.top() - self._label_height)
        return base

    def _handle_rects(self) -> dict[_HandlePosition, QRectF]:
        r = self.rect()
        mx = (r.left() + r.right()) / 2.0
        my = (r.top() + r.bottom()) / 2.0
        s = _HALF_HANDLE
        return {
            _HandlePosition.TOP_LEFT: QRectF(r.left() - s, r.top() - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.TOP: QRectF(mx - s, r.top() - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.TOP_RIGHT: QRectF(r.right() - s, r.top() - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.LEFT: QRectF(r.left() - s, my - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.RIGHT: QRectF(r.right() - s, my - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.BOTTOM_LEFT: QRectF(r.left() - s, r.bottom() - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.BOTTOM: QRectF(mx - s, r.bottom() - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.BOTTOM_RIGHT: QRectF(r.right() - s, r.bottom() - s, _HANDLE_SIZE, _HANDLE_SIZE),
        }

    def _handle_at(self, pos: QPointF) -> _HandlePosition:
        for hp, hr in self._handle_rects().items():
            if hr.contains(pos):
                return hp
        return _HandlePosition.NONE

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        pen = self._selected_pen if self.isSelected() else self._default_pen
        painter.setPen(pen)
        painter.setBrush(self._brush)
        painter.drawRect(self.rect())

        if self.label:
            r = self.rect()
            badge_w = len(self.label) * 8 + 12
            badge = QRectF(r.left(), r.top() - self._label_height, badge_w, self._label_height)

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

        if self.isSelected():
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            for hr in self._handle_rects().values():
                painter.drawRect(hr)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        if self.isSelected():
            hp = self._handle_at(event.pos())
            if hp != _HandlePosition.NONE:
                self.setCursor(_HANDLE_CURSORS[hp])
            else:
                self.unsetCursor()
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isSelected():
            hp = self._handle_at(event.pos())
            if hp != _HandlePosition.NONE:
                self._active_handle = hp
                self._drag_origin = event.pos()
                self._drag_rect_origin = QRectF(self.rect())
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_handle != _HandlePosition.NONE and self._drag_rect_origin is not None:
            pos = event.pos()
            r = QRectF(self._drag_rect_origin)
            hp = self._active_handle

            if hp in (_HandlePosition.TOP_LEFT, _HandlePosition.TOP, _HandlePosition.TOP_RIGHT):
                r.setTop(min(pos.y(), r.bottom() - _MIN_DIMENSION))
            if hp in (_HandlePosition.BOTTOM_LEFT, _HandlePosition.BOTTOM, _HandlePosition.BOTTOM_RIGHT):
                r.setBottom(max(pos.y(), r.top() + _MIN_DIMENSION))
            if hp in (_HandlePosition.TOP_LEFT, _HandlePosition.LEFT, _HandlePosition.BOTTOM_LEFT):
                r.setLeft(min(pos.x(), r.right() - _MIN_DIMENSION))
            if hp in (_HandlePosition.TOP_RIGHT, _HandlePosition.RIGHT, _HandlePosition.BOTTOM_RIGHT):
                r.setRight(max(pos.x(), r.left() + _MIN_DIMENSION))

            self.prepareGeometryChange()
            self.setRect(r.normalized())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_handle != _HandlePosition.NONE:
            self._active_handle = _HandlePosition.NONE
            self._drag_origin = None
            self._drag_rect_origin = None
            callback = getattr(self, "_on_local_geometry_changed", None)
            if callable(callback):
                callback()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def to_dict(self) -> dict:
        r = self.rect()
        return {
            "id": self.annotation_id,
            "type": "rect",
            "label": self.label,
            "color": self._color.name(),
            "x": round(r.x(), 2),
            "y": round(r.y(), 2),
            "w": round(r.width(), 2),
            "h": round(r.height(), 2),
        }

    def __repr__(self) -> str:
        d = self.to_dict()
        return f"BoundingBoxItem(id={d['id']}, label={d['label']!r}, x={d['x']}, y={d['y']})"

