"""
ui/panels/toolbar_panel.py — ToolbarPanel + SettingsDialog

Top toolbar — owns all save/load/help/settings logic.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QToolBar,
    QDialog,
    QFormLayout,
    QSpinBox,
    QDialogButtonBox,
    QWidget,
    QMainWindow,
    QFileDialog,
    QMessageBox,
)


class SettingsDialog(QDialog):
    """Modal dialog for adjusting global annotation style settings."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_width: int = 2,
        initial_font: int = 9,
        initial_height: int = 18,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Annotation Settings")
        self.resize(300, 150)

        layout = QFormLayout(self)

        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 20)
        self.spin_width.setValue(initial_width)
        layout.addRow("Line Thickness (px):", self.spin_width)

        self.spin_font = QSpinBox()
        self.spin_font.setRange(6, 72)
        self.spin_font.setValue(initial_font)
        layout.addRow("Label Font Size (pt):", self.spin_font)

        self.spin_height = QSpinBox()
        self.spin_height.setRange(10, 100)
        self.spin_height.setValue(initial_height)
        layout.addRow("Label Badge Height (px):", self.spin_height)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_values(self) -> tuple[int, int, int]:
        """Return (pen_width, font_size, label_height)."""
        return self.spin_width.value(), self.spin_font.value(), self.spin_height.value()


