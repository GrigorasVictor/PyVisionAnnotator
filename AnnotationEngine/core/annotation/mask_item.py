"""Mask annotation graphics item."""
from __future__ import annotations

import uuid
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsPixmapItem,
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
)


class MaskItem(QGraphicsPixmapItem):
    """Selectable mask annotation rendered as coloured pixels on a QPixmap."""

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
        self._pen_width: int = 2
        self._fill_alpha: int = 80
        self._active_handle: _HandlePosition = _HandlePosition.NONE
        self._drag_rect_origin: Optional[QRectF] = None
        self._bbox_override: Optional[QRectF] = None

        self._points: list[list[float]] = [[float(p[0]), float(p[1])] for p in points]

        self._update_bbox()

        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self._rebuild_pixmap()

    def _update_bbox(self) -> None:
        if not self._points:
            self._min_x = self._min_y = 0.0
            self._max_x = self._max_y = 0.0
            return
        xs = [p[0] for p in self._points]
        ys = [p[1] for p in self._points]
        self._min_x, self._max_x = min(xs), max(xs)
        self._min_y, self._max_y = min(ys), max(ys)

    def _rebuild_pixmap(self) -> None:
        from utils.geometry import rasterize_points

        pm, ox, oy = rasterize_points(self._points, self._color, fill_alpha=self._fill_alpha)

        if pm.isNull():
            self._img = QImage(1, 1, QImage.Format.Format_ARGB32)
            self._img.fill(Qt.GlobalColor.transparent)
            ox, oy = 0.0, 0.0
            pm = QPixmap.fromImage(self._img)

        self._img: QImage = pm.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        self._img_offset = QPointF(ox, oy)
        self.setPixmap(pm)
        self.setOffset(ox, oy)

    def _apply_fill_alpha_to_image(self) -> None:
        self._ensure_image()
        w, h = self._img.width(), self._img.height()
        for y in range(h):
            for x in range(w):
                px = self._img.pixelColor(x, y)
                if px.alpha() == 0:
                    continue
                px.setAlpha(self._fill_alpha)
                self._img.setPixelColor(x, y, px)
        self._flush_image()

    def _ensure_image(self) -> None:
        if not hasattr(self, "_img") or self._img is None or self._img.isNull():
            self._rebuild_pixmap()

    def _expand_image_to_cover(self, scene_rect: QRectF) -> None:
        self._ensure_image()
        ox, oy = self._img_offset.x(), self._img_offset.y()
        cur = QRectF(ox, oy, self._img.width(), self._img.height())

        if cur.contains(scene_rect):
            return

        united = cur.united(scene_rect)
        if united == cur:
            return

        nx, ny = int(united.x()), int(united.y())
        nw, nh = int(united.width()) + 1, int(united.height()) + 1
        new_img = QImage(nw, nh, QImage.Format.Format_ARGB32)
        new_img.fill(Qt.GlobalColor.transparent)
        p = QPainter(new_img)
        p.drawImage(int(ox - nx), int(oy - ny), self._img)
        p.end()
        self._img = new_img
        self._img_offset = QPointF(nx, ny)
        self.setOffset(nx, ny)

    def _flush_image(self) -> None:
        self.prepareGeometryChange()
        self.setPixmap(QPixmap.fromImage(self._img))
        ox, oy = self._img_offset.x(), self._img_offset.y()
        self._min_x = ox
        self._min_y = oy
        self._max_x = ox + self._img.width()
        self._max_y = oy + self._img.height()

    def set_bbox_rect(self, x: float, y: float, w: float, h: float) -> None:
        w = max(_MIN_DIMENSION, float(w))
        h = max(_MIN_DIMENSION, float(h))
        self.prepareGeometryChange()
        self._bbox_override = QRectF(float(x), float(y), w, h)
        self.update()

    def _effective_bbox_scene(self) -> QRectF:
        if self._bbox_override is not None:
            return QRectF(self._bbox_override)
        w = max(1.0, self._max_x - self._min_x)
        h = max(1.0, self._max_y - self._min_y)
        return QRectF(self._min_x, self._min_y, w, h)

    def _effective_bbox_local(self) -> QRectF:
        off = self.offset()
        r = self._effective_bbox_scene()
        return QRectF(r.x() - off.x(), r.y() - off.y(), r.width(), r.height())

    def _handle_rects(self) -> dict[_HandlePosition, QRectF]:
        r = self._effective_bbox_local()
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

    def paint_brush(self, scene_pos: QPointF, radius: float) -> None:
        brush_rect = QRectF(
            scene_pos.x() - radius,
            scene_pos.y() - radius,
            radius * 2 + 1,
            radius * 2 + 1,
        )

        self._expand_image_to_cover(brush_rect)

        ox, oy = self._img_offset.x(), self._img_offset.y()

        p = QPainter(self._img)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._color)
        c.setAlpha(self._fill_alpha)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(c))
        p.drawEllipse(QPointF(scene_pos.x() - ox, scene_pos.y() - oy), radius, radius)
        p.end()
        self._flush_image()

    def erase_brush(self, scene_pos: QPointF, radius: float) -> None:
        self._ensure_image()
        ox, oy = self._img_offset.x(), self._img_offset.y()
        cur = QRectF(ox, oy, self._img.width(), self._img.height())
        brush_rect = QRectF(
            scene_pos.x() - radius,
            scene_pos.y() - radius,
            radius * 2 + 1,
            radius * 2 + 1,
        )
        if not cur.intersects(brush_rect):
            return

        p = QPainter(self._img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(Qt.GlobalColor.transparent))
        p.drawEllipse(QPointF(scene_pos.x() - ox, scene_pos.y() - oy), radius, radius)
        p.end()
        self._flush_image()

    def _current_points(self) -> list[list[float]]:
        if hasattr(self, "_img") and self._img is not None and not self._img.isNull():
            from utils.geometry import pixels_to_points

            ox, oy = self._img_offset.x(), self._img_offset.y()
            return pixels_to_points(self._img, ox, oy)
        return [[p[0], p[1]] for p in self._points]

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self._effective_bbox_local())
        return path

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

    @property
    def fill_alpha(self) -> int:
        return self._fill_alpha

    @fill_alpha.setter
    def fill_alpha(self, alpha: int) -> None:
        alpha_i = max(0, min(255, int(alpha)))
        if self._fill_alpha == alpha_i:
            return
        self._fill_alpha = alpha_i
        if hasattr(self, "_img") and self._img is not None and not self._img.isNull():
            self._apply_fill_alpha_to_image()
        else:
            self._rebuild_pixmap()

    def boundingRect(self) -> QRectF:
        base = super().boundingRect().united(self._effective_bbox_local())
        base = base.adjusted(-_HALF_HANDLE, -_HALF_HANDLE, _HALF_HANDLE, _HALF_HANDLE)
        return base

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        super().paint(painter, option, widget)

        bbox = self._effective_bbox_local()

        if self.isSelected():
            painter.setPen(QPen(QColor(50, 255, 50), self._pen_width))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(bbox)

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
                self._drag_rect_origin = self._effective_bbox_local()
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

            r = r.normalized()
            off = self.offset()
            self.prepareGeometryChange()
            self._bbox_override = QRectF(r.x() + off.x(), r.y() + off.y(), r.width(), r.height())
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_handle != _HandlePosition.NONE:
            self._active_handle = _HandlePosition.NONE
            self._drag_rect_origin = None
            callback = getattr(self, "_on_local_geometry_changed", None)
            if callable(callback):
                callback()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def to_dict(self) -> dict:
        pts = self._current_points() if (hasattr(self, "_img") and self._img is not None) else self._points
        points = [[round(p[0], 2), round(p[1], 2)] for p in pts]
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            self._min_x, self._max_x = min(xs), max(xs)
            self._min_y, self._max_y = min(ys), max(ys)
        bbox = self._effective_bbox_scene()
        return {
            "id": self.annotation_id,
            "type": "mask",
            "label": self.label,
            "color": self._color.name(),
            "points": points,
            "x": round(bbox.x(), 2),
            "y": round(bbox.y(), 2),
            "w": round(bbox.width(), 2),
            "h": round(bbox.height(), 2),
        }

    def __repr__(self) -> str:
        return f"MaskItem(id={self.annotation_id}, label={self.label!r}, pts={len(self._points)})"

