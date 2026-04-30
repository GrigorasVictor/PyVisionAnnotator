"""core/workers/ollama_worker.py - Async Ollama workers for model list and chat."""
from __future__ import annotations

import importlib
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal


class OllamaModelsWorker(QThread):
    """Loads available local Ollama models without blocking the UI thread."""

    models_loaded = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, host: str = "", parent=None) -> None:
        super().__init__(parent)
        self._host = str(host or "").strip()

    def _build_client(self):
        ollama = importlib.import_module("ollama")
        client_cls = getattr(ollama, "Client", None)
        if client_cls is None:
            return ollama
        if self._host:
            return client_cls(host=self._host)
        return client_cls()

    @staticmethod
    def _extract_models(response: Any) -> list[str]:
        if isinstance(response, dict):
            raw_models = response.get("models")
        else:
            raw_models = getattr(response, "models", None)

        names: list[str] = []
        if not isinstance(raw_models, list):
            return names

        for model in raw_models:
            if isinstance(model, dict):
                name = str(model.get("model") or model.get("name") or "").strip()
            else:
                name = str(getattr(model, "model", "") or getattr(model, "name", "")).strip()
            if name and name not in names:
                names.append(name)
        return names

    def run(self) -> None:
        try:
            client = self._build_client()
            response = client.list()
            model_names = self._extract_models(response)
            self.models_loaded.emit(model_names)
        except ModuleNotFoundError:
            self.failed.emit("Missing dependency: install 'ollama'.")
        except Exception as exc:
            self.failed.emit(f"Could not load Ollama models: {exc}")


class OllamaChatWorker(QThread):
    """Sends a chat request to Ollama in the background."""

    token_received = pyqtSignal(str)
    response_ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, model: str, messages: list[dict[str, str]], host: str = "", parent=None) -> None:
        super().__init__(parent)
        self._model = str(model or "").strip()
        self._messages = list(messages or [])
        self._host = str(host or "").strip()

    def _build_client(self):
        ollama = importlib.import_module("ollama")
        client_cls = getattr(ollama, "Client", None)
        if client_cls is None:
            return ollama
        if self._host:
            return client_cls(host=self._host)
        return client_cls()

    @staticmethod
    def _extract_text(response: Any) -> str:
        if isinstance(response, dict):
            message = response.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if content:
                    return str(content)
            content = response.get("response")
            if content:
                return str(content)
        message = getattr(response, "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if content:
                return str(content)
        return ""

    @staticmethod
    def _extract_token(chunk: Any) -> str:
        if isinstance(chunk, dict):
            message = chunk.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if content:
                    return str(content)
            content = chunk.get("response")
            if content:
                return str(content)
        message = getattr(chunk, "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if content:
                return str(content)
        content = getattr(chunk, "response", None)
        if content:
            return str(content)
        return ""

    def run(self) -> None:
        if not self._model:
            self.failed.emit("Choose a model first.")
            return
        if not self._messages:
            self.failed.emit("Message is empty.")
            return

        try:
            client = self._build_client()
            stream = client.chat(model=self._model, messages=self._messages, stream=True)
            chunks: list[str] = []
            for chunk in stream:
                token = self._extract_token(chunk)
                if not token:
                    continue
                chunks.append(token)
                self.token_received.emit(token)
            content = "".join(chunks).strip()
            if not content:
                # Fallback for clients/backends that return a final non-streamed object.
                response = client.chat(model=self._model, messages=self._messages, stream=False)
                content = self._extract_text(response).strip()
            if not content:
                self.failed.emit("Ollama returned an empty response.")
                return
            self.response_ready.emit(content)
        except ModuleNotFoundError:
            self.failed.emit("Missing dependency: install 'ollama'.")
        except Exception as exc:
            self.failed.emit(f"Chat request failed: {exc}")

