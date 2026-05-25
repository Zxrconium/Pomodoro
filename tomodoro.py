#!/usr/bin/env python3
"""Tomodoro — cute minimalistic Pomodoro timer."""

import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont
import math
import json
import os
import wave
import struct
import io

try:
    import pygame
    _PYGAME = True
except ImportError:
    _PYGAME = False

try:
    from PIL import Image, ImageDraw, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

# ── Palette ────────────────────────────────────────────────────────────
BG      = "#F0F4EE"
PRIMARY = "#87A878"
LIGHT   = "#B2C9A7"
DARK    = "#6B8F5E"
TEXT    = "#3D5A3E"
SUBTEXT = "#7A9B7B"
WHITE   = "#FFFFFF"
SHADOW  = "#D8E3D4"
TEAL    = "#6BADA0"

MODE_COLORS = [PRIMARY, TEAL, DARK]
MODE_HOVER  = [DARK, "#4E8A7E", "#4A6640"]

DEFAULT = {"work": 25, "short": 5, "long": 15, "long_after": 4}
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".tomodoro.json")


# ── Font helper ─────────────────────────────────────────────────────────
def _font_family() -> str:
    available = set(tkfont.families())
    for f in ("Nunito", "Helvetica Rounded", "Segoe UI", "Calibri",
              "Helvetica", "Arial"):
        if f in available:
            return f
    return "TkDefaultFont"


# ── Chime synthesis ─────────────────────────────────────────────────────
def _make_chime() -> bytes:
    """Synthesize a soft 2-note bell chime (C5 → G5)."""
    sr = 44100
    dur = 2.8
    n = int(sr * dur)

    # Two bell strikes 0.3 s apart
    strikes = [
        (0.00, [(523.25, 1.00, 2.2), (1046.5, 0.30, 3.5), (1568.0, 0.15, 5.0)]),
        (0.35, [(783.99, 0.85, 2.0), (1567.9, 0.25, 3.2), (2093.0, 0.12, 5.5)]),
    ]

    buf = []
    for i in range(n):
        t = i / sr
        s = 0.0
        for t0, partials in strikes:
            dt = t - t0
            if dt < 0:
                continue
            for freq, amp, decay in partials:
                s += amp * math.exp(-decay * dt) * math.sin(2 * math.pi * freq * dt)
        s *= min(1.0, t / 0.006)          # 6 ms attack
        buf.append(max(-32767, min(32767, int(s * 18000))))

    out = io.BytesIO()
    with wave.open(out, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack(f"<{n}h", *buf))
    return out.getvalue()


# ── Tomato icon ──────────────────────────────────────────────────────────
def _make_icon_photo(root, size: int = 64):
    if not _PIL:
        return None
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    body_pad = int(s * 0.08)
    body_top = int(s * 0.16)
    d.ellipse([body_pad, body_top, s - body_pad, s - body_pad],
              fill="#E05C4A")

    cx = s // 2
    # Stem
    d.rectangle([cx - 2, 2, cx + 2, body_top + 2], fill="#5A7A3A")
    # Left leaf
    d.ellipse([cx - 10, 3, cx + 2, body_top + 2], fill=PRIMARY)
    # Right leaf
    d.ellipse([cx - 2, 3, cx + 10, body_top + 2], fill=DARK)

    # Highlight
    hw = int(s * 0.12)
    d.ellipse([int(s*0.22), int(s*0.24), int(s*0.22)+hw*2, int(s*0.24)+hw],
              fill=(255, 255, 255, 90))

    return ImageTk.PhotoImage(img)


