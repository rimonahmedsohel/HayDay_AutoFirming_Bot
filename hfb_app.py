"""
HFB — Hay Day Auto-Farming Bot
Standalone GUI Application
"""
import tkinter as tk
from tkinter import scrolledtext
import threading
import subprocess
import sys
import io
import os
import time

# ── Resolve bundled resource paths ──────────────────────────────────
from adb_path import get_adb_path, CREATE_NO_WINDOW

ADB = get_adb_path()
DEVICE = "127.0.0.1:7555"

# ── Application version ────────────────────────────────────────────
VERSION = "1.0.0"


class StdoutRedirector(io.TextIOBase):
    """Redirect all print() output to a tkinter Text widget."""

    def __init__(self, text_widget, app):
        self.text_widget = text_widget
        self.app = app

    def write(self, message):
        if message and message.strip():
            # Schedule GUI update on the main thread
            self.app.after(0, self._append, message)
        return len(message) if message else 0

    def _append(self, message):
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, message + "\n")
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass


class HFBApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(f"HFB — Hay Day Auto-Farming Bot  v{VERSION}")
        self.geometry("900x620")
        self.resizable(True, True)
        self.configure(bg="#1a1a2e")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.bot_thread = None
        self.is_running = False

        self._build_ui()
        self._redirect_stdout()
        self._log("HFB Application started. Click [▶ Start Bot] to begin.")

    # ── UI Construction ─────────────────────────────────────────────
    def _build_ui(self):
        # Title bar
        title_frame = tk.Frame(self, bg="#16213e", pady=12)
        title_frame.pack(fill="x")

        tk.Label(
            title_frame,
            text="🌾  HFB — Hay Day Auto-Farming Bot",
            font=("Segoe UI", 18, "bold"),
            fg="#e94560",
            bg="#16213e",
        ).pack(side="left", padx=20)

        tk.Label(
            title_frame,
            text=f"v{VERSION}",
            font=("Segoe UI", 10),
            fg="#7f8c8d",
            bg="#16213e",
        ).pack(side="right", padx=20)

        # Status bar
        status_frame = tk.Frame(self, bg="#0f3460", pady=8)
        status_frame.pack(fill="x")

        self.status_dot = tk.Label(
            status_frame,
            text="●",
            font=("Segoe UI", 14),
            fg="#95a5a6",
            bg="#0f3460",
        )
        self.status_dot.pack(side="left", padx=(20, 8))

        self.status_label = tk.Label(
            status_frame,
            text="Idle — Waiting for user",
            font=("Segoe UI", 11),
            fg="#ecf0f1",
            bg="#0f3460",
        )
        self.status_label.pack(side="left")

        # Button frame
        btn_frame = tk.Frame(self, bg="#1a1a2e", pady=10)
        btn_frame.pack(fill="x")

        self.start_btn = tk.Button(
            btn_frame,
            text="▶  Start Bot",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#27ae60",
            activebackground="#2ecc71",
            activeforeground="#ffffff",
            relief="flat",
            padx=30,
            pady=8,
            cursor="hand2",
            command=self._start_bot,
        )
        self.start_btn.pack(side="left", padx=(20, 10))

        self.stop_btn = tk.Button(
            btn_frame,
            text="■  Stop Bot",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#c0392b",
            activebackground="#e74c3c",
            activeforeground="#ffffff",
            relief="flat",
            padx=30,
            pady=8,
            cursor="hand2",
            state="disabled",
            command=self._stop_bot,
        )
        self.stop_btn.pack(side="left", padx=10)

        self.clear_btn = tk.Button(
            btn_frame,
            text="🗑  Clear Log",
            font=("Segoe UI", 10),
            fg="#bdc3c7",
            bg="#2c3e50",
            activebackground="#34495e",
            activeforeground="#ecf0f1",
            relief="flat",
            padx=15,
            pady=6,
            cursor="hand2",
            command=self._clear_log,
        )
        self.clear_btn.pack(side="right", padx=20)

        # Log panel
        log_label_frame = tk.Frame(self, bg="#1a1a2e")
        log_label_frame.pack(fill="x", padx=20, pady=(5, 0))
        tk.Label(
            log_label_frame,
            text="📋 Live Log Output",
            font=("Segoe UI", 10, "bold"),
            fg="#7f8c8d",
            bg="#1a1a2e",
        ).pack(anchor="w")

        self.log_text = scrolledtext.ScrolledText(
            self,
            wrap="word",
            font=("Consolas", 10),
            bg="#0d1117",
            fg="#c9d1d9",
            insertbackground="#c9d1d9",
            selectbackground="#264f78",
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        # Footer
        footer = tk.Frame(self, bg="#16213e", pady=5)
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text="HFB • ADB Target: 127.0.0.1:7555 (MuMu Player)",
            font=("Segoe UI", 8),
            fg="#7f8c8d",
            bg="#16213e",
        ).pack()

    # ── stdout redirect ─────────────────────────────────────────────
    def _redirect_stdout(self):
        sys.stdout = StdoutRedirector(self.log_text, self)
        sys.stderr = StdoutRedirector(self.log_text, self)

    # ── Logging helper ──────────────────────────────────────────────
    def _log(self, message):
        self.log_text.configure(state="normal")
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    # ── Status updates ──────────────────────────────────────────────
    def _set_status(self, text, color="#95a5a6"):
        self.status_dot.configure(fg=color)
        self.status_label.configure(text=text)

    # ── Bot lifecycle ───────────────────────────────────────────────
    def _start_bot(self):
        if self.is_running:
            return

        self.is_running = True
        self.start_btn.configure(state="disabled", bg="#7f8c8d")
        self.stop_btn.configure(state="normal", bg="#c0392b")
        self._set_status("Connecting to MuMu Player…", "#f39c12")

        self.bot_thread = threading.Thread(target=self._bot_worker, daemon=True)
        self.bot_thread.start()

    def _stop_bot(self):
        if not self.is_running:
            return

        self._log("⛔ Stop signal sent! Waiting for current operation to finish…")
        self._set_status("Stopping…", "#e74c3c")

        # Tell the bot to stop
        import start
        start.set_running(False)
        self.is_running = False

        self.start_btn.configure(state="normal", bg="#27ae60")
        self.stop_btn.configure(state="disabled", bg="#7f8c8d")

    def _bot_worker(self):
        """Runs in a background thread."""
        try:
            # Step 1: Connect ADB
            self._log("Connecting ADB to MuMu Player at 127.0.0.1:7555…")
            result = subprocess.run(
                [ADB, "connect", DEVICE],
                capture_output=True, text=True,
                creationflags=CREATE_NO_WINDOW,
            )
            self._log(f"ADB: {result.stdout.strip()}")

            # Disable ADB auth prompts
            subprocess.run(
                [ADB, "-s", DEVICE, "shell", "settings", "put", "global", "adb_enabled", "1"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )

            self.after(0, self._set_status, "Bot running — farming in progress", "#2ecc71")

            # Step 2: Start the master loop
            import start
            start.set_running(True)
            start.run_master_loop()

        except Exception as e:
            self._log(f"❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            self.after(0, self._on_bot_stopped)

    def _on_bot_stopped(self):
        self._set_status("Idle — Bot stopped", "#95a5a6")
        self._log("Bot has stopped.")
        self.start_btn.configure(state="normal", bg="#27ae60")
        self.stop_btn.configure(state="disabled", bg="#7f8c8d")

    # ── Window close ────────────────────────────────────────────────
    def _on_close(self):
        if self.is_running:
            import start
            start.set_running(False)
            self.is_running = False
            self._log("Shutting down… waiting for bot to stop.")
            # Give the bot thread a moment to wind down
            self.after(1500, self.destroy)
        else:
            self.destroy()


if __name__ == "__main__":
    app = HFBApp()
    app.mainloop()
