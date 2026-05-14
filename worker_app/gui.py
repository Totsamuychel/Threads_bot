"""CustomTkinter GUI for the Threads Worker app."""

import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Optional

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    raise SystemExit("customtkinter not installed. Run: pip install customtkinter")

from worker_app import config as cfg
from worker_app import ollama_manager
from worker_app.worker_client import WorkerClient

# Status colours
_STATUS_COLOR = {
    "disconnected": "#888888",
    "connecting":   "#f0a500",
    "connected":    "#2ecc71",
    "reconnecting": "#f0a500",
    "error":        "#e74c3c",
}
_STATUS_LABEL = {
    "disconnected": "Disconnected",
    "connecting":   "Connecting…",
    "connected":    "Connected",
    "reconnecting": "Reconnecting…",
    "error":        "Error",
}

_LOG_MAX = 500  # max log lines kept in memory


class WorkerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Threads Worker")
        self.geometry("680x560")
        self.minsize(520, 460)
        self.resizable(True, True)

        self._client: Optional[WorkerClient] = None
        self._status = "disconnected"
        self._log_queue: queue.Queue = queue.Queue()
        self._after_id = None

        self._conf = cfg.load()
        self._build_ui()
        self._restore_config()
        self._poll_log()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Header ─────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, corner_radius=0, fg_color=("#1a1a2e", "#1a1a2e"))
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="🧵 Threads Worker", font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#7c8cf8",
        ).grid(row=0, column=0, padx=16, pady=12)

        self._status_dot = ctk.CTkLabel(
            hdr, text="●", font=ctk.CTkFont(size=22),
            text_color=_STATUS_COLOR["disconnected"],
        )
        self._status_dot.grid(row=0, column=1, sticky="e", padx=4)

        self._status_lbl = ctk.CTkLabel(
            hdr, text="Disconnected", font=ctk.CTkFont(size=13),
            text_color="#aaaaaa",
        )
        self._status_lbl.grid(row=0, column=2, sticky="e", padx=(0, 16))

        # ── Connection settings ─────────────────────────────────────────
        conn = ctk.CTkFrame(self)
        conn.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 4))
        conn.grid_columnconfigure(1, weight=1)
        conn.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(conn, text="Server URL", width=90).grid(row=0, column=0, padx=(12, 4), pady=8, sticky="w")
        self._entry_url = ctk.CTkEntry(conn, placeholder_text="http://192.168.1.100:8000")
        self._entry_url.grid(row=0, column=1, padx=4, pady=8, sticky="ew")

        ctk.CTkLabel(conn, text="Worker name", width=100).grid(row=0, column=2, padx=(12, 4), pady=8, sticky="w")
        self._entry_name = ctk.CTkEntry(conn, placeholder_text="my-gpu-pc")
        self._entry_name.grid(row=0, column=3, padx=4, pady=8, sticky="ew")

        ctk.CTkLabel(conn, text="Ollama port", width=90).grid(row=1, column=0, padx=(12, 4), pady=(0, 8), sticky="w")
        self._entry_port = ctk.CTkEntry(conn, placeholder_text="11434", width=100)
        self._entry_port.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="w")

        self._btn_connect = ctk.CTkButton(
            conn, text="Connect", width=110, command=self._on_connect,
            fg_color="#4a56e2", hover_color="#3a46d2",
        )
        self._btn_connect.grid(row=1, column=2, columnspan=2, padx=(12, 4), pady=(0, 8), sticky="e")

        # ── Tabs ────────────────────────────────────────────────────────
        tabs = ctk.CTkTabview(self)
        tabs.grid(row=2, column=0, sticky="nsew", padx=16, pady=(4, 8))
        tabs.add("Log")
        tabs.add("Ollama")

        # Log tab
        log_tab = tabs.tab("Log")
        log_tab.grid_columnconfigure(0, weight=1)
        log_tab.grid_rowconfigure(0, weight=1)

        self._log_box = ctk.CTkTextbox(log_tab, state="disabled", wrap="word", font=ctk.CTkFont(family="Consolas", size=11))
        self._log_box.grid(row=0, column=0, sticky="nsew")

        # Ollama tab
        oll_tab = tabs.tab("Ollama")
        oll_tab.grid_columnconfigure(0, weight=1)
        oll_tab.grid_rowconfigure(2, weight=1)

        # Status row
        sf = ctk.CTkFrame(oll_tab, fg_color="transparent")
        sf.grid(row=0, column=0, sticky="ew", pady=(8, 4))
        sf.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(sf, text="Ollama status:").grid(row=0, column=0, padx=(0, 8))
        self._ollama_status_lbl = ctk.CTkLabel(sf, text="Checking…", text_color="#aaaaaa")
        self._ollama_status_lbl.grid(row=0, column=1, sticky="w")

        btn_frame = ctk.CTkFrame(oll_tab, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", pady=4)

        ctk.CTkButton(btn_frame, text="Install Ollama", width=140, command=self._install_ollama).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="Check status", width=120, command=self._check_ollama, fg_color="#555", hover_color="#444").pack(side="left", padx=(0, 8))

        # Manual pull
        pull_f = ctk.CTkFrame(oll_tab, fg_color="transparent")
        pull_f.grid(row=2, column=0, sticky="ew", pady=4)
        pull_f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(pull_f, text="Pull model manually:").grid(row=0, column=0, columnspan=2, sticky="w", pady=(4, 2))
        self._entry_model = ctk.CTkEntry(pull_f, placeholder_text="e.g. llama3.2 or qwen2.5vl:7b")
        self._entry_model.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(pull_f, text="Pull", width=80, command=self._manual_pull).grid(row=1, column=1)

        # Models list
        ctk.CTkLabel(oll_tab, text="Available models:").grid(row=3, column=0, sticky="w", pady=(8, 2))
        self._models_box = ctk.CTkTextbox(oll_tab, height=120, state="disabled", font=ctk.CTkFont(family="Consolas", size=11))
        self._models_box.grid(row=4, column=0, sticky="ew")

        # Refresh ollama status every 10s
        self._check_ollama()
        self._schedule_ollama_refresh()

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def _restore_config(self):
        self._entry_url.insert(0, self._conf.get("server_url", ""))
        self._entry_name.insert(0, self._conf.get("worker_name", ""))
        self._entry_port.insert(0, self._conf.get("ollama_port", "11434"))

    def _save_config(self):
        cfg.save({
            "server_url": self._entry_url.get().strip(),
            "worker_name": self._entry_name.get().strip(),
            "ollama_port": self._entry_port.get().strip(),
        })

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _on_connect(self):
        if self._client and self._status == "connected":
            self._client.stop()
            self._client = None
            self._set_status("disconnected")
            self._btn_connect.configure(text="Connect")
            self._log("Disconnected")
            return

        url = self._entry_url.get().strip()
        name = self._entry_name.get().strip()
        port_str = self._entry_port.get().strip() or "11434"

        if not url or not name:
            messagebox.showerror("Error", "Server URL and worker name are required")
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Ollama port must be a number")
            return

        self._save_config()
        self._btn_connect.configure(text="Connecting…", state="disabled")
        self._set_status("connecting")

        def _do():
            client = WorkerClient(
                server_url=url,
                worker_name=name,
                ollama_port=port,
                log_cb=self._log,
                status_cb=self._set_status,
            )
            ok = client.start()
            if ok:
                self._client = client
                self.after(0, lambda: self._btn_connect.configure(text="Disconnect", state="normal"))
            else:
                self.after(0, lambda: self._btn_connect.configure(text="Connect", state="normal"))

        threading.Thread(target=_do, daemon=True).start()

    # ------------------------------------------------------------------
    # Ollama tab
    # ------------------------------------------------------------------

    def _check_ollama(self):
        def _do():
            installed = ollama_manager.is_installed()
            running = ollama_manager.is_running()
            models = ollama_manager.list_models() if running else []
            status = "Not installed"
            color = "#e74c3c"
            if installed and running:
                status = f"Running — {len(models)} model(s) loaded"
                color = "#2ecc71"
            elif installed:
                status = "Installed but not running"
                color = "#f0a500"

            self.after(0, lambda: self._ollama_status_lbl.configure(text=status, text_color=color))
            self.after(0, lambda: self._refresh_models_list(models))

        threading.Thread(target=_do, daemon=True).start()

    def _refresh_models_list(self, models: list):
        self._models_box.configure(state="normal")
        self._models_box.delete("0.0", "end")
        if models:
            self._models_box.insert("end", "\n".join(models))
        else:
            self._models_box.insert("end", "(none)")
        self._models_box.configure(state="disabled")

    def _schedule_ollama_refresh(self):
        self.after(10_000, lambda: (self._check_ollama(), self._schedule_ollama_refresh()))

    def _install_ollama(self):
        self._log("Starting Ollama installation…")
        threading.Thread(target=lambda: ollama_manager.install(log_cb=self._log), daemon=True).start()

    def _manual_pull(self):
        model = self._entry_model.get().strip()
        if not model:
            return
        self._log(f"Pulling {model}…")

        def _do():
            if not ollama_manager.is_running():
                self._log("Ollama is not running — starting…")
                ollama_manager.start_ollama(log_cb=self._log)
            ollama_manager.pull_model(model, log_cb=self._log)
            self._check_ollama()

        threading.Thread(target=_do, daemon=True).start()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self._log_queue.put(f"[{ts}] {msg}")

    def _poll_log(self):
        try:
            while True:
                line = self._log_queue.get_nowait()
                self._log_box.configure(state="normal")
                self._log_box.insert("end", line + "\n")
                self._log_box.see("end")
                # Trim if too long
                lines = int(self._log_box.index("end-1c").split(".")[0])
                if lines > _LOG_MAX:
                    self._log_box.delete("1.0", f"{lines - _LOG_MAX}.0")
                self._log_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(200, self._poll_log)

    # ------------------------------------------------------------------
    # Status indicator
    # ------------------------------------------------------------------

    def _set_status(self, status: str):
        self._status = status
        color = _STATUS_COLOR.get(status, "#888888")
        label = _STATUS_LABEL.get(status, status.capitalize())
        self.after(0, lambda: (
            self._status_dot.configure(text_color=color),
            self._status_lbl.configure(text=label),
        ))

    # ------------------------------------------------------------------
    def _on_close(self):
        if self._client:
            self._client.stop()
        self.destroy()
