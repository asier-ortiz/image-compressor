#!/usr/bin/env python3
"""Build script — generates a standalone executable for the current platform."""

import platform
import subprocess
import sys

APP_NAME = "Compresor de Imágenes"
ICON = "icon.ico" if platform.system() == "Windows" else "icon.png"
SEPARATOR = ";" if platform.system() == "Windows" else ":"

cmd = [
    sys.executable, "-m", "PyInstaller",
    "-y",
    "--onefile",
    "--windowed",
    "--name", APP_NAME,
    "--icon", ICON,
    "--add-data", f"icon.png{SEPARATOR}.",
    "--add-data", f"icon.ico{SEPARATOR}.",
    "app.py",
]

print(f"Building for {platform.system()}...")
print(f"  Command: {' '.join(cmd)}")
subprocess.run(cmd, check=True)
print(f"\nDone! Executable is in dist/")
