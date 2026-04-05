"""Tool-state helpers for AnnotationCanvas.

Clears in-progress drawing state (paint target, poly points, rubber bands, markers) when switching tools.
Key: set_tool (reset drawing flags + remove temp overlays).
"""
from __future__ import annotations


def set_tool(canvas, tool_mode: str) -> None:
    """Switch active tool and clear any in-progress temporary draw state."""
    canvas._current_tool = tool_mode
    canvas._painting = False
    canvas._paint_target = None
    canvas._drawing = False
    canvas._poly_points = []

    if canvas._rubber_band:
        if canvas._rubber_band.scene() == canvas._scene:
            canvas._scene.removeItem(canvas._rubber_band)
        canvas._rubber_band = None

    if hasattr(canvas, "_rubber_lines"):
        for line in canvas._rubber_lines:
            if line.scene() == canvas._scene:
                canvas._scene.removeItem(line)
        canvas._rubber_lines.clear()

    if canvas._rubber_poly:
        if canvas._rubber_poly.scene() == canvas._scene:
            canvas._scene.removeItem(canvas._rubber_poly)
        canvas._rubber_poly = None

