"""Authentication dialog with Login and Register flows."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class AuthLoginDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Account")
        self.resize(420, 220)

        root = QVBoxLayout(self)
        self._tabs = QTabWidget(self)

        login_tab = QWidget(self)
        login_form = QFormLayout(login_tab)
        self._login_email = QLineEdit(self)
        self._login_email.setPlaceholderText("email@example.com")
        self._login_password = QLineEdit(self)
        self._login_password.setEchoMode(QLineEdit.EchoMode.Password)
        login_form.addRow("Email", self._login_email)
        login_form.addRow("Password", self._login_password)
        self._tabs.addTab(login_tab, "Login")

        register_tab = QWidget(self)
        register_form = QFormLayout(register_tab)
        self._register_email = QLineEdit(self)
        self._register_email.setPlaceholderText("email@example.com")
        self._register_password = QLineEdit(self)
        self._register_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._register_confirm = QLineEdit(self)
        self._register_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        register_form.addRow("Email", self._register_email)
        register_form.addRow("Password", self._register_password)
        register_form.addRow("Confirm Password", self._register_confirm)
        self._tabs.addTab(register_tab, "Register")

        root.addWidget(self._tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_credentials(self) -> tuple[str, str]:
        _, email, password, _ = self.get_submission()
        return email, password

    def get_submission(self) -> tuple[str, str, str, str]:
        mode = "register" if self._tabs.currentIndex() == 1 else "login"
        if mode == "register":
            return (
                mode,
                self._register_email.text().strip(),
                self._register_password.text(),
                self._register_confirm.text(),
            )
        return (
            mode,
            self._login_email.text().strip(),
            self._login_password.text(),
            "",
        )

    def accept(self) -> None:
        mode, email, password, confirm = self.get_submission()
        if not email or not password:
            QMessageBox.warning(self, "Account", "Email and password are required.")
            return
        if mode == "register" and password != confirm:
            QMessageBox.warning(self, "Account", "Passwords do not match.")
            return
        super().accept()

