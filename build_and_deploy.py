"""
Build and deploy script for tdp_engine using PyInstaller's Python API.
This script will:
- Build the project into a single executable using PyInstaller
- Copy all required assets and resources
- Log progress and errors
"""
import os
import shutil
import sys
import logging
from PyInstaller.__main__ import run as pyinstaller_run

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger("build_and_deploy")
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, "main.py")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# List of asset folders to copy
ASSET_FOLDERS = [    
    "resources",
]

# PyInstaller options
USE_ONEFILE = False  # Set to False to build --onedir for testing

PYINSTALLER_OPTS = [
    MAIN_SCRIPT,
    ("--onefile" if USE_ONEFILE else "--onedir"),
    #"--windowed",
    f"--additional-hooks-dir={PROJECT_ROOT}",
    f"--distpath={DIST_DIR}",
    f"--workpath={BUILD_DIR}",
    #f"--add-data={ASSETS_DIR}{os.pathsep}assets",
    # Treat SDL runtime DLLs as binaries so PyInstaller handles them as native libs.
    # Use --add-binary for the folder containing the SDL DLLs.
    f"--add-binary=resources/sdl3{os.pathsep}sdl3/bin",
    f"--add-binary=/usr/lib/x86_64-linux-gnu/libpython3.12.so.1.0:_internal"
    # Useful debug switch: disable UPX to avoid potential DLL performance/corruption issues
    # "--noupx",
]

def copy_resources():
    """Copy resource folders to the dist directory."""
    for folder in ASSET_FOLDERS:
        src = os.path.join(PROJECT_ROOT, folder)
        # Place resources next to the internal in the onedir layout
        dst = os.path.join(DIST_DIR, "main", "_internal", folder)
        if os.path.exists(src):
            try:
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                logger.info(f"Copied {folder} to dist directory.")
            except Exception as e:
                logger.error(f"Failed to copy {folder}: {e}")
        else:
            logger.warning(f"Asset folder {folder} does not exist.")

def build_executable():
    """Run PyInstaller to build the executable."""
    logger.info("Starting PyInstaller build...")
    try:
        pyinstaller_run(PYINSTALLER_OPTS)
        logger.info("PyInstaller build completed.")
    except Exception as e:
        logger.error(f"PyInstaller build failed: {e}")
        sys.exit(1)

def main():
    build_executable()
    copy_resources()
    logger.info("Build and deploy completed successfully.")

if __name__ == "__main__":
    main()