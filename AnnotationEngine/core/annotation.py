"""
core/annotation.py — BoundingBoxItem + PolygonItem

All coordinates are in image-pixel / scene space.
"""
from __future__ import annotations

import uuid
from enum import Enum, auto
from typing import Optional

from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QPen, QPainter, QFont, QPolygonF, QPixmap, QPainterPath
from PyQt6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsPolygonItem,
    QGraphicsPixmapItem,
    QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

_HANDLE_SIZE: float = 8.0
_HALF_HANDLE: float = _HANDLE_SIZE / 2.0
_MIN_DIMENSION: float = 6.0


class _HandlePosition(Enum):
    NONE         = auto()
    TOP_LEFT     = auto()
    TOP_RIGHT    = auto()
    BOTTOM_LEFT  = auto()
    BOTTOM_RIGHT = auto()
    TOP          = auto()
    BOTTOM       = auto()
    LEFT         = auto()
    RIGHT        = auto()


_HANDLE_CURSORS: dict[_HandlePosition, Qt.CursorShape] = {
    _HandlePosition.TOP_LEFT:     Qt.CursorShape.SizeFDiagCursor,
    _HandlePosition.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    _HandlePosition.TOP_RIGHT:    Qt.CursorShape.SizeBDiagCursor,
    _HandlePosition.BOTTOM_LEFT:  Qt.CursorShape.SizeBDiagCursor,
    _HandlePosition.TOP:          Qt.CursorShape.SizeVerCursor,
    _HandlePosition.BOTTOM:       Qt.CursorShape.SizeVerCursor,
    _HandlePosition.LEFT:         Qt.CursorShape.SizeHorCursor,
    _HandlePosition.RIGHT:        Qt.CursorShape.SizeHorCursor,
}


def _make_font(size: int) -> QFont:
    """Create a bold Segoe UI font at the given point size."""
    f = QFont("Segoe UI", size)
    f.setBold(True)
    return f


# ─────────────────────────────────────────────────────────────────── #
#  PolygonItem  (QGraphicsPolygonItem — for manual polygon drawing)
# ─────────────────────────────────────────────────────────────────── #
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
            poly_r  = self.polygon().boundingRect()
            badge_w = len(self.label) * 8 + 12
            badge   = QRectF(poly_r.left(), poly_r.top() - self._label_height, badge_w, self._label_height)

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
        poly   = self.polygon()
        points = [[round(p.x(), 2), round(p.y(), 2)] for p in poly]
        r      = poly.boundingRect()
        return {
            "id": self.annotation_id, "type": "poly", "label": self.label,
            "color": self._color.name(), "points": points,
            "x": round(r.x(), 2), "y": round(r.y(), 2),
            "w": round(r.width(), 2), "h": round(r.height(), 2),
        }

    def __repr__(self) -> str:
        return f"PolygonItem(id={self.annotation_id}, label={self.label!r})"


