"""
utils/build_exe.py — Build Script

Automates the creation of a standalone .exe for PyVisionAnnotator using PyInstaller.
Builds everything into build_output/ as a complete, ready-to-install package.

Usage: python utils/build_exe.py
"""
import sys
import subprocess
import shutil
from pathlib import Path


def _copy_inference_backends(project_root: Path, app_folder: Path) -> Path | None:
    """Copy shared dist backends into packaged app folder, if available."""
    src = project_root.parent / "research" / "others" / "dist"
    if not src.exists() or not src.is_dir():
        print(f"  - Backends folder not found (skip): {src}")
        return None

    dst = app_folder / "inference_backends"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"  ✓ Copied inference backends: {src} -> {dst}")
    return dst


def _copy_llama_cpp_lib(app_folder: Path) -> Path | None:
    """Copy llama-cpp-python native DLL folder into PyInstaller's internal tree."""
    try:
        import llama_cpp
    except Exception as exc:
        print(f"  - llama_cpp not importable (skip native DLL copy): {exc}")
        return None

    src = Path(llama_cpp.__file__).resolve().parent / "lib"
    if not src.exists() or not src.is_dir():
        print(f"  - llama_cpp native lib folder not found (skip): {src}")
        return None

    dst = app_folder / "_internal" / "llama_cpp" / "lib"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"  ✓ Copied llama_cpp native DLLs: {src} -> {dst}")
    return dst


