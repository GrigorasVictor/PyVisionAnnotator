import os
import subprocess
import sys

# Change this variable to the name of the python script you want to convert to an executable
TARGET_SCRIPT = "mask2former.py"

def create_executable(script_name):
    # Check if the script exists
    if not os.path.exists(script_name):
        print(f"Error: The file '{script_name}' does not exist in the current directory.")
        return

    print(f"Creating executable for: {script_name}")
    
    # Construct the PyInstaller command
    # --onefile: Create a single executable file
    # --clean: Clean PyInstaller cache and remove temporary files before building
    # --noupx: Disable UPX compression to improve startup time (avoids decompression overhead)
    # Note: Switching from --onefile to --onedir (folder output) would significantly improve startup time further
    # Note: Removed --optimize 2 because 'transformers' library requires docstrings to function correctly.
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onedir",
        "--clean",
        "--noupx",
        "--collect-data",
        "clip",
        script_name
    ]

    try:
        # Run PyInstaller
        subprocess.check_call(command)
        print(f"\nSuccessfully created executable for {script_name}")
        print(f"You can find the executable in the 'dist' folder.")
        
    except subprocess.CalledProcessError as e:
        print(f"\nError occurred while creating executable: {e}")
    except FileNotFoundError:
        print("\nError: PyInstaller is not installed or not found in PATH.")
        print("Please install it using: pip install pyinstaller")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)

    target_script = sys.argv[1] if len(sys.argv) > 1 else TARGET_SCRIPT
    create_executable(target_script)
