"""
Build script for ThreadsWorker.exe

Run from the repo root:
    python worker_app/build_exe.py

Requirements:
    pip install pyinstaller customtkinter psutil requests
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = Path(__file__).resolve().parent / "threads_worker.spec"


def main():
    print("Building ThreadsWorker.exe…")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC), "--distpath", str(ROOT / "worker_app" / "dist")],
        cwd=str(ROOT / "worker_app"),
    )
    if result.returncode == 0:
        exe = ROOT / "worker_app" / "dist" / "ThreadsWorker.exe"
        print(f"\nSuccess! EXE: {exe}")
    else:
        print("\nBuild failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
