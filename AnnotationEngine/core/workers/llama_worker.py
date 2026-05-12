"""core/workers/llama_worker.py - Async llama.cpp chat worker using llama-cpp-python."""

from __future__ import annotations

import os
import threading
from typing import Iterable, Any

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

_DEFAULT_CTX = 20000
_DEFAULT_MAX_TOKENS = 1500
_DEFAULT_TEMP = 0.8
_DEFAULT_TOP_P = 0.95
_DEFAULT_REPEAT_PENALTY = 1.05

_LLAMA_APP_KEY = "llama_cpp_instance"
_LLAMA_LOCK = threading.Lock()


class LlamaChatWorker(QThread):
    """Streams llama.cpp output in a background thread."""

    token_received = pyqtSignal(str)
    response_ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        model_path: str,
        messages: list[dict[str, str]],
        n_ctx: int = _DEFAULT_CTX,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = _DEFAULT_TEMP,
        top_p: float = _DEFAULT_TOP_P,
        repeat_penalty: float = _DEFAULT_REPEAT_PENALTY,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._model_path = str(model_path or "").strip()
        self._messages = list(messages or [])
        self._n_ctx = n_ctx
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._top_p = top_p
        self._repeat_penalty = repeat_penalty

    @staticmethod
    def _build_prompt(messages: Iterable[dict[str, str]]) -> str:
        system_parts: list[str] = []
        history_parts: list[str] = []
        for item in messages:
            role = str(item.get("role") or "").strip().lower()
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            if role == "system":
                system_parts.append(content)
                continue
            if role == "assistant":
                prefix = "Assistant"
            elif role == "user":
                prefix = "User"
            else:
                prefix = role.capitalize() if role else "User"
            history_parts.append(f"{prefix}: {content}")

        prompt_parts: list[str] = []
        if system_parts:
            prompt_parts.append("System: " + "\n".join(system_parts))
        prompt_parts.extend(history_parts)
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)

    @staticmethod
    def _strip_llama_preamble(text: str) -> str:
        if not text:
            return text
        markers = ["System:", "User:", "Assistant:"]
        last_idx = -1
        for marker in markers:
            idx = text.rfind(marker)
            if idx > last_idx:
                last_idx = idx
        if last_idx >= 0:
            text = text[last_idx:]
        if text.startswith("Assistant:"):
            text = text[len("Assistant:"):]
        return text.strip()

    def _validate_paths(self) -> str | None:
        if not self._model_path:
            return "Choose a llama.cpp model path first."
        if not os.path.exists(self._model_path):
            return f"Model path not found: {self._model_path}"
        return None

    def _get_app_llama(self, model_path: str, n_ctx: int) -> Any:
        app = QApplication.instance()
        cache: dict[str, Any] = {}
        if app is not None:
            existing = app.property(_LLAMA_APP_KEY)
            if isinstance(existing, dict):
                cache = existing

        if cache.get("model_path") != model_path or cache.get("n_ctx") != n_ctx or cache.get("llama") is None:
            from llama_cpp import Llama

            cache = {
                "model_path": model_path,
                "n_ctx": n_ctx,
                "llama": Llama(model_path=model_path, n_ctx=n_ctx, verbose=False),
            }
            if app is not None:
                app.setProperty(_LLAMA_APP_KEY, cache)

        return cache["llama"]

    def run(self) -> None:
        if not self._messages:
            self.failed.emit("Message is empty.")
            return

        error = self._validate_paths()
        if error:
            self.failed.emit(error)
            return

        chunks: list[str] = []

        try:
            with _LLAMA_LOCK:
                llm = self._get_app_llama(self._model_path, self._n_ctx)
            stream = llm.create_chat_completion(
                messages=self._messages,
                temperature=self._temperature,
                top_p=self._top_p,
                max_tokens=self._max_tokens,
                repeat_penalty=self._repeat_penalty,
                stream=True,
            )
            for chunk in stream:
                delta = chunk["choices"][0].get("delta", {})
                token = str(delta.get("content") or "")
                if token:
                    chunks.append(token)
                    self.token_received.emit(token)
        except ImportError:
            self.failed.emit("llama-cpp-python is not installed. Install it first.")
            return
        except Exception as exc:
            self.failed.emit(f"llama.cpp runner failed: {exc}")
            return

        content = "".join(chunks).strip()
        if not content:
            self.failed.emit("llama.cpp returned an empty response.")
            return
        self.response_ready.emit(content)