# ══════════════════════════════════════════════════════════════════════════
class Tomodoro(ctk.CTk):

    CS = 250   # canvas size
    AP = 22    # arc padding from canvas edge
    AW = 18    # arc line width

    def __init__(self):
        super().__init__()

        self.cfg = dict(DEFAULT)
        try:
            with open(SETTINGS_PATH) as f:
                self.cfg.update(json.load(f))
        except Exception:
            pass

        self.mode    = 0
        self.count   = 0
        self.running = False
        self.left    = 0
        self.total   = 0
        self._job    = None
        self._arc_col = PRIMARY

        # Sound
        self._chime = None
        if _PYGAME:
            try:
                pygame.mixer.init(44100, -16, 1, 512)
                self._chime = pygame.mixer.Sound(io.BytesIO(_make_chime()))
                self._chime.set_volume(0.65)
            except Exception:
                pass

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")
        self.title("Tomodoro")
        self.resizable(False, False)
        self.configure(fg_color=BG)

        self._fam = _font_family()
        self._build_ui()
        self._mode_switch(0, auto_start=False)

        # Set window icon
        self.update_idletasks()
        icon = _make_icon_photo(self)
        if icon:
            self.iconphoto(True, icon)
            self._icon_ref = icon

        # Center window
        self.update_idletasks()
        W, H = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw-W)//2}+{(sh-H)//2}")

    # ── UI construction ──────────────────────────────────────────────────

    def _f(self, size: int, weight: str = "normal") -> ctk.CTkFont:
        return ctk.CTkFont(family=self._fam, size=size, weight=weight)

    def _build_ui(self):
        # ── Header ──
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=26, pady=(22, 6))

        ctk.CTkLabel(
            hdr, text="🍅  Tomodoro",
            font=self._f(22, "bold"), text_color=DARK
        ).pack(side="left")

        ctk.CTkButton(
            hdr, text="⚙", width=38, height=38,
            fg_color=LIGHT, hover_color=PRIMARY,
            text_color=DARK, corner_radius=19,
            font=ctk.CTkFont(size=17),
            command=self._open_settings
        ).pack(side="right")

        # ── Mode tabs ──
        tabs_frame = ctk.CTkFrame(self, fg_color="transparent")
        tabs_frame.pack(pady=(2, 8))

        self._tabs = []
        for i, label in enumerate(("Work", "Short Break", "Long Break")):
            b = ctk.CTkButton(
                tabs_frame, text=label,
                width=112, height=30,
                fg_color=LIGHT, hover_color=MODE_HOVER[i],
                text_color=TEXT, corner_radius=15,
                font=self._f(12, "bold"),
                command=lambda i=i: self._mode_switch(i, auto_start=False)
            )
            b.pack(side="left", padx=3)
            self._tabs.append(b)

        # ── Timer card ──
        card = ctk.CTkFrame(
            self, fg_color=WHITE, corner_radius=30,
            border_width=2, border_color=LIGHT
        )
        card.pack(padx=26, pady=4)

        self.cv = tk.Canvas(
            card, width=self.CS, height=self.CS,
            bg=WHITE, highlightthickness=0
        )
        self.cv.pack(padx=22, pady=22)

        # ── Session dots ──
        dot_wrap = ctk.CTkFrame(self, fg_color="transparent")
        dot_wrap.pack(pady=(8, 4))

        self._dots_lbl = ctk.CTkLabel(
            dot_wrap, text="",
            font=ctk.CTkFont(size=22), text_color=PRIMARY
        )
        self._dots_lbl.pack()

        self._count_lbl = ctk.CTkLabel(
            dot_wrap, text="",
            font=self._f(12), text_color=SUBTEXT
        )
        self._count_lbl.pack()

        # ── Control buttons ──
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(6, 26))

        self._play_btn = ctk.CTkButton(
            btn_row, text="▶   Start",
            width=152, height=50,
            fg_color=PRIMARY, hover_color=DARK,
            text_color=WHITE, corner_radius=25,
            font=self._f(15, "bold"),
            command=self._toggle
        )
        self._play_btn.pack(side="left", padx=6)

        ctk.CTkButton(
            btn_row, text="↺   Reset",
            width=122, height=50,
            fg_color=LIGHT, hover_color=PRIMARY,
            text_color=DARK, corner_radius=25,
            font=self._f(15, "bold"),
            command=self._reset
        ).pack(side="left", padx=6)

    # ── Timer state machine ──────────────────────────────────────────────

    def _duration(self, m: int) -> int:
        return [self.cfg["work"], self.cfg["short"], self.cfg["long"]][m] * 60

    def _mode_switch(self, m: int, auto_start: bool = True):
        self._stop()
        self.mode     = m
        self.left     = self.total = self._duration(m)
        self._arc_col = MODE_COLORS[m]
        self._refresh_tabs()
        self._draw()
        self._refresh_dots()
        self._play_btn.configure(text="▶   Start")
        if auto_start:
            self._toggle()

    def _refresh_tabs(self):
        for i, btn in enumerate(self._tabs):
            if i == self.mode:
                btn.configure(fg_color=MODE_COLORS[i], text_color=WHITE)
            else:
                btn.configure(fg_color=LIGHT, text_color=TEXT,
                               hover_color=MODE_HOVER[i])

    def _toggle(self):
        if self.running:
            self._stop()
            self._play_btn.configure(text="▶   Resume")
        else:
            self.running = True
            self._play_btn.configure(text="⏸   Pause")
            self._tick()

    def _stop(self):
        self.running = False
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def _reset(self):
        self._stop()
        self.left = self.total
        self._play_btn.configure(text="▶   Start")
        self._draw()

    def _tick(self):
        if not self.running:
            return
        if self.left <= 0:
            self._on_finish()
            return
        self.left -= 1
        self._draw()
        self._job = self.after(1000, self._tick)

    def _on_finish(self):
        self.running = False
        if self._chime:
            self._chime.play()

        if self.mode == 0:
            self.count += 1
            la = max(1, self.cfg["long_after"])
            nxt = 2 if (self.count % la == 0) else 1
        else:
            nxt = 0

        self._mode_switch(nxt, auto_start=True)

    # ── Canvas drawing ───────────────────────────────────────────────────

    def _draw(self):
        cv = self.cv
        cv.delete("all")

        cs = self.CS
        cx = cy = cs / 2
        r  = cx - self.AP
        x0, y0 = cx - r, cy - r
        x1, y1 = cx + r, cy + r

        # Outer shadow
        cv.create_oval(
            x0 + 3, y0 + 3, x1 + 3, y1 + 3,
            outline=SHADOW, fill="", width=self.AW + 4
        )

        # Background ring
        cv.create_arc(
            x0, y0, x1, y1,
            start=0, extent=359.9,
            fill="", outline=LIGHT,
            width=self.AW, style=tk.ARC
        )

        # Progress arc  (clockwise from 12 o'clock)
        p = self.left / max(self.total, 1)
        if p > 0.003:
            cv.create_arc(
                x0, y0, x1, y1,
                start=90, extent=-360.0 * p,
                fill="", outline=self._arc_col,
                width=self.AW, style=tk.ARC
            )

        # Time display
        time_str = f"{self.left // 60:02d}:{self.left % 60:02d}"
        cv.create_text(
            cx, cy - 12,
            text=time_str,
            font=(self._fam, 42, "bold"),
            fill=TEXT
        )

        # Mode label
        labels = ["Focus Time", "Short Break ☕", "Long Break ✨"]
        cv.create_text(
            cx, cy + 30,
            text=labels[self.mode],
            font=(self._fam, 13),
            fill=SUBTEXT
        )

    def _refresh_dots(self):
        la = max(1, self.cfg["long_after"])
        done = self.count % la
        self._dots_lbl.configure(text="🍅" * done + "◯" * (la - done))
        n = self.count
        if n == 0:
            msg = "No pomodoros completed yet"
        elif n == 1:
            msg = "1 pomodoro completed  🎉"
        else:
            msg = f"{n} pomodoros completed  🎉"
        self._count_lbl.configure(text=msg)

    # ── Settings ─────────────────────────────────────────────────────────

    def _open_settings(self):
        SettingsWindow(self)

    def _save_cfg(self):
        try:
            with open(SETTINGS_PATH, "w") as f:
                json.dump(self.cfg, f, indent=2)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════
