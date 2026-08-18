"""
Jarvis Voice Assistant — Desktop App (GUI)
-------------------------------------------
A futuristic "sci-fi HUD" interface inspired by eDEX-UI / TRON-style terminal
dashboards: dark background, glowing cyan accents, HUD corner brackets, a
live animated radar that reflects what the assistant is doing (idle /
listening / thinking / speaking), a live clock, and a terminal-style
conversation log.

All the actual logic (voice recognition, commands, memory) still lives in
assistant.py — this file is just the window wrapped around it.

Run this with run_gui.bat, or turn it into a real standalone .exe with
build_exe.bat (see README.md).
"""

import math
import threading
import datetime
import json
import tkinter as tk
from tkinter import scrolledtext

import assistant

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None

# ---------------------------------------------------------------------------
# HUD color palette (eDEX-UI / TRON style)
# ---------------------------------------------------------------------------
BG = "#060a10"          # near-black background
PANEL = "#0b131d"        # slightly lighter panel background
BORDER = "#0e3a4a"       # dim cyan border / grid lines
CYAN = "#28e8ff"         # primary accent
CYAN_DIM = "#0f6b80"
GREEN = "#33ff9c"        # listening / active
AMBER = "#ffc857"        # thinking / processing
RED = "#ff4d5e"          # offline / error
TEXT = "#cdf3ff"
DIM = "#4c7080"
FONT_MONO = "Consolas"


def spaced(text):
    """Adds letter-spacing feel to headers, e.g. 'JARVIS' -> 'J A R V I S'."""
    return " ".join(list(text.upper()))


class Radar(tk.Canvas):
    """Small animated circular HUD element that reflects assistant state."""

    STATE_COLORS = {
        "offline": RED,
        "idle": CYAN,
        "listening": GREEN,
        "thinking": AMBER,
        "speaking": GREEN,
    }

    def __init__(self, parent, size=170, **kwargs):
        super().__init__(parent, width=size, height=size, bg=PANEL, highlightthickness=0, **kwargs)
        self.size = size
        self.center = size / 2
        self.radius = size / 2 - 10
        self.angle = 0.0
        self.state = "offline"
        self._pulse = 0.0
        self._pulse_dir = 1
        self._draw_static()
        self._sweep_id = None
        self.after(30, self._animate)

    def _draw_static(self):
        self.delete("static")
        c, r = self.center, self.radius
        for ring_r in (r, r * 0.66, r * 0.33):
            self.create_oval(c - ring_r, c - ring_r, c + ring_r, c + ring_r,
                              outline=BORDER, width=1, tags="static")
        # crosshair
        self.create_line(c - r, c, c + r, c, fill=BORDER, tags="static")
        self.create_line(c, c - r, c, c + r, fill=BORDER, tags="static")
        # tick marks
        for deg in range(0, 360, 30):
            rad = math.radians(deg)
            x1, y1 = c + (r - 4) * math.cos(rad), c + (r - 4) * math.sin(rad)
            x2, y2 = c + r * math.cos(rad), c + r * math.sin(rad)
            self.create_line(x1, y1, x2, y2, fill=CYAN_DIM, tags="static")

    def set_state(self, state):
        self.state = state

    def _animate(self):
        self.delete("dynamic")
        color = self.STATE_COLORS.get(self.state, CYAN)
        c, r = self.center, self.radius

        if self.state == "listening":
            self.angle = (self.angle + 8) % 360
            rad = math.radians(self.angle)
            x2, y2 = c + r * math.cos(rad), c + r * math.sin(rad)
            self.create_line(c, c, x2, y2, fill=color, width=2, tags="dynamic")
            # fading trail
            for i in range(1, 6):
                trail_angle = math.radians(self.angle - i * 10)
                tx, ty = c + r * math.cos(trail_angle), c + r * math.sin(trail_angle)
                self.create_line(c, c, tx, ty, fill=color, width=1, stipple="gray50", tags="dynamic")
        elif self.state == "thinking":
            self.angle = (self.angle + 14) % 360
            for offset in (0, 120, 240):
                rad = math.radians(self.angle + offset)
                x, y = c + (r * 0.8) * math.cos(rad), c + (r * 0.8) * math.sin(rad)
                self.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline="", tags="dynamic")
        else:
            # idle / speaking / offline -> pulsing center dot
            self._pulse += 0.06 * self._pulse_dir
            if self._pulse > 1:
                self._pulse, self._pulse_dir = 1, -1
            elif self._pulse < 0:
                self._pulse, self._pulse_dir = 0, 1
            pr = 6 + self._pulse * 10
            self.create_oval(c - pr, c - pr, c + pr, c + pr, outline=color, width=2, tags="dynamic")

        self.create_oval(c - 4, c - 4, c + 4, c + 4, fill=color, outline="", tags="dynamic")
        self.after(35, self._animate)


