"""
utils/geometry.py — Geometry helpers

Converts raw mask-pixel coordinate lists returned by segmentation models
(e.g. mask2former / SAM) into simplified QPolygonF outlines suitable for
PolygonItem annotations.

Also provides a rasterisation helper that burns a QPolygonF onto a compact
QImage / QPixmap so that even masks with tens of thousands of vertices can
be displayed at O(1) paint cost.
"""
from __future__ import annotations

import math
from typing import List, Tuple

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPolygonF, QImage, QPixmap, QColor


# ─────────────────────────────────────────────────────────────────── #
#  Public API
# ─────────────────────────────────────────────────────────────────── #

def mask_coords_to_polygon(
    coords: List[List[int | float]],
    epsilon: float = 2.0,
    convex: bool = False,
) -> QPolygonF:
    """Convert a list of ``[x, y]`` pixel coordinates into a QPolygonF.

    Uses Douglas-Peucker simplification to reduce point count and prevent UI lag.
    """
    if len(coords) < 3:
        poly = QPolygonF()
        for c in coords:
            poly.append(QPointF(float(c[0]), float(c[1])))
        return poly

    # Convert to list of tuples for processing
    points = [(float(c[0]), float(c[1])) for c in coords]

    # Optional: Simplification (crucial for performance with mask pixels)
    if epsilon > 0:
        points = _douglas_peucker(points, epsilon)

    poly = QPolygonF()
    for x, y in points:
        poly.append(QPointF(x, y))
    return poly


# ─────────────────────────────────────────────────────────────────── #
#  Simplification Algorithms
# ─────────────────────────────────────────────────────────────────── #

def _perpendicular_distance(point, line_start, line_end):
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    mag_sq = dx * dx + dy * dy
    if mag_sq == 0.0:
        return math.hypot(point[0] - line_start[0], point[1] - line_start[1])

    u = ((point[0] - line_start[0]) * dx + (point[1] - line_start[1]) * dy) / mag_sq
    u = max(0.0, min(1.0, u))

    proj_x = line_start[0] + u * dx
    proj_y = line_start[1] + u * dy
    return math.hypot(point[0] - proj_x, point[1] - proj_y)

def _douglas_peucker(points: List[Tuple[float, float]], epsilon: float) -> List[Tuple[float, float]]:
    """Iterative Douglas-Peucker simplification to avoid recursion limits."""
    if len(points) < 3:
        return points

    # Find the point with the maximum distance
    dmax = 0.0
    index = 0
    end = len(points) - 1

    stack = [(0, end)]
    keep_indices = {0, end}

    while stack:
        start, end = stack.pop()
        dmax = 0.0
        index = start

        for i in range(start + 1, end):
            d = _perpendicular_distance(points[i], points[start], points[end])
            if d > dmax:
                dmax = d
                index = i

        if dmax > epsilon:
            keep_indices.add(index)
            stack.append((start, index))
            stack.append((index, end))

    sorted_indices = sorted(list(keep_indices))
    return [points[i] for i in sorted_indices]


# ─────────────────────────────────────────────────────────────────── #
#  Rasterisation  (works directly on raw [[x,y], …] coordinate lists)
# ─────────────────────────────────────────────────────────────────── #

def rasterize_points(
    points: List[List[float | int]],
    color: QColor,
    fill_alpha: int = 80,
) -> tuple[QPixmap, float, float]:
    """Paint every ``[x, y]`` coordinate as a single pixel onto a compact
    ARGB32 QImage and return it as a QPixmap.

    This is *much* cheaper than building a QPolygonF with thousands of
    vertices — we simply set individual pixel colours, which is O(n) in
    Python but O(1) at render time because the result is a flat texture.

    The image is sized to the bounding box of the points (+ 1 px padding),
    keeping memory proportional to the mask footprint.

    Returns:
        ``(pixmap, offset_x, offset_y)`` — the pixmap and its scene-space
        top-left so the caller can ``item.setOffset(offset_x, offset_y)``.
    """
    if not points:
        return QPixmap(), 0.0, 0.0

    # Compute bounding box
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for p in points:
        px, py = float(p[0]), float(p[1])
        if px < min_x: min_x = px
        if px > max_x: max_x = px
        if py < min_y: min_y = py
        if py > max_y: max_y = py

    pad = 1
    ox = min_x - pad
    oy = min_y - pad
    w = int(max_x - min_x + 2 * pad + 1)
    h = int(max_y - min_y + 2 * pad + 1)

    if w < 1 or h < 1:
        return QPixmap(), ox, oy

    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    # Pre-compute the fill colour (ARGB packed int)
    fill = QColor(color)
    fill.setAlpha(fill_alpha)
    rgba = fill.rgba()          # 0xAARRGGBB packed uint

    for p in points:
        ix = int(float(p[0]) - ox)
        iy = int(float(p[1]) - oy)
        if 0 <= ix < w and 0 <= iy < h:
            img.setPixel(ix, iy, rgba)

    return QPixmap.fromImage(img), ox, oy

