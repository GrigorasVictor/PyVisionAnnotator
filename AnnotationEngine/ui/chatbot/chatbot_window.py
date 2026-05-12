"""ui/chatbot/chatbot_window.py - Lightweight Ollama chat UI with model picker."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from core.workers.ollama_worker import OllamaChatWorker, OllamaModelsWorker
from core.workers.llama_worker import LlamaChatWorker, _DEFAULT_CTX, _DEFAULT_MAX_TOKENS, _DEFAULT_TEMP, _DEFAULT_TOP_P, _DEFAULT_REPEAT_PENALTY
from ui.chatbot.prompt import build_system_message
from ui.chatbot.llama_params_dialog import LlamaParamsDialog

_ORG = "PyVisionAnnotator"
_APP = "PyVisionAnnotator"
_DEFAULT_HOST = "http://localhost:11434"


class ChatbotWindow(QWidget):
    """Simple local chatbot window backed by Ollama."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chatbot (Ollama)")
        self.resize(760, 560)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._models_worker: Optional[OllamaModelsWorker] = None
        self._chat_worker: Optional[OllamaChatWorker | LlamaChatWorker] = None
        self._messages: list[dict[str, str]] = [build_system_message()]
        self._assistant_streaming: bool = False
        self._stream_buffer: str = ""

        self._build_ui()
        self._load_settings()
        self._connect_signals()
        self._refresh_models()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("Ollama Assistant")
        title.setObjectName("chatbotTitle")
        root.addWidget(title)

        subtitle = QLabel("Local AI helper for annotation workflow and troubleshooting.")
        subtitle.setObjectName("chatbotSubtitle")
        root.addWidget(subtitle)

        backend_row = QHBoxLayout()
        backend_row.addWidget(QLabel("Backend:"))
        self.combo_backend = QComboBox()
        self.combo_backend.addItems(["Ollama", "Llama.cpp"])
        backend_row.addWidget(self.combo_backend, 1)
        root.addLayout(backend_row)

        self.ollama_widget = QWidget()
        ollama_row = QHBoxLayout(self.ollama_widget)
        ollama_row.setContentsMargins(0, 0, 0, 0)
        ollama_row.addWidget(QLabel("Host:"))
        self.edit_host = QLineEdit()
        self.edit_host.setPlaceholderText(_DEFAULT_HOST)
        ollama_row.addWidget(self.edit_host, 2)

        ollama_row.addWidget(QLabel("Model:"))
        self.combo_models = QComboBox()
        self.combo_models.setMinimumWidth(220)
        ollama_row.addWidget(self.combo_models, 2)

        self.btn_refresh = QPushButton("Refresh Models")
        ollama_row.addWidget(self.btn_refresh)
        root.addWidget(self.ollama_widget)

        self.llama_widget = QWidget()
        llama_row = QVBoxLayout(self.llama_widget)
        llama_row.setContentsMargins(0, 0, 0, 0)

        llama_model_row = QHBoxLayout()
        llama_model_row.addWidget(QLabel("Model path:"))
        self.edit_llama_model = QLineEdit()
        self.edit_llama_model.setPlaceholderText("E:\\model.gguf")
        llama_model_row.addWidget(self.edit_llama_model, 2)
        self.btn_browse_llama_model = QPushButton("Browse")
        llama_model_row.addWidget(self.btn_browse_llama_model)
        self.btn_llama_params = QPushButton("Parameters")
        llama_model_row.addWidget(self.btn_llama_params)
        llama_row.addLayout(llama_model_row)

        root.addWidget(self.llama_widget)

        self.view_chat = QTextEdit()
        self.view_chat.setReadOnly(True)
        self.view_chat.setPlaceholderText("Conversation will appear here...")
        root.addWidget(self.view_chat, 1)

        self.edit_prompt = QTextEdit()
        self.edit_prompt.setPlaceholderText("Write a message and press Send...")
        self.edit_prompt.setMaximumHeight(140)
        root.addWidget(self.edit_prompt)

        action_row = QHBoxLayout()
        self.lbl_status = QLabel("Ready.")
        action_row.addWidget(self.lbl_status, 1)

        self.btn_clear = QPushButton("Clear")
        action_row.addWidget(self.btn_clear)

        self.btn_send = QPushButton("Send")
        action_row.addWidget(self.btn_send)
        root.addLayout(action_row)

        # Keep native/application style; only layout/flow is customized.

    def _connect_signals(self) -> None:
        self.btn_refresh.clicked.connect(self._refresh_models)
        self.btn_send.clicked.connect(self._send_prompt)
        self.btn_clear.clicked.connect(self._clear_chat)
        self.combo_backend.currentIndexChanged.connect(self._on_backend_changed)
        self.btn_browse_llama_model.clicked.connect(self._browse_llama_model)
        self.btn_llama_params.clicked.connect(self._open_llama_params)

    def _load_settings(self) -> None:
        settings = QSettings(_ORG, _APP)
        host = str(settings.value("ollama/host", _DEFAULT_HOST) or _DEFAULT_HOST).strip()
        self.edit_host.setText(host)
        backend = str(settings.value("chatbot/backend", "Ollama") or "Ollama").strip()
        idx = self.combo_backend.findText(backend)
        if idx >= 0:
            self.combo_backend.setCurrentIndex(idx)
        self.edit_llama_model.setText(str(settings.value("llama/model_path", "") or "").strip())
        self._update_backend_visibility()

    def _save_settings(self) -> None:
        settings = QSettings(_ORG, _APP)
        settings.setValue("chatbot/backend", self.combo_backend.currentText().strip())
        settings.setValue("ollama/host", self.edit_host.text().strip() or _DEFAULT_HOST)
        settings.setValue("ollama/model", self.combo_models.currentText().strip())
        settings.setValue("llama/model_path", self.edit_llama_model.text().strip())

    def _append(self, role: str, text: str) -> None:
        self.view_chat.append(f"{role}:\n{text}\n")
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        scrollbar = self.view_chat.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _start_assistant_stream(self) -> None:
        if self._assistant_streaming:
            return
        self._assistant_streaming = True
        self._stream_buffer = ""
        self.view_chat.append("Assistant:\n")
        self._scroll_to_bottom()

    def _append_assistant_token(self, token: str) -> None:
        if not token:
            return
        if not self._assistant_streaming:
            self._start_assistant_stream()
        self._stream_buffer += token
        cursor = self.view_chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self.view_chat.setTextCursor(cursor)
        self._scroll_to_bottom()

    def _finish_assistant_stream(self) -> None:
        if not self._assistant_streaming:
            return
        self._assistant_streaming = False
        self.view_chat.append("\n")
        self._scroll_to_bottom()

    def _set_busy(self, busy: bool) -> None:
        self.btn_send.setEnabled(not busy)
        self.btn_refresh.setEnabled(not busy)
        self.edit_host.setEnabled(not busy)
        self.combo_models.setEnabled(not busy)
        self.combo_backend.setEnabled(not busy)
        self.edit_llama_model.setEnabled(not busy)
        self.btn_browse_llama_model.setEnabled(not busy)
        self.btn_llama_params.setEnabled(not busy)

    def _refresh_models(self) -> None:
        if self._backend_is_llama():
            return
        if self._models_worker and self._models_worker.isRunning():
            return

        self._set_busy(True)
        self.lbl_status.setText("Loading models...")

        host = self.edit_host.text().strip()
        self._models_worker = OllamaModelsWorker(host=host, parent=self)
        self._models_worker.models_loaded.connect(self._on_models_loaded)
        self._models_worker.failed.connect(self._on_models_failed)
        self._models_worker.finished.connect(lambda: self._set_busy(False))
        self._models_worker.start()

    def _on_models_loaded(self, models: list[str]) -> None:
        selected_before = self.combo_models.currentText().strip()
        persisted = str(QSettings(_ORG, _APP).value("ollama/model", "") or "").strip()

        self.combo_models.blockSignals(True)
        self.combo_models.clear()
        self.combo_models.addItems(models)
        self.combo_models.blockSignals(False)

        if selected_before:
            idx = self.combo_models.findText(selected_before)
            if idx >= 0:
                self.combo_models.setCurrentIndex(idx)
        elif persisted:
            idx = self.combo_models.findText(persisted)
            if idx >= 0:
                self.combo_models.setCurrentIndex(idx)

        if models:
            self.lbl_status.setText(f"Loaded {len(models)} model(s).")
            self._save_settings()
            return

        self.lbl_status.setText("No models found. Pull one with 'ollama pull <model>'.")

    def _on_models_failed(self, message: str) -> None:
        self.lbl_status.setText(message)

    def _send_prompt(self) -> None:
        if self._chat_worker and self._chat_worker.isRunning():
            return

        prompt = self.edit_prompt.toPlainText().strip()
        if not prompt:
            return

        if self._backend_is_llama():
            model_path = self.edit_llama_model.text().strip()
            if not model_path:
                QMessageBox.warning(self, "Model", "Choose a llama.cpp model path first.")
                return
        else:
            model = self.combo_models.currentText().strip()
            if not model:
                QMessageBox.warning(self, "Model", "Choose an Ollama model first.")
                return

        self._append("You", prompt)
        self._messages.append({"role": "user", "content": prompt})
        self.edit_prompt.clear()

        self._set_busy(True)
        self._save_settings()

        if self._backend_is_llama():
            self.lbl_status.setText("Waiting for llama.cpp...")
            model_path = self.edit_llama_model.text().strip()
            
            settings = QSettings(_ORG, _APP)
            n_ctx = int(settings.value("llama/n_ctx", _DEFAULT_CTX))
            max_tokens = int(settings.value("llama/max_tokens", _DEFAULT_MAX_TOKENS))
            temp = float(settings.value("llama/temperature", _DEFAULT_TEMP))
            top_p = float(settings.value("llama/top_p", _DEFAULT_TOP_P))
            rep_pen = float(settings.value("llama/repeat_penalty", _DEFAULT_REPEAT_PENALTY))
            
            self._chat_worker = LlamaChatWorker(
                model_path=model_path,
                messages=self._messages,
                n_ctx=n_ctx,
                max_tokens=max_tokens,
                temperature=temp,
                top_p=top_p,
                repeat_penalty=rep_pen,
                parent=self,
            )
        else:
            model = self.combo_models.currentText().strip()
            self.lbl_status.setText(f"Waiting for {model}...")
            host = self.edit_host.text().strip()
            self._chat_worker = OllamaChatWorker(model=model, messages=self._messages, host=host, parent=self)

        self._chat_worker.token_received.connect(self._on_chat_token)
        self._chat_worker.response_ready.connect(self._on_chat_response)
        self._chat_worker.failed.connect(self._on_chat_failed)
        self._chat_worker.finished.connect(lambda: self._set_busy(False))
        self._chat_worker.start()

    def _on_chat_token(self, token: str) -> None:
        self._append_assistant_token(token)

    def _on_chat_response(self, text: str) -> None:
        if self._assistant_streaming:
            self._finish_assistant_stream()
            final_text = self._stream_buffer.strip() or text
        else:
            final_text = text
            self._append("Assistant", final_text)

        self._messages.append({"role": "assistant", "content": final_text})
        self._stream_buffer = ""
        self.lbl_status.setText("Ready.")

    def _on_chat_failed(self, message: str) -> None:
        if self._assistant_streaming:
            self._finish_assistant_stream()
            self._stream_buffer = ""
        self.lbl_status.setText(message)
        self._append("System", message)

    def _clear_chat(self) -> None:
        self._messages = [build_system_message()]
        self._assistant_streaming = False
        self._stream_buffer = ""
        self.view_chat.clear()
        self.lbl_status.setText("Conversation cleared. Session prompt kept.")

    def _backend_is_llama(self) -> bool:
        return self.combo_backend.currentText().strip().lower() == "llama.cpp"

    def _update_backend_visibility(self) -> None:
        use_llama = self._backend_is_llama()
        self.ollama_widget.setVisible(not use_llama)
        self.llama_widget.setVisible(use_llama)
        self.btn_refresh.setEnabled(not use_llama)

    def _on_backend_changed(self) -> None:
        self._update_backend_visibility()
        self._save_settings()
        if not self._backend_is_llama():
            self._refresh_models()
        else:
            self.lbl_status.setText("Ready (llama.cpp).")

    def _browse_llama_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select GGUF model", "", "GGUF Model (*.gguf);;All Files (*)")
        if path:
            self.edit_llama_model.setText(path)
            self._save_settings()

    def _open_llama_params(self) -> None:
        settings = QSettings(_ORG, _APP)
        n_ctx = int(settings.value("llama/n_ctx", _DEFAULT_CTX))
        max_tokens = int(settings.value("llama/max_tokens", _DEFAULT_MAX_TOKENS))
        temp = float(settings.value("llama/temperature", _DEFAULT_TEMP))
        top_p = float(settings.value("llama/top_p", _DEFAULT_TOP_P))
        rep_pen = float(settings.value("llama/repeat_penalty", _DEFAULT_REPEAT_PENALTY))

        dlg = LlamaParamsDialog(self)
        dlg.set_values(n_ctx, max_tokens, temp, top_p, rep_pen)
        if dlg.exec():
            new_n_ctx, new_max, new_temp, new_top_p, new_rep = dlg.get_values()
            settings.setValue("llama/n_ctx", new_n_ctx)
            settings.setValue("llama/max_tokens", new_max)
            settings.setValue("llama/temperature", new_temp)
            settings.setValue("llama/top_p", new_top_p)
            settings.setValue("llama/repeat_penalty", new_rep)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_settings()
        super().closeEvent(event)