class SettingsWindow(ctk.CTkToplevel):

    def __init__(self, parent: Tomodoro):
        super().__init__(parent)
        self.p = parent
        self.title("Settings")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.grab_set()
        self.focus_set()

        w, h = 370, 430
        self.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        self.geometry(f"{w}x{h}+{px+(pw-w)//2}+{py+(ph-h)//2}")

        self._fam = parent._fam
        self._build()

    def _f(self, size: int, weight: str = "normal") -> ctk.CTkFont:
        return ctk.CTkFont(family=self._fam, size=size, weight=weight)

    def _build(self):
        ctk.CTkLabel(
            self, text="⚙   Settings",
            font=self._f(19, "bold"), text_color=DARK
        ).pack(pady=(22, 12))

        specs = [
            ("Work Duration",     "work",       5, 90, "min"),
            ("Short Break",       "short",      1, 30, "min"),
            ("Long Break",        "long",       5, 60, "min"),
            ("Long Break After",  "long_after", 2,  8, "rounds"),
        ]

        self._sliders = {}

        for label, key, lo, hi, unit in specs:
            row = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=18,
                               border_width=1, border_color=LIGHT)
            row.pack(fill="x", padx=22, pady=5)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x", padx=16, pady=(10, 0))

            ctk.CTkLabel(top, text=label,
                         font=self._f(13, "bold"),
                         text_color=TEXT).pack(side="left")

            val_lbl = ctk.CTkLabel(
                top,
                text=f"{self.p.cfg[key]} {unit}",
                font=self._f(13), text_color=PRIMARY
            )
            val_lbl.pack(side="right")

            sl = ctk.CTkSlider(
                row,
                from_=lo, to=hi, number_of_steps=hi - lo,
                progress_color=PRIMARY, button_color=DARK,
                button_hover_color=DARK, fg_color=LIGHT,
                width=310,
                command=lambda v, lbl=val_lbl, u=unit:
                    lbl.configure(text=f"{round(v)} {u}")
            )
            sl.set(self.p.cfg[key])
            sl.pack(padx=16, pady=(4, 14))
            self._sliders[key] = sl

        ctk.CTkButton(
            self, text="✓   Save & Close",
            width=300, height=52,
            fg_color=PRIMARY, hover_color=DARK,
            text_color=WHITE, corner_radius=26,
            font=self._f(16, "bold"),
            command=self._save
        ).pack(pady=(10, 22))

    def _save(self):
        for k, sl in self._sliders.items():
            self.p.cfg[k] = round(sl.get())
        self.p._save_cfg()
        self.p._mode_switch(self.p.mode, auto_start=False)
        self.p._refresh_dots()
        self.destroy()


# ── Entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = Tomodoro()
    app.mainloop()