# ─────────────────────────────────────────────────────────────────── #
#  MaskItem  (pixel-backed — O(1) render for AutoSeg masks)
# ─────────────────────────────────────────────────────────────────── #
class MaskItem(QGraphicsPixmapItem):
    """Selectable mask annotation rendered as coloured pixels on a QPixmap.

    Accepts raw ``[[x, y], …]`` coordinates (thousands of mask pixels),
    paints each one onto a compact QImage and displays the result as a
    flat texture. Rendering cost is O(1) regardless of point count.
    """

    def __init__(
        self,
        points: list[list[float]],
        annotation_id: str | None = None,
        label: str = "",
        color: str = "#ff3232",
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.annotation_id: str = annotation_id or uuid.uuid4().hex[:8]
        self.label: str = label
        self._color = QColor(color)
        self._font_size: int = 9
        self._label_height: int = 18
        self._pen_width: int = 2  # kept for settings compat

        # Store raw points for export and hit-testing
        self._points: list[list[float]] = [
            [float(p[0]), float(p[1])] for p in points
        ]

        self._update_bbox()

        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(10)
        self._rebuild_pixmap()

    # ---- internal bbox cache ------------------------------------------ #
    def _update_bbox(self) -> None:
        if not self._points:
            self._min_x = self._min_y = 0.0
            self._max_x = self._max_y = 0.0
            return
        xs = [p[0] for p in self._points]
        ys = [p[1] for p in self._points]
        self._min_x, self._max_x = min(xs), max(xs)
        self._min_y, self._max_y = min(ys), max(ys)

    # ---- rasterisation ------------------------------------------------ #
    def _rebuild_pixmap(self) -> None:
        """Rasterise points directly as individual pixels onto a QImage."""
        from utils.geometry import rasterize_points

        pm, ox, oy = rasterize_points(self._points, self._color, fill_alpha=80)
        self.setPixmap(pm)
        self.setOffset(ox, oy)

    # ---- shape (accurate click hit-test) ------------------------------ #
    def shape(self) -> QPainterPath:
        """Rectangular hit-test area covering all mask pixels."""
        path = QPainterPath()
        off = self.offset()
        path.addRect(QRectF(
            self._min_x - off.x(),
            self._min_y - off.y(),
            self._max_x - self._min_x + 1,
            self._max_y - self._min_y + 1,
        ))
        return path

    # ---- properties --------------------------------------------------- #
    @property
    def color(self) -> QColor:
        return QColor(self._color)

    @color.setter
    def color(self, value: str | QColor) -> None:
        self._color = QColor(value)
        self._rebuild_pixmap()

    @property
    def pen_width(self) -> int:
        return self._pen_width

    @pen_width.setter
    def pen_width(self, w: int) -> None:
        self._pen_width = max(1, w)

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

    # ---- bounding rect (includes label badge) ------------------------- #
    def boundingRect(self) -> QRectF:
        base = super().boundingRect()
        if self.label:
            # Extend upward from the top of the pixmap content to fit the badge
            base.setTop(base.top() - self._label_height)
        return base

    # ---- paint (only draws the label badge; pixmap renders itself) ----- #
    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        super().paint(painter, option, widget)

        if self.label:
            # The pixmap is drawn at self.offset() in item-local coordinates.
            # Badge goes just above the pixmap's top-left corner.
            off = self.offset()
            badge_w = len(self.label) * 8 + 12
            badge = QRectF(off.x(), off.y() - self._label_height, badge_w, self._label_height)

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

    # ---- serialisation ------------------------------------------------ #
    def to_dict(self) -> dict:
        points = [[round(p[0], 2), round(p[1], 2)] for p in self._points]
        return {
            "id": self.annotation_id, "type": "mask", "label": self.label,
            "color": self._color.name(), "points": points,
            "x": round(self._min_x, 2), "y": round(self._min_y, 2),
            "w": round(self._max_x - self._min_x, 2),
            "h": round(self._max_y - self._min_y, 2),
        }

    def __repr__(self) -> str:
        return f"MaskItem(id={self.annotation_id}, label={self.label!r}, pts={len(self._points)})"


# ─────────────────────────────────────────────────────────────────── #
#  BoundingBoxItem
# ─────────────────────────────────────────────────────────────────── #
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

        self._active_handle:    _HandlePosition  = _HandlePosition.NONE
        self._drag_origin:      Optional[QPointF] = None
        self._drag_rect_origin: Optional[QRectF]  = None

        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self._rebuild_pens()

    def _rebuild_pens(self) -> None:
        fill = QColor(self._color)
        fill.setAlpha(35)
        self._brush        = QBrush(fill)
        self._default_pen  = QPen(self._color,     self._pen_width)
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
        base = self.rect().adjusted(-_HALF_HANDLE, -_HALF_HANDLE,
                                     _HALF_HANDLE,  _HALF_HANDLE)
        if self.label:
            base.setTop(base.top() - self._label_height)
        return base

    def _handle_rects(self) -> dict[_HandlePosition, QRectF]:
        r  = self.rect()
        mx = (r.left() + r.right())  / 2.0
        my = (r.top()  + r.bottom()) / 2.0
        s  = _HALF_HANDLE
        return {
            _HandlePosition.TOP_LEFT:     QRectF(r.left()  - s, r.top()    - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.TOP:          QRectF(mx        - s, r.top()    - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.TOP_RIGHT:    QRectF(r.right() - s, r.top()    - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.LEFT:         QRectF(r.left()  - s, my         - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.RIGHT:        QRectF(r.right() - s, my         - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.BOTTOM_LEFT:  QRectF(r.left()  - s, r.bottom() - s, _HANDLE_SIZE, _HANDLE_SIZE),
            _HandlePosition.BOTTOM:       QRectF(mx        - s, r.bottom() - s, _HANDLE_SIZE, _HANDLE_SIZE),
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
        # Body
        pen = self._selected_pen if self.isSelected() else self._default_pen
        painter.setPen(pen)
        painter.setBrush(self._brush)
        painter.drawRect(self.rect())

        # Label badge (fixed height — no QFontMetrics in paint)
        if self.label:
            r       = self.rect()
            badge_w = len(self.label) * 8 + 12
            badge   = QRectF(r.left(), r.top() - self._label_height, badge_w, self._label_height)

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

        # Resize handles
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
                self._active_handle    = hp
                self._drag_origin      = event.pos()
                self._drag_rect_origin = QRectF(self.rect())
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_handle != _HandlePosition.NONE and self._drag_rect_origin is not None:
            pos = event.pos()
            r   = QRectF(self._drag_rect_origin)
            hp  = self._active_handle

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
            self._active_handle    = _HandlePosition.NONE
            self._drag_origin      = None
            self._drag_rect_origin = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def to_dict(self) -> dict:
        r = self.rect()
        return {
            "id": self.annotation_id, "type": "rect", "label": self.label,
            "color": self._color.name(),
            "x": round(r.x(), 2), "y": round(r.y(), 2),
            "w": round(r.width(), 2), "h": round(r.height(), 2),
        }

    def __repr__(self) -> str:
        d = self.to_dict()
        return f"BoundingBoxItem(id={d['id']}, label={d['label']!r}, x={d['x']}, y={d['y']})"
