"""
ui/panels/left_panel.py — LeftPanel

Left sidebar: folder browser + image file list.
Owns all file-switching logic including the unsaved-changes guard.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class LeftPanel(QWidget):
    """Left sidebar: folder browser and image file list.

    Signals:
        folder_opened(folder_path)   — a new folder was loaded.
        image_load_requested(path)   — MainWindow should call canvas.load_image(path).
        save_before_switch_requested — panel needs MainWindow to save before it can switch;
                                       MainWindow calls confirm_switch() or cancel_switch().
    """

    folder_opened = pyqtSignal(str)
    image_load_requested = pyqtSignal(str)   # path to load
    save_before_switch_requested = pyqtSignal()

    def __init__(
        self,
        current_image_path_fn: Callable[[], str],
        unsaved_fn: Callable[[], bool],
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Args:
            current_image_path_fn: zero-arg callable returning manager.image_path.
            unsaved_fn:            zero-arg callable returning _unsaved_changes bool.
        """
        super().__init__(parent)
        self._get_current_path = current_image_path_fn
        self._is_unsaved = unsaved_fn

        # Pending switch target while waiting for save confirmation
        self._pending_item: Optional[QListWidgetItem] = None
        self._pending_prev: Optional[QListWidgetItem] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.btn_open_folder = QPushButton("📂 Open Folder …")
        layout.addWidget(self.btn_open_folder)
        layout.addWidget(QLabel("Images:"))
        self.file_list = QListWidget()
        layout.addWidget(self.file_list)

        self.btn_open_folder.clicked.connect(self._on_open_folder)
        self.file_list.currentItemChanged.connect(self._on_file_selected)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    @property
    def folder_path(self) -> str:
        return self._folder_path if hasattr(self, "_folder_path") else ""

    def populate(self, folder: str) -> int:
        """Fill file list with images from *folder*. Returns image count."""
        self._folder_path = folder
        self.file_list.clear()
        count = 0
        for name in sorted(os.listdir(folder)):
            if Path(name).suffix.lower() in IMAGE_EXTENSIONS:
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, os.path.join(folder, name))
                self.file_list.addItem(item)
                count += 1
        return count

    def select_item_for_path(self, image_path: str) -> None:
        """Silently select the list item matching *image_path*."""
        if not image_path:
            return
        norm = os.path.normcase(os.path.abspath(image_path))
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            raw = item.data(Qt.ItemDataRole.UserRole) or ""
            if os.path.normcase(os.path.abspath(raw)) == norm:
                self.file_list.blockSignals(True)
                self.file_list.setCurrentItem(item)
                self.file_list.blockSignals(False)
                return

    def revert_selection(self, previous: Optional[QListWidgetItem]) -> None:
        """Revert list selection to *previous* (called on Cancel)."""
        self.file_list.blockSignals(True)
        self.file_list.setCurrentItem(previous)
        self.file_list.blockSignals(False)

    def confirm_switch(self) -> None:
        """Called by MainWindow after a successful save — proceed with pending switch."""
        if self._pending_item is not None:
            self._do_load(self._pending_item)
        self._pending_item = None
        self._pending_prev = None

    def cancel_switch(self) -> None:
        """Called by MainWindow when save was cancelled — revert selection."""
        if self._pending_prev is not None:
            self.revert_selection(self._pending_prev)
        self._pending_item = None
        self._pending_prev = None

    # ------------------------------------------------------------------ #
    #  Internal slots
    # ------------------------------------------------------------------ #
    def _on_open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Image Folder", self.folder_path or ""
        )
        if not folder:
            return
        count = self.populate(folder)
        self.folder_opened.emit(folder)

    def _on_file_selected(
        self,
        current: Optional[QListWidgetItem],
        previous: Optional[QListWidgetItem],
    ) -> None:
        if current is None:
            return

        # Skip if this image is already loaded
        path: str = current.data(Qt.ItemDataRole.UserRole)
        if (
            os.path.normcase(os.path.abspath(self._get_current_path()))
            == os.path.normcase(os.path.abspath(path))
        ):
            return

        if self._is_unsaved() and previous:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved annotations. Save them before switching?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                self.revert_selection(previous)
                return
            if reply == QMessageBox.StandardButton.Yes:
                # Ask MainWindow to save; it will call confirm_switch() or cancel_switch()
                self._pending_item = current
                self._pending_prev = previous
                self.save_before_switch_requested.emit()
                return

        self._do_load(current)

    def _do_load(self, item: QListWidgetItem) -> None:
        path: str = item.data(Qt.ItemDataRole.UserRole)
        self.image_load_requested.emit(path)