class ToolbarPanel(QToolBar):
    """Top application toolbar — owns all save/load/help/settings logic.

    Outward signals:
        status_message(str)          — update the status bar.
        settings_applied(w, f, h)    — new pen/font/height values (MainWindow applies to manager).
        unsaved_cleared()            — a successful save cleared the dirty flag.
        annotations_loaded(img, lst) — finished loading: image path + annotation list.
    """

    status_message = pyqtSignal(str)
    settings_applied = pyqtSignal(int, int, int)   # pen_width, font_size, label_height
    unsaved_cleared = pyqtSignal()
    annotations_loaded = pyqtSignal(str, list)     # image_path, annotation dicts
    autoseg_config_requested = pyqtSignal()        # open AutoSeg settings dialog

    def __init__(
        self,
        manager,                          # AnnotationManager
        folder_path_fn: Callable[[], str],  # zero-arg → left panel's folder_path
        parent: Optional[QMainWindow] = None,
    ) -> None:
        super().__init__("Main", parent)
        self._manager = manager
        self._get_folder_path = folder_path_fn
        self._export_root: Optional[str] = None

        self.setMovable(False)
        self.setIconSize(QSize(20, 20))

        self._act_save_json: QAction = self.addAction("💾 Save JSON")
        self._act_save_csv: QAction  = self.addAction("📄 Save CSV")
        self._act_load_json: QAction = self.addAction("📥 Load JSON")
        self._act_load_csv: QAction  = self.addAction("📊 Load CSV")
        self.addSeparator()
        self._act_settings: QAction   = self.addAction("⚙ Settings")
        self._act_autoseg: QAction    = self.addAction("🤖 AutoSeg")
        self._act_help: QAction       = self.addAction("❓ Help")

        self._act_save_json.triggered.connect(self._on_save_json)
        self._act_save_csv.triggered.connect(self._on_save_csv)
        self._act_load_json.triggered.connect(self._on_load_json)
        self._act_load_csv.triggered.connect(self._on_load_csv)
        self._act_settings.triggered.connect(self._on_settings)
        self._act_autoseg.triggered.connect(self._on_autoseg_config)
        self._act_help.triggered.connect(self._on_help)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def reset_export_root(self) -> None:
        """Call when a new folder is opened so the next save asks for directory."""
        self._export_root = None

    def save_json(self) -> bool:
        """Public entry-point used by keyboard shortcut / unsaved-changes guard."""
        return self._on_save_json()

    # ------------------------------------------------------------------ #
    #  Save
    # ------------------------------------------------------------------ #
    def _on_save_json(self) -> bool:
        if not self._manager.image_path:
            QMessageBox.warning(self.parent(), "No image", "Load an image first.")
            return False
        if self._export_root is None:
            chosen = QFileDialog.getExistingDirectory(
                self.parent(), "Select Directory to Save Annotations",
                os.path.dirname(self._manager.image_path),
            )
            if not chosen:
                return False
            self._export_root = chosen
        try:
            from utils.io_handler import save_dataset_structure
            saved = save_dataset_structure(
                output_dir=self._export_root,
                image_full_path=self._manager.image_path,
                width=self._manager.image_width,
                height=self._manager.image_height,
                annotations=self._manager.get_all_dicts(),
                format="json",
            )
            self.status_message.emit(f"Saved {len(saved)} file(s) to {self._export_root}")
            self.unsaved_cleared.emit()
            return True
        except Exception as exc:
            QMessageBox.critical(self.parent(), "Save Error", f"Failed to save JSON:\n{exc}")
            return False

    def _on_save_csv(self) -> None:
        if not self._manager.image_path:
            QMessageBox.warning(self.parent(), "No image", "Load an image first.")
            return
        if self._export_root is None:
            chosen = QFileDialog.getExistingDirectory(
                self.parent(), "Select Directory to Save Annotations",
                os.path.dirname(self._manager.image_path),
            )
            if not chosen:
                return
            self._export_root = chosen
        try:
            from utils.io_handler import save_dataset_structure
            saved = save_dataset_structure(
                output_dir=self._export_root,
                image_full_path=self._manager.image_path,
                width=self._manager.image_width,
                height=self._manager.image_height,
                annotations=self._manager.get_all_dicts(),
                format="csv",
            )
            self.status_message.emit(f"Saved {len(saved)} file(s) to {self._export_root}")
        except Exception as exc:
            QMessageBox.critical(self.parent(), "Save Error", f"Failed to save CSV:\n{exc}")

    # ------------------------------------------------------------------ #
    #  Load
    # ------------------------------------------------------------------ #
    def _resolve_image_path(self, annotation_file: str, stored: str) -> Optional[str]:
        if os.path.isfile(stored):
            return stored
        base = os.path.basename(stored)
        for candidate in (
            os.path.join(os.path.dirname(annotation_file), base),
            os.path.join(os.path.dirname(os.path.dirname(annotation_file)), base),
        ):
            if os.path.isfile(candidate):
                return candidate
        # Try folder currently open in left panel
        folder = self._get_folder_path()
        if folder:
            cand = os.path.join(folder, base)
            if os.path.isfile(cand):
                return cand
        return None

    def _on_load_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.parent(), "Load Annotations (JSON)",
            self._get_folder_path() or "", "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            from utils.io_handler import import_json
            filename, _w, _h, ann_list = import_json(path)
        except Exception as exc:
            QMessageBox.critical(self.parent(), "Load error", str(exc))
            return
        img_path = self._resolve_image_path(path, filename) or ""
        self.annotations_loaded.emit(img_path, ann_list)

    def _on_load_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.parent(), "Load Annotations (CSV)",
            self._get_folder_path() or "", "CSV Files (*.csv)",
        )
        if not path:
            return
        try:
            from utils.io_handler import import_csv
            data = import_csv(path)
        except Exception as exc:
            QMessageBox.critical(self.parent(), "Load error", str(exc))
            return
        if not data:
            QMessageBox.warning(self.parent(), "Empty CSV", "No data found in CSV.")
            return
        filename = next(iter(data))
        ann_list = data[filename]
        img_path = self._resolve_image_path(path, filename) or ""
        self.annotations_loaded.emit(img_path, ann_list)

    # ------------------------------------------------------------------ #
    #  Settings & Help
    # ------------------------------------------------------------------ #
    def _on_settings(self) -> None:
        dlg = SettingsDialog(
            self.parent(),
            initial_width=self._manager.settings_pen_width,
            initial_font=self._manager.settings_font_size,
            initial_height=self._manager.settings_label_height,
        )
        if dlg.exec():
            w, f, h = dlg.get_values()
            self._manager.update_global_settings(w, f, h)
            self.settings_applied.emit(w, f, h)
            self.status_message.emit(f"Settings: Width={w}px, Font={f}pt, Height={h}px")

    def _on_autoseg_config(self) -> None:
        """Open the AutoSeg model configuration dialog."""
        self.autoseg_config_requested.emit()

    def _on_help(self) -> None:
        QMessageBox.information(
            self.parent(),
            "Help & Shortcuts",
            (
                "<b>Shortcuts:</b><br>"
                "• <b>Ctrl+O</b>: Open Image Folder<br>"
                "• <b>Ctrl+S</b>: Save JSON<br>"
                "• <b>Delete</b>: Remove selected annotation<br>"
                "<br>"
                "<b>Mouse Controls:</b><br>"
                "• <b>Wheel</b>: Zoom In/Out<br>"
                "• <b>Middle Click</b> (or Space + Drag): Pan image<br>"
                "• <b>Left Drag</b>: Draw bounding box (Rect tool)<br>"
                "• <b>Left Click</b>: Add polygon point (Poly tool)<br>"
                "• <b>Right Click / Enter</b>: Close polygon<br>"
                "• <b>Click annotation</b>: Select<br>"
                "<br>"
                "<b>AutoSeg Tool:</b><br>"
                "• Configure model via toolbar → <i>🤖 AutoSeg</i><br>"
                "• Accepts a <b>.py</b> script or standalone <b>.exe</b><br>"
                "• <b>Left Click</b> on object: Run auto-segmentation<br>"
                "• Result is added as a polygon annotation<br>"
            ),
        )
