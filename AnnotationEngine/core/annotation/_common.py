"""Shared helpers/constants for annotation item graphics classes."""
from __future__ import annotations

from enum import Enum, auto

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

_HANDLE_SIZE: float = 8.0
_HALF_HANDLE: float = _HANDLE_SIZE / 2.0
_MIN_DIMENSION: float = 6.0


class _HandlePosition(Enum):
    NONE = auto()
    TOP_LEFT = auto()
    TOP_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()


_HANDLE_CURSORS: dict[_HandlePosition, Qt.CursorShape] = {
    _HandlePosition.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    _HandlePosition.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    _HandlePosition.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    _HandlePosition.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    _HandlePosition.TOP: Qt.CursorShape.SizeVerCursor,
    _HandlePosition.BOTTOM: Qt.CursorShape.SizeVerCursor,
    _HandlePosition.LEFT: Qt.CursorShape.SizeHorCursor,
    _HandlePosition.RIGHT: Qt.CursorShape.SizeHorCursor,
}


def _make_font(size: int) -> QFont:
    """Create a bold Segoe UI font at the given point size."""
    f = QFont("Segoe UI", size)
    f.setBold(True)
    return f

