"""Ollama installation and model management for the worker app."""

import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

OLLAMA_WIN_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_LIN_URL = "https://ollama.ai/install.sh"
OLLAMA_API = "http://localhost:11434"


def _is_windows() -> bool:
    return platform.system() == "Windows"


def is_installed() -> bool:
    """Return True if the ollama binary is on PATH or in default install location."""
    if shutil.which("ollama"):
        return True
    if _is_windows():
        local_app = os.environ.get("LOCALAPPDATA", "")
        exe = Path(local_app) / "Programs" / "Ollama" / "ollama.exe"
        return exe.exists()
    return False


def get_ollama_exe() -> str:
    """Return full path to ollama executable."""
    found = shutil.which("ollama")
    if found:
        return found
    if _is_windows():
        local_app = os.environ.get("LOCALAPPDATA", "")
        exe = Path(local_app) / "Programs" / "Ollama" / "ollama.exe"
        if exe.exists():
            return str(exe)
    raise FileNotFoundError("ollama not found")


def is_running(timeout: int = 3) -> bool:
    """Return True if local Ollama API is responding."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def start_ollama(log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """Start ollama serve in the background. Returns True if started."""
    try:
        exe = get_ollama_exe()
    except FileNotFoundError:
        return False

    def _log(msg: str):
        logger.info(msg)
        if log_cb:
            log_cb(msg)

    if is_running():
        _log("Ollama already running")
        return True

    _log("Starting ollama serve…")
    try:
        if _is_windows():
            subprocess.Popen(
                [exe, "serve"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                [exe, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        # Wait up to 10s
        import time
        for _ in range(20):
            time.sleep(0.5)
            if is_running():
                _log("Ollama started")
                return True
        _log("Ollama did not respond after 10s")
        return False
    except Exception as e:
        _log(f"Failed to start ollama: {e}")
        return False


def install(log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """Download and silently install Ollama. Returns True on success."""
    def _log(msg: str):
        logger.info(msg)
        if log_cb:
            log_cb(msg)

    if is_installed():
        _log("Ollama already installed")
        return True

    if _is_windows():
        return _install_windows(_log)
    else:
        return _install_linux(_log)


def _install_windows(log_cb: Callable[[str], None]) -> bool:
    log_cb("Downloading Ollama installer…")
    try:
        tmp = tempfile.mktemp(suffix=".exe")
        urllib.request.urlretrieve(OLLAMA_WIN_URL, tmp)
        log_cb("Running installer (silent)…")
        result = subprocess.run(
            [tmp, "/S"],
            timeout=120,
            capture_output=True,
        )
        os.unlink(tmp)
        if result.returncode == 0:
            log_cb("Ollama installed successfully")
            return True
        else:
            log_cb(f"Installer returned code {result.returncode}")
            return False
    except Exception as e:
        log_cb(f"Install error: {e}")
        return False


def _install_linux(log_cb: Callable[[str], None]) -> bool:
    log_cb("Installing Ollama via install script…")
    try:
        tmp = tempfile.mktemp(suffix=".sh")
        urllib.request.urlretrieve(OLLAMA_LIN_URL, tmp)
        os.chmod(tmp, 0o755)
        result = subprocess.run(["bash", tmp], timeout=120, capture_output=True, text=True)
        os.unlink(tmp)
        if result.returncode == 0:
            log_cb("Ollama installed successfully")
            return True
        log_cb(f"Install error: {result.stderr[:300]}")
        return False
    except Exception as e:
        log_cb(f"Install error: {e}")
        return False


def list_models() -> List[str]:
    """Return list of currently available local model names."""
    import json
    try:
        with urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=5) as r:
            data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def pull_model(name: str, log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """Pull a model via ollama CLI. Streams progress to log_cb. Returns True on success."""
    def _log(msg: str):
        logger.info(msg)
        if log_cb:
            log_cb(msg)

    _log(f"Pulling model {name}…")
    try:
        exe = get_ollama_exe()
        proc = subprocess.Popen(
            [exe, "pull", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                _log(f"  {line}")
        proc.wait()
        if proc.returncode == 0:
            _log(f"Model {name} ready")
            return True
        _log(f"Pull failed (code {proc.returncode})")
        return False
    except FileNotFoundError:
        _log("ollama not found — install it first")
        return False
    except Exception as e:
        _log(f"Pull error: {e}")
        return False
