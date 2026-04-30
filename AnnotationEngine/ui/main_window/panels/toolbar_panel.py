"""
ui/panels/toolbar_panel.py — ToolbarPanel + SettingsDialog

Top toolbar — owns all save/load/help/settings logic.
"""
from __future__ import annotations

import os
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
    QDoubleSpinBox,
    QSizePolicy,
)

from core.subprocess_handler import SubprocessHandler

_ORG = "PyVisionAnnotator"
_APP = "PyVisionAnnotator"
_DEFAULT_LOGIN_URL = "http://localhost/auth/login"
_DEFAULT_REGISTER_URL = "http://localhost/auth/register"

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

        self.edit_automask_device = QLineEdit()
        self.edit_automask_device.setText(str(settings.value("autoseg/device", "cpu")))
        self.edit_automask_device.setPlaceholderText("cpu or cuda")
        layout_automask.addRow("Device (cpu/cuda):", self.edit_automask_device)

        self.edit_automask_extra_args = QLineEdit()
        self.edit_automask_extra_args.setPlaceholderText(r'e.g. --half --imgsz 1024')
        self.edit_automask_extra_args.setText(str(settings.value("autoseg/extra_args", "")))
        layout_automask.addRow("Custom Args:", self.edit_automask_extra_args)

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
        self.edit_yolo_device.setText(str(settings.value("autoseg_yolo/device", "cpu")))
        layout_autoseg.addRow("Device (cuda/cpu):", self.edit_yolo_device)

        self.edit_yolo_extra_args = QLineEdit()
        self.edit_yolo_extra_args.setPlaceholderText(r'e.g. --imgsz 1280 --agnostic-nms')
        self.edit_yolo_extra_args.setText(str(settings.value("autoseg_yolo/extra_args", "")))
        layout_autoseg.addRow("Custom Args:", self.edit_yolo_extra_args)

        layout_autoseg.addRow(QLabel("<i>Runs 'bbox' and 'segment' modes automatically.</i>"))

        self.tabs.addTab(self.tab_autoseg, "AutoSeg (YOLO)")

        # --- Tab 4: Account ---
        self.tab_account = QWidget()
        layout_account = QFormLayout(self.tab_account)

        self.edit_auth_login_url = QLineEdit()
        self.edit_auth_login_url.setPlaceholderText(_DEFAULT_LOGIN_URL)
        self.edit_auth_login_url.setText(str(settings.value("auth/login_url", _DEFAULT_LOGIN_URL)))
        layout_account.addRow("Login URL:", self.edit_auth_login_url)

        self.edit_auth_register_url = QLineEdit()
        self.edit_auth_register_url.setPlaceholderText(_DEFAULT_REGISTER_URL)
        self.edit_auth_register_url.setText(str(settings.value("auth/register_url", _DEFAULT_REGISTER_URL)))
        layout_account.addRow("Register URL:", self.edit_auth_register_url)

        self.tabs.addTab(self.tab_account, "Account")

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        main_layout.addWidget(btns)

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
        settings.setValue("autoseg/device", self.edit_automask_device.text().strip())
        settings.setValue("autoseg/extra_args", self.edit_automask_extra_args.text().strip())
        
        # Save AutoSeg (YOLO) settings
        settings.setValue("autoseg_yolo/executable", self.edit_yolo_exe.text().strip())
        settings.setValue("autoseg_yolo/model_path", self.edit_yolo_model.text().strip())
        settings.setValue("autoseg_yolo/conf", self.spin_yolo_conf.value())
        settings.setValue("autoseg_yolo/device", self.edit_yolo_device.text().strip())
        settings.setValue("autoseg_yolo/extra_args", self.edit_yolo_extra_args.text().strip())

        # Save Account endpoints
        login_url = self.edit_auth_login_url.text().strip() or _DEFAULT_LOGIN_URL
        register_url = self.edit_auth_register_url.text().strip() or _DEFAULT_REGISTER_URL
        settings.setValue("auth/login_url", login_url)
        settings.setValue("auth/register_url", register_url)
        
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
        auth_requested()             — request auth flow (MainWindow handles popup + HTTP).
    """

    status_message = pyqtSignal(str)
    settings_applied = pyqtSignal(int, int, int)   # pen_width, font_size, label_height
    unsaved_cleared = pyqtSignal()
    annotations_loaded = pyqtSignal(str, list)     # image_path, annotation dicts
    auth_requested = pyqtSignal()
    chat_requested = pyqtSignal()
    chatbot_requested = pyqtSignal()
    export_requested = pyqtSignal(str)

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
        self._act_export_coco: QAction = self.addAction("🧩 Export COCO Template")
        self._act_export_yolo: QAction = self.addAction("🧩 Export YOLO Template")
        self._act_export_mask_image: QAction = self.addAction("🖼 Save Mask Image")
        self._act_load_json: QAction = self.addAction("📥 Load JSON")
        self._add_big_separator()
        self._act_auth: QAction = self.addAction("👤 Account")
        self._act_chat: QAction = self.addAction("💬 Chat")
        self._act_chatbot: QAction = self.addAction("🤖 Chatbot")
        self._add_big_separator()
        self._add_flexible_spacer()
        self._act_settings: QAction   = self.addAction("⚙ Settings")
        self._act_help: QAction       = self.addAction("❓ Help")

        self._act_save_json.triggered.connect(self._on_save_json)
        self._act_export_coco.triggered.connect(self._on_export_coco_template)
        self._act_export_yolo.triggered.connect(self._on_export_yolo_template)
        self._act_export_mask_image.triggered.connect(lambda: self.export_requested.emit("mask_photo"))
        self._act_load_json.triggered.connect(self._on_load_json)
        self._act_auth.triggered.connect(self.auth_requested.emit)
        self._act_chat.triggered.connect(self.chat_requested.emit)
        self._act_chatbot.triggered.connect(self.chatbot_requested.emit)
        self._act_settings.triggered.connect(self._on_settings)
        self._act_help.triggered.connect(self._on_help)

    def _add_big_separator(self, spacer_width: int = 26) -> None:
        """Add a visual group split with extra horizontal spacing."""
        self.addSeparator()
        spacer = QWidget(self)
        spacer.setFixedWidth(max(0, int(spacer_width)))
        self.addWidget(spacer)

    def _add_flexible_spacer(self) -> None:
        """Push following actions to the right side of the toolbar."""
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

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

    def _on_export_coco_template(self) -> None:
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
            from utils.io_handler import export_template_structure
            saved = export_template_structure(
                output_dir=self._export_root,
                image_full_path=self._manager.image_path,
                width=self._manager.image_width,
                height=self._manager.image_height,
                annotations=self._manager.get_all_dicts(),
                template="coco",
            )
            self.status_message.emit(f"Saved {len(saved)} file(s) to {self._export_root}")
        except Exception as exc:
            QMessageBox.critical(self.parent(), "Export Error", f"Failed to export COCO template:\n{exc}")

    def _on_export_yolo_template(self) -> None:
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
            from utils.io_handler import export_template_structure
            saved = export_template_structure(
                output_dir=self._export_root,
                image_full_path=self._manager.image_path,
                width=self._manager.image_width,
                height=self._manager.image_height,
                annotations=self._manager.get_all_dicts(),
                template="yolo",
            )
            self.status_message.emit(f"Saved {len(saved)} file(s) to {self._export_root}")
        except Exception as exc:
            QMessageBox.critical(self.parent(), "Export Error", f"Failed to export YOLO template:\n{exc}")

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
                "• <b>Toolbar</b>: Export COCO / YOLO templates / Save Mask Image<br>"
                "<br>"
                "<b>Mouse Controls:</b><br>"
                "• <b>Wheel</b>: Zoom In/Out<br>"
                "• <b>Middle Click</b> (or Space + Drag): Pan image<br>"
                "• <b>Left Drag</b>: Draw bounding box (Rect tool)<br>"
                "• <b>Left Click</b>: Add polygon point (Poly tool)<br>"
                "• <b>Right Click / Enter</b>: Close polygon<br>"
                "• <b>Click annotation</b>: Select<br>"
            ),
        )
