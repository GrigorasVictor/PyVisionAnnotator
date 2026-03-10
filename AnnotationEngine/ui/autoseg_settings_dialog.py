"""
ui/autoseg_settings_dialog.py — AutoSeg Configuration Dialog

Allows the user to set the path for the external segmentation model:
  • A standalone executable (.exe) or script
  • Timeout (seconds)

Paths are persisted via QSettings so they survive between sessions.
"""
from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QSpinBox,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
    QWidget,
    QLabel,
)

from core.subprocess_handler import SubprocessHandler

_ORG = "PyVisionAnnotator"
_APP = "PyVisionAnnotator"


class AutoSegSettingsDialog(QDialog):
    """Modal dialog for configuring the external AutoSeg model."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure AutoSeg Model")
        self.setMinimumWidth(540)

        settings = QSettings(_ORG, _APP)

        layout = QFormLayout(self)

        # ---- Model path (.py or .exe) ----
        self.edit_model = QLineEdit()
        self.edit_model.setPlaceholderText(
            r"e.g.  C:\models\segmenter.exe"
        )
        self.edit_model.setText(settings.value("autoseg/model_path", ""))
        btn_browse_model = QPushButton("Browse …")
        btn_browse_model.clicked.connect(self._browse_model)
        row_model = QHBoxLayout()
        row_model.addWidget(self.edit_model)
        row_model.addWidget(btn_browse_model)
        layout.addRow("Model Executable:", row_model)

        # ---- Timeout ----
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(5, 600)
        self.spin_timeout.setSuffix(" s")
        self.spin_timeout.setValue(int(settings.value("autoseg/timeout", 120)))
        layout.addRow("Timeout:", self.spin_timeout)

        # ---- Info label ----
        info = QLabel(
            "<i>The subprocess will be called as:<br>"
            "• <code>model.exe --image &lt;path&gt; --point x,y</code><br>"
            "and must return JSON with a <b>\"coordinates\"</b> key.</i>"
        )
        info.setWordWrap(True)
        layout.addRow(info)

        # ---- Test button ----
        self.btn_test = QPushButton("🧪 Test Connection …")
        self.btn_test.clicked.connect(self._on_test)
        layout.addRow(self.btn_test)

        # ---- OK / Cancel ----
        btns = QDialogButtonBox()
        btns.setStandardButtons(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    # ------------------------------------------------------------------ #
    #  Browse helpers
    # ------------------------------------------------------------------ #
    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model Executable",
            self.edit_model.text() or "",
            "Executables (*.exe);;All Files (*)",
        )
        if path:
            self.edit_model.setText(path)

    # ------------------------------------------------------------------ #
    #  Test
    # ------------------------------------------------------------------ #
    def _on_test(self) -> None:
        model = self.edit_model.text().strip()

        if not model:
            QMessageBox.warning(self, "Missing", "Please set the model file path first.")
            return

        if not os.path.isfile(model):
            QMessageBox.warning(self, "Not Found", f"Model file not found:\n{model}")
            return

        # Simple test execution
        args = ["--help"]
        success, data, error = SubprocessHandler.run_command(
            executable=model,
            script=None,
            args=args,
            timeout=10,
        )

        if success or (not success and data):
            QMessageBox.information(
                self,
                "Test Passed ✅",
                f"The process started successfully.\n\n"
                f"stdout (truncated):\n{str(data)[:300]}",
            )
        else:
            QMessageBox.critical(
                self,
                "Test Failed ❌",
                f"The process could not be started.\n\nError:\n{error}",
            )

    # ------------------------------------------------------------------ #
    #  Accept / persist
    # ------------------------------------------------------------------ #
    def _on_accept(self) -> None:
        model = self.edit_model.text().strip()

        if not model:
            QMessageBox.warning(self, "Missing", "Model file path is required.")
            return

        settings = QSettings(_ORG, _APP)
        settings.setValue("autoseg/model_path", model)
        settings.setValue("autoseg/timeout", self.spin_timeout.value())
        self.accept()

    # ------------------------------------------------------------------ #
    #  Static helpers — used by MainWindow / RightPanel
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_config() -> tuple[str, Optional[str], int]:
        """Read persisted AutoSeg config from QSettings.

        Returns:
            ``(executable, script_or_None, timeout)``
        """
        settings = QSettings(_ORG, _APP)
        model_path = settings.value("autoseg/model_path", "")
        timeout = int(settings.value("autoseg/timeout", 120))

        # Script is always None now as we run the executable directly
        return model_path, None, timeout


    @staticmethod
    def is_configured() -> bool:
        """Return True if a model path has been set."""
        settings = QSettings(_ORG, _APP)
        return bool(settings.value("autoseg/model_path", ""))