def build():
    # 1. Identify paths
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    entry_point = project_root / "app.py"
    installation_dir = project_root / "build_output"
    app_folder = installation_dir / "PyVisionAnnotator"

    if not entry_point.exists():
        print(f"Error: Could not find entry point at {entry_point}")
        return

    print("--- PyVisionAnnotator Build Tool ---")
    print(f"Project Root:      {project_root}")
    print(f"Entry Point:       {entry_point}")
    print(f"Installation Dir:  {installation_dir}")

    # 2. Clean old build (if exists)
    if installation_dir.exists():
        print(f"\nCleaning old build directory: {installation_dir}")
        shutil.rmtree(installation_dir)
    installation_dir.mkdir(parents=True, exist_ok=True)

    # 3. Check/Install PyInstaller
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("PyInstaller not found. Installing via pip...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        except subprocess.CalledProcessError:
            print("Error: Failed to install PyInstaller.")
            return

    # 4. Construct PyInstaller command with all paths pointing to build_output
    # We use --onedir to produce a folder containing the executable and dependencies
    # We use --noconsole to hide the terminal window
    # We use --distpath to install directly into build_output
    # We use --workpath to keep build artifacts in build_output (not project root)
    # We use --specpath to keep the .spec file in build_output (not project root)

    build_path = installation_dir / "build"
    spec_path = installation_dir / "spec"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(entry_point),
        "--name", "PyVisionAnnotator",
        "--onedir",
        "--noconsole",
        "--clean",
        "--noconfirm",
        "--distpath", str(installation_dir),      # Output exe folder goes here
        "--workpath", str(build_path),
        "--specpath", str(spec_path),
        "--paths", str(project_root),
    ]

    # Ensure PyInstaller bundles modules loaded dynamically at runtime.
    # websocket-client and ollama can be imported indirectly, so add explicit hidden imports.
    hidden = [
        "websocket",
        "websocket._app",
        "websocket._core",
        "websocket._socket",
        "ollama",
        "llama_cpp",
        "llama_cpp.llama_cpp",
        "llama_cpp._ctypes_extensions",
    ]
    for mod in hidden:
        cmd.extend(["--hidden-import", mod])

    cmd.extend(["--collect-binaries", "llama_cpp"])

    # Pre-build sanity checks for runtime dependencies that are imported dynamically.
    try:
        import importlib
        ws_mod = importlib.import_module("websocket")
        has_good_api = hasattr(ws_mod, "create_connection") or hasattr(ws_mod, "WebSocket")
        if not has_good_api:
            print("WARNING: 'websocket' module found but it does not look like 'websocket-client'.")
            print("Please install 'websocket-client' in the build environment: python -m pip install websocket-client")
    except ModuleNotFoundError:
        print("WARNING: 'websocket-client' not found in build environment. Installing it is recommended.")

    try:
        import importlib
        ollama_mod = importlib.import_module("ollama")
        has_client = hasattr(ollama_mod, "Client")
        if not has_client:
            print("WARNING: 'ollama' module found but Client API is missing.")
            print("Please install/upgrade it in the build environment: python -m pip install -U ollama")
    except ModuleNotFoundError:
        print("WARNING: 'ollama' not found in build environment. Install it before build: python -m pip install ollama")

    print("\nStarting build process... (this may take a minute)")
    print("Executing:", " ".join(cmd))

    # 5. Execute PyInstaller
    try:
        result = subprocess.run(cmd, cwd=project_root)

        if result.returncode != 0:
            print("\nBuild failed. Check output above for errors.")
            return

        # 6. Copy supporting files (README, requirements, etc.)
        print("\nCopying supporting files...")
        files_to_copy = [
            "requirements.txt",
            "feauters of the application.md",
        ]

        for file in files_to_copy:
            src = project_root / file
            if src.exists():
                dst = installation_dir / file
                shutil.copy2(src, dst)
                print(f"  ✓ Copied {file}")

        # 6b. Copy external model/runtime backends (mask2former / yoloe dist)
        print("\nCopying external inference backends...")
        backends_path = _copy_inference_backends(project_root, app_folder)

        # 6c. Copy llama-cpp-python native DLLs.
        print("\nCopying llama_cpp native runtime files...")
        llama_cpp_lib_path = _copy_llama_cpp_lib(app_folder)

        # 7. Create a README for the installation
        readme_content = """# PyVisionAnnotator - Installation

This folder contains a complete, standalone installation of PyVisionAnnotator.

## Running the Application

1. Navigate to this folder in Windows Explorer
2. Open the `PyVisionAnnotator` subfolder
3. Double-click `PyVisionAnnotator.exe` to launch the application

## System Requirements

- Windows 7 or later (64-bit)
- At least 4GB RAM recommended
- No additional software installation needed

## Features

- Image annotation with bounding boxes and polygons
- AutoSeg integration for automatic object segmentation
- JSON export + COCO/YOLO template export of annotations
- Image brightness/contrast/gamma adjustments
- Crosshair cursor for precise alignment
- Bundled inference backends auto-detected at first run (if packaged in inference_backends/)

## Folder Structure

- `PyVisionAnnotator/` - Main application folder with executable
- `requirements.txt` - Python package dependencies (reference only)
- `feauters of the application.md` - Detailed feature documentation

## Troubleshooting

If the application fails to start:
1. Ensure you're running it from the PyVisionAnnotator subfolder
2. Check that your GPU drivers are up to date
3. Try running from Command Prompt to see error messages

For more help, see the feature documentation file.
"""
        readme_path = installation_dir / "README.txt"
        readme_path.write_text(readme_content, encoding="utf-8")
        print(f"  ✓ Created README.txt")

        # 8. Report success
        exe_path = app_folder / "PyVisionAnnotator.exe"

        print("\n" + "="*50)
        print("BUILD SUCCESSFUL!")
        print("="*50)
        print(f"\n✓ Installation folder: {installation_dir}")
        print(f"✓ Executable:         {exe_path}")
        if backends_path is not None:
            print(f"✓ Backends folder:    {backends_path}")
        if llama_cpp_lib_path is not None:
            print(f"✓ llama_cpp DLLs:     {llama_cpp_lib_path}")
        print(f"\nTo run the application:")
        print(f"  1. Open: {installation_dir}")
        print(f"  2. Open: PyVisionAnnotator folder")
        print(f"  3. Double-click: PyVisionAnnotator.exe")
        print(f"\nThe application is now ready to distribute or install.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    build()