class HUDButton(tk.Label):
    """A clickable HUD-styled 'button' built from a Label so we get full control of the glow look."""

    def __init__(self, parent, text, command=None, color=CYAN, **kwargs):
        self.command = command
        self.color = color
        super().__init__(
            parent, text=spaced(text), font=(FONT_MONO, 10, "bold"),
            bg=PANEL, fg=color, padx=16, pady=10, cursor="hand2",
            highlightbackground=color, highlightcolor=color, highlightthickness=1,
            **kwargs
        )
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_click(self, _event):
        if self.command:
            self.command()

    def _on_enter(self, _event):
        self.configure(bg=self.color, fg=BG)

    def _on_leave(self, _event):
        self.configure(bg=PANEL, fg=self.color)

    def set_color(self, color):
        self.color = color
        self.configure(fg=color, highlightbackground=color, highlightcolor=color)


class JarvisApp:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.thread = None
        self.name = assistant.config.get("assistant_name", "Jarvis")

        root.title(f"{self.name} // HUD TERMINAL")
        root.geometry("980x680")
        root.configure(bg=BG)
        root.minsize(780, 560)

        self.tray_icon = None

        self._build_frame()
        self._build_header()
        self._build_body()
        self._build_footer()

        assistant.set_gui_hooks(on_speak=self.on_speak, on_status=self.on_status)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._tick_clock()

        # Auto-start listening as soon as the app opens, so you don't have to
        # click Start every time — controlled by config.json "auto_start_listening".
        if assistant.config.get("auto_start_listening", True):
            self.root.after(400, self.start)

        # If launched at Windows startup, go straight to the tray instead of
        # showing a window — controlled by config.json "start_minimized".
        if assistant.config.get("start_minimized", False) and pystray is not None:
            self.root.after(600, self._minimize_to_tray)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_frame(self):
        """Outer canvas draws the HUD border + corner brackets; content sits inset inside it."""
        self.outer = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.outer.pack(fill="both", expand=True)
        self.outer.bind("<Configure>", self._redraw_border)

        self.content = tk.Frame(self.outer, bg=BG)
        self.content_window = self.outer.create_window(14, 14, anchor="nw", window=self.content)

    def _redraw_border(self, event):
        self.outer.delete("border")
        w, h = event.width, event.height
        pad = 10
        bl = 26  # bracket leg length

        # thin outer border
        self.outer.create_rectangle(pad, pad, w - pad, h - pad, outline=BORDER, width=1, tags="border")

        # corner brackets (HUD look)
        for x, dx in ((pad, 1), (w - pad, -1)):
            for y, dy in ((pad, 1), (h - pad, -1)):
                self.outer.create_line(x, y, x + bl * dx, y, fill=CYAN, width=2, tags="border")
                self.outer.create_line(x, y, x, y + bl * dy, fill=CYAN, width=2, tags="border")

        self.outer.coords(self.content_window, 14, 14)
        self.outer.itemconfig(self.content_window, width=max(w - 28, 100), height=max(h - 28, 100))
        self.outer.tag_lower("border")

    def _build_header(self):
        header = tk.Frame(self.content, bg=BG)
        header.pack(fill="x", padx=10, pady=(6, 4))

        left = tk.Frame(header, bg=BG)
        left.pack(side="left")
        tk.Label(left, text=spaced(self.name), font=(FONT_MONO, 24, "bold"),
                 bg=BG, fg=CYAN).pack(anchor="w")
        tk.Label(left, text="VOICE COMMAND INTERFACE", font=(FONT_MONO, 9),
                 bg=BG, fg=DIM).pack(anchor="w")

        right = tk.Frame(header, bg=BG)
        right.pack(side="right")
        self.clock_label = tk.Label(right, text="00:00:00", font=(FONT_MONO, 20, "bold"), bg=BG, fg=TEXT)
        self.clock_label.pack(anchor="e")
        self.date_label = tk.Label(right, text="", font=(FONT_MONO, 9), bg=BG, fg=DIM)
        self.date_label.pack(anchor="e")

        tk.Frame(self.content, bg=BORDER, height=1).pack(fill="x", padx=10, pady=(4, 8))

    def _build_body(self):
        body = tk.Frame(self.content, bg=BG)
        body.pack(fill="both", expand=True, padx=10)

        # ---- Left panel: radar + status readout ----
        left_panel = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        left_panel.pack(side="left", fill="y", padx=(0, 10), pady=2)

        tk.Label(left_panel, text=spaced("Status"), font=(FONT_MONO, 9, "bold"),
                 bg=PANEL, fg=DIM).pack(pady=(14, 4))

        self.radar = Radar(left_panel)
        self.radar.pack(padx=18, pady=6)

        self.status_label = tk.Label(left_panel, text="OFFLINE", font=(FONT_MONO, 13, "bold"),
                                      bg=PANEL, fg=RED)
        self.status_label.pack(pady=(4, 16))

        tk.Frame(left_panel, bg=BORDER, height=1).pack(fill="x", padx=14)

        stats_frame = tk.Frame(left_panel, bg=PANEL)
        stats_frame.pack(fill="x", padx=16, pady=14)
        self.mic_stat = self._stat_row(stats_frame, "MIC")
        self.mode_stat = self._stat_row(stats_frame, "MODE", assistant.config.get("language", "ur-PK"))
        self.mem_stat = self._stat_row(stats_frame, "MEMORY", "LOADED")

        tk.Frame(left_panel, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(6, 12))

        self.memory_btn = HUDButton(left_panel, "View Memory", command=self.show_memory, color=CYAN)
        self.memory_btn.pack(padx=16, pady=(0, 10), fill="x")
        self.commands_btn = HUDButton(left_panel, "Commands", command=self.show_commands, color=CYAN)
        self.commands_btn.pack(padx=16, pady=(0, 18), fill="x")

        # ---- Right panel: terminal-style conversation log ----
        right_panel = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        right_panel.pack(side="left", fill="both", expand=True, pady=2)

        log_header = tk.Frame(right_panel, bg=PANEL)
        log_header.pack(fill="x")
        tk.Label(log_header, text=spaced("Conversation Log"), font=(FONT_MONO, 9, "bold"),
                 bg=PANEL, fg=DIM).pack(side="left", padx=14, pady=10)

        self.log_box = scrolledtext.ScrolledText(
            right_panel, wrap="word", bg="#050a0f", fg=TEXT,
            font=(FONT_MONO, 10), bd=0, padx=14, pady=12,
            insertbackground=TEXT, state="normal", highlightthickness=0
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_box.tag_config("assistant", foreground=CYAN)
        self.log_box.tag_config("user", foreground=GREEN)
        self.log_box.tag_config("system", foreground=DIM)
        self._log("system", f"[SYS] {self.name} HUD ready. Press START to begin.")

    def _stat_row(self, parent, label, initial="—"):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, font=(FONT_MONO, 9), bg=PANEL, fg=DIM, width=8, anchor="w").pack(side="left")
        val = tk.Label(row, text=initial, font=(FONT_MONO, 9, "bold"), bg=PANEL, fg=TEXT, anchor="e")
        val.pack(side="right")
        return val

    def _build_footer(self):
        footer = tk.Frame(self.content, bg=BG)
        footer.pack(fill="x", padx=10, pady=(10, 8))

        self.start_btn = HUDButton(footer, "Start Listening", command=self.toggle, color=GREEN)
        self.start_btn.pack(side="left", fill="x", expand=True)

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------
    def _tick_clock(self):
        now = datetime.datetime.now()
        self.clock_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(text=now.strftime("%A, %d %B %Y").upper())
        self.root.after(1000, self._tick_clock)

    # ------------------------------------------------------------------
    # Assistant hooks (thread-safe UI updates)
    # ------------------------------------------------------------------
    def _log(self, tag, text):
        self.log_box.insert(tk.END, text + "\n\n", tag)
        self.log_box.see(tk.END)

    def on_speak(self, text):
        self.root.after(0, lambda: self._log("assistant", f"[{self.name.upper()}] {text}"))

    def on_status(self, status):
        self.root.after(0, lambda: self._set_status(status))

    def _set_status(self, status):
        self.status_label.config(text=status.upper().rstrip("…").strip())
        if not self.running:
            self.radar.set_state("offline")
            self.status_label.config(fg=RED)
            self.mic_stat.config(text="OFF", fg=RED)
            return

        mapping = {
            "Listening…": ("listening", GREEN, "LIVE"),
            "Thinking…": ("thinking", AMBER, "BUSY"),
            "Speaking…": ("speaking", GREEN, "BUSY"),
            "Idle": ("idle", CYAN, "READY"),
            "Online": ("idle", CYAN, "READY"),
        }
        state, color, mic_text = mapping.get(status, ("idle", CYAN, "READY"))
        self.radar.set_state(state)
        self.status_label.config(fg=color)
        self.mic_stat.config(text=mic_text, fg=color)

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------
    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        self.running = True
        self.start_btn.configure(text=spaced("Stop Listening"))
        self.start_btn.set_color(RED)
        self._set_status("Online")
        self._log("system", "[SYS] Listening started.")
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()

    def run_loop(self):
        wake_enabled = assistant.config.get("wake_word_enabled", True)
        wake_word = assistant.config.get("wake_word", "jarvis")

        if wake_enabled:
            assistant.speak(f"{self.name} is on standby. Say '{wake_word}' any time to wake me up.")
        else:
            assistant.speak(f"{self.name} is online. Say a command, or say exit to quit.")

        while self.running:
            if wake_enabled:
                remainder = assistant.listen_for_wake_word(stop_check=lambda: not self.running)
                if remainder is None:
                    break  # Stop button was pressed while waiting for the wake word.
                if remainder:
                    command = remainder
                else:
                    assistant.speak("Yes?")
                    command = assistant.listen()
            else:
                command = assistant.listen()

            if command:
                self.root.after(0, lambda c=command: self._log("user", f"[YOU] {c}"))
            keep_going = assistant.handle_command(command)
            if not keep_going:
                self.running = False
                self.root.after(0, self._reset_button)
                break

    def stop(self):
        self.running = False
        self._reset_button()
        self._log("system", "[SYS] Listening stopped.")

    def _reset_button(self):
        self.start_btn.configure(text=spaced("Start Listening"))
        self.start_btn.set_color(GREEN)
        self._set_status("Offline")

    def show_memory(self):
        win = tk.Toplevel(self.root)
        win.title("MEMORY BANK")
        win.geometry("380x440")
        win.configure(bg=PANEL)

        tk.Label(win, text=spaced(f"What {self.name} Remembers"), font=(FONT_MONO, 11, "bold"),
                 bg=PANEL, fg=CYAN).pack(pady=(16, 8))

        box = scrolledtext.ScrolledText(win, wrap="word", bg="#050a0f", fg=TEXT,
                                         font=(FONT_MONO, 10), bd=0, padx=10, pady=10,
                                         highlightthickness=0)
        box.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        try:
            with open(assistant.MEMORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            box.insert("1.0", json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            box.insert("1.0", f"Could not read memory.json: {e}")
        box.config(state="disabled")

    def show_commands(self):
        win = tk.Toplevel(self.root)
        win.title("COMMAND REFERENCE")
        win.geometry("440x520")
        win.configure(bg=PANEL)

        tk.Label(win, text=spaced("Available Commands"), font=(FONT_MONO, 11, "bold"),
                 bg=PANEL, fg=CYAN).pack(pady=(16, 8))

        box = scrolledtext.ScrolledText(win, wrap="word", bg="#050a0f", fg=TEXT,
                                         font=(FONT_MONO, 10), bd=0, padx=10, pady=10,
                                         highlightthickness=0)
        box.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        wake_word = assistant.config.get("wake_word", "jarvis")
        commands_text = (
            f"WAKE WORD\n"
            f"  Say '{wake_word}' first, then your command\n"
            f"  (or say them together: '{wake_word}, open chrome')\n\n"
            "APPS\n"
            "  open chrome / notepad / calculator / word / excel / paint / ...\n"
            "  close chrome\n\n"
            "WEB\n"
            "  search <query>\n"
            "  open website <name>  /  go to <site>\n\n"
            "WEATHER\n"
            "  what's the weather\n"
            "  weather in <city>\n\n"
            "MESSAGING\n"
            "  message <contact> <text>\n\n"
            "ADS\n"
            "  schedule <ad set name> <start> to <end>\n\n"
            "SYSTEM\n"
            "  volume up / volume down / mute\n"
            "  lock the screen\n"
            "  shut down  /  restart  /  sleep\n"
            "  cancel shutdown  /  cancel restart\n"
            "  take a screenshot\n"
            "  battery status  /  cpu status\n"
            "  what's the wifi password\n\n"
            "TIME\n"
            "  what's the time  /  what's the date\n\n"
            "MEMORY\n"
            "  my name is <name>  /  mera naam <name> hai\n"
            "  what is my name\n"
            "  remember <thing> is <value>\n"
            "  <thing> kya hai\n\n"
            "EXIT\n"
            "  exit  /  goodbye  /  stop listening\n"
        )
        box.insert("1.0", commands_text)
        box.config(state="disabled")

    # ------------------------------------------------------------------
    # System tray — lets Jarvis keep running (and listening for the wake
    # word) in the background instead of quitting when you close the window.
    # ------------------------------------------------------------------
    def _build_tray_image(self):
        img = Image.new("RGB", (64, 64), (6, 10, 16))
        draw = ImageDraw.Draw(img)
        draw.ellipse((6, 6, 58, 58), outline=(40, 232, 255), width=4)
        draw.ellipse((26, 26, 38, 38), fill=(40, 232, 255))
        return img

    def _minimize_to_tray(self):
        self.root.withdraw()
        if self.tray_icon is None:
            menu = pystray.Menu(
                pystray.MenuItem("Show", self._tray_show, default=True),
                pystray.MenuItem("Exit", self._tray_exit),
            )
            self.tray_icon = pystray.Icon("jarvis", self._build_tray_image(), self.name, menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _tray_show(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)

    def _tray_exit(self, icon=None, item=None):
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.after(0, self.root.destroy)

    def on_close(self):
        if pystray is not None:
            # Keep running in the background (and keep listening for the wake
            # word) instead of exiting — click the tray icon to bring it back,
            # or right-click it and choose Exit to actually quit.
            self._minimize_to_tray()
        else:
            self.running = False
            self.root.destroy()


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    JarvisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
