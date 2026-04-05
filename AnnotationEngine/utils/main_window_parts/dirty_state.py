"""Track annotation unsaved changes state and close-event guard.

Marks dirty on annotation changes, clears on save, prompts user Save/Discard/Cancel on app close.
Key: on_data_changed (set flag), clear_unsaved (reset), handle_close_event (prompt if dirty).
"""

from __future__ import annotations

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMessageBox


def on_data_changed(window, *_args) -> None:
    if not window._ignore_changes:
        window._unsaved_changes = True


def clear_unsaved(window) -> None:
    window._unsaved_changes = False


def handle_close_event(window, event: QCloseEvent) -> None:
    """Guard app close when there are unsaved annotation changes."""
    if not window._unsaved_changes:
        event.accept()
        return

    reply = QMessageBox.question(
        window,
        "Unsaved Changes",
        "You have unsaved annotations. Save before exiting?",
        QMessageBox.StandardButton.Save
        | QMessageBox.StandardButton.Discard
        | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Save,
    )

    if reply == QMessageBox.StandardButton.Cancel:
        event.ignore()
        return

    if reply == QMessageBox.StandardButton.Save and not window._toolbar.save_json():
        event.ignore()
        return

    event.accept()

