"""HTTP client that registers and sends heartbeats to the admin server."""

import logging
import platform
import socket
import threading
import time
from typing import Callable, Optional

import requests

from worker_app import ollama_manager

logger = logging.getLogger(__name__)

_HEARTBEAT_INTERVAL = 15  # seconds


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class WorkerClient:
    """Manages registration + heartbeat loop with the admin server."""

    def __init__(
        self,
        server_url: str,
        worker_name: str,
        ollama_port: int = 11434,
        log_cb: Optional[Callable[[str], None]] = None,
        status_cb: Optional[Callable[[str], None]] = None,
    ):
        self.server_url = server_url.rstrip("/")
        self.worker_name = worker_name
        self.ollama_port = ollama_port
        self.log_cb = log_cb
        self.status_cb = status_cb

        self._worker_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    def _log(self, msg: str):
        logger.info(msg)
        if self.log_cb:
            self.log_cb(msg)

    def _set_status(self, status: str):
        if self.status_cb:
            self.status_cb(status)

    # ------------------------------------------------------------------
    def start(self) -> bool:
        """Register and start heartbeat loop. Returns True if connected."""
        self._log(f"Connecting to {self.server_url}…")
        self._set_status("connecting")
        worker_id = self._register()
        if worker_id is None:
            self._set_status("error")
            return False

        self._worker_id = worker_id
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        self._set_status("connected")
        return True

    def stop(self):
        """Stop the heartbeat loop."""
        self._stop_event.set()

    @property
    def worker_id(self) -> Optional[int]:
        return self._worker_id

    # ------------------------------------------------------------------
    def _register(self) -> Optional[int]:
        host = _get_local_ip()
        payload = {
            "name": self.worker_name,
            "host": host,
            "port": self.ollama_port,
            "api_type": "ollama",
        }
        try:
            r = requests.post(
                f"{self.server_url}/api/workers/register",
                json=payload,
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            wid = data["id"]
            self._log(f"Registered as worker #{wid} — {self.worker_name} @ {host}:{self.ollama_port}")
            return wid
        except requests.RequestException as e:
            msg = str(e)
            if hasattr(e, "response") and e.response is not None:
                msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            self._log(f"Registration failed: {msg}")
            return None

    def _heartbeat_loop(self):
        fail_count = 0
        while not self._stop_event.is_set():
            ok, to_pull = self._send_heartbeat()
            if ok:
                fail_count = 0
                if to_pull:
                    self._pull_models(to_pull)
            else:
                fail_count += 1
                self._set_status("reconnecting")
                if fail_count >= 5:
                    self._log("Too many failures — re-registering…")
                    new_id = self._register()
                    if new_id:
                        self._worker_id = new_id
                        fail_count = 0
                        self._set_status("connected")
                    else:
                        self._set_status("error")

            self._stop_event.wait(_HEARTBEAT_INTERVAL)

    def _send_heartbeat(self):
        """Send heartbeat. Returns (success, models_to_pull)."""
        import shutil
        import subprocess

        gpu = {}
        try:
            nvidia = shutil.which("nvidia-smi")
            if nvidia:
                out = subprocess.check_output(
                    [nvidia, "--query-gpu=name,memory.total,memory.used,memory.free",
                     "--format=csv,noheader,nounits"],
                    timeout=5, text=True,
                )
                parts = [p.strip() for p in out.strip().split(",")]
                if len(parts) >= 4:
                    gpu = {
                        "gpu_name": parts[0],
                        "vram_total_mb": int(float(parts[1])),
                        "vram_used_mb": int(float(parts[2])),
                        "vram_free_mb": int(float(parts[3])),
                    }
        except Exception:
            pass

        ram = {}
        try:
            import psutil
            mem = psutil.virtual_memory()
            ram = {
                "ram_total_mb": int(mem.total / 1024 / 1024),
                "ram_used_mb": int(mem.used / 1024 / 1024),
                "ram_free_mb": int(mem.available / 1024 / 1024),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
            }
        except ImportError:
            pass

        models = ollama_manager.list_models()
        payload = {**gpu, **ram, "models_available": models}

        try:
            r = requests.post(
                f"{self.server_url}/api/workers/{self._worker_id}/heartbeat",
                json=payload,
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            to_pull = data.get("required_models", [])
            self._log(
                f"Heartbeat OK | models: {len(models)}"
                + (f" | GPU: {gpu.get('gpu_name','?')} {gpu.get('vram_used_mb','?')}/{gpu.get('vram_total_mb','?')}MB" if gpu else "")
            )
            return True, to_pull
        except requests.RequestException as e:
            self._log(f"Heartbeat failed: {e}")
            return False, []

    def _pull_models(self, models: list):
        """Pull missing models in a background thread."""
        def _do():
            for m in models:
                self._log(f"Server requires model: {m} — pulling…")
                ok = ollama_manager.pull_model(m, log_cb=self._log)
                if ok:
                    self._log(f"Model {m} ready")
                else:
                    self._log(f"Failed to pull {m}")

        threading.Thread(target=_do, daemon=True).start()
