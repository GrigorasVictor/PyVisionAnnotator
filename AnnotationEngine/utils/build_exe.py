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

    # Ensure PyInstaller bundles websocket-client: dynamic imports may be missed.
    # Add common websocket-client modules as hidden imports so the built exe contains them.
    hidden = [
        "websocket",
        "websocket._app",
        "websocket._core",
        "websocket._socket",
    ]
    for mod in hidden:
        cmd.extend(["--hidden-import", mod])

    # Pre-build sanity check: ensure the environment has websocket-client (not a conflicting
    # package named 'websocket' with different API). This helps avoid runtime failures in the
    # packaged app where an incompatible websocket module gets bundled.
    try:
        import importlib
        ws_mod = importlib.import_module("websocket")
        has_good_api = hasattr(ws_mod, "create_connection") or hasattr(ws_mod, "WebSocket")
        if not has_good_api:
            print("WARNING: 'websocket' module found but it does not look like 'websocket-client'.")
            print("Please install 'websocket-client' in the build environment: python -m pip install websocket-client")
    except ModuleNotFoundError:
        print("WARNING: 'websocket-client' not found in build environment. Installing it is recommended.")

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
        print(f"\nTo run the application:")
        print(f"  1. Open: {installation_dir}")
        print(f"  2. Open: PyVisionAnnotator folder")
        print(f"  3. Double-click: PyVisionAnnotator.exe")
        print(f"\nThe application is now ready to distribute or install.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    build()

