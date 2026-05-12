"""
PyVisionAnnotator — Entry point.

Launches the main application window.
"""
import sys

# ---------------------------------------------------------
# WORKAROUND FOR LLAMA_CPP CRASH (Access Violation 0x000000)
# Must import llama_cpp before torch/numpy/pandas so that 
# llama_cpp can load its native OpenMP/BLAS DLLs first.
# ---------------------------------------------------------
try:
    import llama_cpp
except ImportError:
    pass

from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _is_exec_candidate(path: Path) -> bool:
    return path.suffix.lower() in {".exe", ".bat", ".cmd", ".py"}


def _find_candidate(folder: Path, keywords: tuple[str, ...], exclude: set[Path] | None = None) -> Path | None:
    excluded = {p.resolve() for p in (exclude or set())}
    best: Path | None = None
    best_score = -1
    for p in folder.rglob("*"):
        if not p.is_file() or not _is_exec_candidate(p):
            continue
        rp = p.resolve()
        if rp in excluded:
            continue
        name = p.name.lower()
        score = sum(2 for k in keywords if k in name)
        if score == 0:
            continue
        score -= int(len(str(p))) // 120  # prefer shorter relative paths on tie
        if score > best_score:
            best = p
            best_score = score
    return best


def _find_yolo_weights(folder: Path) -> Path | None:
    best: Path | None = None
    for p in folder.rglob("*.pt"):
        if not p.is_file():
            continue
        name = p.name.lower()
        if "yolo" not in name and "seg" not in name:
            continue
        if best is None or len(str(p)) < len(str(best)):
            best = p
    return best


def _set_if_empty_or_missing(settings: QSettings, key: str, value: Path | None) -> None:
    if value is None:
        return
    current = str(settings.value(key, "") or "").strip()
    if current and Path(current).exists():
        return
    settings.setValue(key, str(value.resolve()))


def _apply_bundled_backend_defaults() -> None:
    root = _bundle_root()
    candidates = [
        root / "inference_backends",
        root / "dist",
        root / "models",
    ]
    backend_dir = next((p for p in candidates if p.exists() and p.is_dir()), None)
    if backend_dir is None:
        return

    mask_exe = _find_candidate(backend_dir, ("mask2former", "mask", "sam"))
    yolo_exe = _find_candidate(backend_dir, ("yoloe", "yolo", "seg"), exclude={mask_exe} if mask_exe else set())
    yolo_weights = _find_yolo_weights(backend_dir)

    settings = QSettings("PyVisionAnnotator", "PyVisionAnnotator")
    _set_if_empty_or_missing(settings, "autoseg/model_path", mask_exe)
    _set_if_empty_or_missing(settings, "autoseg_yolo/executable", yolo_exe)
    _set_if_empty_or_missing(settings, "autoseg_yolo/model_path", yolo_weights)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PyVisionAnnotator")
    app.setStyle("Fusion")

    _apply_bundled_backend_defaults()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
