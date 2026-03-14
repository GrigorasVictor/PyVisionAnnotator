"""
ui/panels/toolbar_panel.py — ToolbarPanel + SettingsDialog

Top toolbar — owns all save/load/help/settings logic.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import QSize, pyqtSignal, QSettings
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
    QTabWidget,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QDoubleSpinBox
)

from core.subprocess_handler import SubprocessHandler

_ORG = "PyVisionAnnotator"
_APP = "PyVisionAnnotator"

class SettingsDialog(QDialog):
    """Modal dialog for application settings (Style & AutoMask)."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_width: int = 2,
        initial_font: int = 9,
        initial_height: int = 18,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 300)

        self.tabs = QTabWidget()
        
        # --- Tab 1: Visual Style ---
        self.tab_visual = QWidget()
        layout_visual = QFormLayout(self.tab_visual)

        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 20)
        self.spin_width.setValue(initial_width)
        layout_visual.addRow("Line Thickness (px):", self.spin_width)

        self.spin_font = QSpinBox()
        self.spin_font.setRange(6, 72)
        self.spin_font.setValue(initial_font)
        layout_visual.addRow("Label Font Size (pt):", self.spin_font)

        self.spin_height = QSpinBox()
        self.spin_height.setRange(10, 100)
        self.spin_height.setValue(initial_height)
        layout_visual.addRow("Label Badge Height (px):", self.spin_height)
        
        self.tabs.addTab(self.tab_visual, "Visual Style")

        # --- Tab 2: AutoMask ---
        self.tab_automask = QWidget()
        layout_automask = QFormLayout(self.tab_automask)
        
        settings = QSettings(_ORG, _APP)
        
        self.edit_model = QLineEdit()
        self.edit_model.setPlaceholderText(r"e.g. C:\models\segmenter.exe")
        self.edit_model.setText(settings.value("autoseg/model_path", ""))
        
        btn_browse = QPushButton("Browse …")
        btn_browse.clicked.connect(self._browse_model)
        
        row_model = QHBoxLayout()
        row_model.addWidget(self.edit_model)
        row_model.addWidget(btn_browse)
        layout_automask.addRow("Model Executable:", row_model)
        
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(5, 600)
        self.spin_timeout.setSuffix(" s")
        # Use safe conversion
        val_timeout = settings.value("autoseg/timeout", 120)
        try:
            val_timeout = int(val_timeout)
        except (ValueError, TypeError):
            val_timeout = 120
        self.spin_timeout.setValue(val_timeout)
        layout_automask.addRow("Timeout:", self.spin_timeout)

        info = QLabel(
            "<i>The subprocess will be called as:<br>"
            "• <code>model.exe --image &lt;path&gt; --point x,y</code><br>"
            "and must return JSON with a <b>\"coordinates\"</b> key.</i>"
        )
        info.setWordWrap(True)
        layout_automask.addRow(info)
        
        self.btn_test = QPushButton("🧪 Test Connection …")
        self.btn_test.clicked.connect(self._on_test_connection)
        layout_automask.addRow(self.btn_test)

        self.tabs.addTab(self.tab_automask, "AutoMask (Point)")

        # --- Tab 3: AutoSeg (YOLO) ---
        self.tab_autoseg = QWidget()
        layout_autoseg = QFormLayout(self.tab_autoseg)

        self.edit_yolo_exe = QLineEdit()
        self.edit_yolo_exe.setPlaceholderText(r"e.g. C:\dist\yolo_segment.exe")
        self.edit_yolo_exe.setText(settings.value("autoseg_yolo/executable", ""))

        btn_browse_exe = QPushButton("Browse Exe…")
        btn_browse_exe.clicked.connect(self._browse_yolo_exe)

        row_exe = QHBoxLayout()
        row_exe.addWidget(self.edit_yolo_exe)
        row_exe.addWidget(btn_browse_exe)
        layout_autoseg.addRow("YOLO Executable:", row_exe)

        self.edit_yolo_model = QLineEdit()
        self.edit_yolo_model.setPlaceholderText(r"e.g. yoloe-26m-seg.pt")
        self.edit_yolo_model.setText(settings.value("autoseg_yolo/model_path", ""))
        
        btn_browse_yolo = QPushButton("Browse Weights…")
        btn_browse_yolo.clicked.connect(self._browse_yolo_model)
        
        row_yolo = QHBoxLayout()
        row_yolo.addWidget(self.edit_yolo_model)
        row_yolo.addWidget(btn_browse_yolo)
        layout_autoseg.addRow("Model Weights (.pt):", row_yolo)

        self.spin_yolo_conf = QDoubleSpinBox()
        self.spin_yolo_conf.setRange(0.01, 1.0)
        self.spin_yolo_conf.setSingleStep(0.05)
        
        # Use safe conversion for float
        val_conf = settings.value("autoseg_yolo/conf", 0.32)
        try:
            val_conf = float(val_conf)
        except (ValueError, TypeError):
            val_conf = 0.32
        self.spin_yolo_conf.setValue(val_conf)
        layout_autoseg.addRow("Confidence Threshold:", self.spin_yolo_conf)

        self.edit_yolo_device = QLineEdit()
        self.edit_yolo_device.setText(settings.value("autoseg_yolo/device", "cuda" if self._has_cuda() else "cpu"))
        layout_autoseg.addRow("Device (cuda/cpu):", self.edit_yolo_device)

        layout_autoseg.addRow(QLabel("<i>Runs 'bbox' and 'segment' modes automatically.</i>"))

        self.tabs.addTab(self.tab_autoseg, "AutoSeg (YOLO)")

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        main_layout.addWidget(btns)

    def _has_cuda(self) -> bool:
        """Check if CUDA is available via torch (if installed)."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
        except Exception:
            return False

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model Executable",
            self.edit_model.text() or "",
            "Executables (*.exe);;All Files (*)",
        )
        if path:
            self.edit_model.setText(path)

    def _browse_yolo_exe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select YOLO Executable",
            self.edit_yolo_exe.text() or "",
            "Executables (*.exe);;All Files (*)",
        )
        if path:
            self.edit_yolo_exe.setText(path)

    def _browse_yolo_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select YOLO Model File",
            self.edit_yolo_model.text() or "",
            "PyTorch Models (*.pt);;All Files (*)",
        )
        if path:
            self.edit_yolo_model.setText(path)

    def _on_test_connection(self) -> None:
        model = self.edit_model.text().strip()
        if not model:
            QMessageBox.warning(self, "Missing", "Please set the model file path first.")
            return
        if not os.path.isfile(model):
            QMessageBox.warning(self, "Not Found", f"Model file not found:\n{model}")
            return
            
        args = ["--help"]
        success, data, error = SubprocessHandler.run_command(
            executable=model, script=None, args=args, timeout=10
        )
        
        if success or (not success and data):
            QMessageBox.information(self, "Test Passed ✅", f"Process started.\nStdout:\n{str(data)[:300]}")
        else:
            QMessageBox.critical(self, "Test Failed ❌", f"Process failed.\nError:\n{error}")

    def accept(self) -> None:
        # Save AutoMask settings immediately
        settings = QSettings(_ORG, _APP)
        settings.setValue("autoseg/model_path", self.edit_model.text().strip())
        settings.setValue("autoseg/timeout", self.spin_timeout.value())
        
        # Save AutoSeg (YOLO) settings
        settings.setValue("autoseg_yolo/executable", self.edit_yolo_exe.text().strip())
        settings.setValue("autoseg_yolo/conf", self.spin_yolo_conf.value())
        settings.setValue("autoseg_yolo/device", self.edit_yolo_device.text().strip())
        
        super().accept()

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
        self._act_help: QAction       = self.addAction("❓ Help")

        self._act_save_json.triggered.connect(self._on_save_json)
        self._act_save_csv.triggered.connect(self._on_save_csv)
        self._act_load_json.triggered.connect(self._on_load_json)
        self._act_load_csv.triggered.connect(self._on_load_csv)
        self._act_settings.triggered.connect(self._on_settings)
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
            self.settings_applied.emit(w, f, h)

    def _on_autoseg_config(self) -> None:
        # Deprecated/Removed, but keeping method if accidentally called?
        # Better to remove it, but I'm replacing the button.
        pass

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
