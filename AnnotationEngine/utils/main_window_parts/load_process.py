from __future__ import annotations

import os
from pathlib import Path


def on_folder_opened(window, folder: str) -> None:
    window._toolbar.reset_export_root()
    window._status.showMessage(f"Loaded {window._left.file_list.count()} image(s) from {folder}")


def on_image_load_requested(window, path: str) -> None:
    """Left panel wants to load a new image."""
    window._ignore_changes = True
    window._canvas.load_image(path)
    window._ignore_changes = False
    window._unsaved_changes = False


def on_save_before_switch(window) -> None:
    """Left panel deferred a switch - we must save first."""
    if window._toolbar.save_json():
        window._left.confirm_switch()
    else:
        window._left.cancel_switch()


def on_image_loaded(window, path: str, w: int, h: int) -> None:
    window._status.showMessage(f"{Path(path).name}  ({w} x {h} px)")


def on_visual_settings_applied(window, pen_width: int, font_size: int, label_height: int) -> None:
    """Apply visual style settings to all existing and future annotations."""
    window._manager.update_global_settings(pen_width, font_size, label_height)

    for item in window._manager.get_all():
        item.update()
    window._canvas.viewport().update()

    window._status.showMessage(
        f"Visual style updated: width={pen_width}, font={font_size}, label={label_height}"
    )


def load_process(window, image_path: str, annotations: list) -> None:
    """Called by toolbar after a successful JSON import."""
    current_norm = os.path.normcase(os.path.abspath(window._manager.image_path or ""))
    new_norm = os.path.normcase(os.path.abspath(image_path or ""))

    if image_path and new_norm != current_norm:
        window._ignore_changes = True
        window._canvas.load_image(image_path)
        window._ignore_changes = False
    else:
        # Same image - clear existing annotations first (no duplicates)
        window._ignore_changes = True
        for old in window._manager.clear():
            window._canvas.scene().removeItem(old)
        window._ignore_changes = False

    window._ignore_changes = True
    items = window._manager.load_annotations(annotations)
    for item in items:
        window._canvas.add_annotation_item(item)
    window._ignore_changes = False

    if image_path:
        window._left.select_item_for_path(image_path)

    window._unsaved_changes = False
    window._status.showMessage(f"Loaded {len(items)} annotation(s).")

