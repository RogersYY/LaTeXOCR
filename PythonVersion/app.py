import base64
import io
import json
import os
import re
import sys
import multiprocessing as mp
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import requests
import ttkbootstrap as ttkb
from ttkbootstrap.constants import BOTH, LEFT, X
from PIL import Image, ImageGrab, ImageTk
from pynput import keyboard
import webview


DEFAULT_CONFIG = {
    "api_base_url": "http://1.95.70.60:3000/v1/chat/completions",
    "api_key": "sk-3AwknygGjEskI3SdeBstLZaHHh9peebQFHnEv4HWeUVdELG1",
    "api_model": "gpt-5.2",
    "copy_format": "latex",
    "hotkey": "<ctrl>+<shift>+a",
}


def get_config_dir():
    if os.name == "nt":
        base = os.getenv("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "LaTeXOCR")
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
        return os.path.join(base, "LaTeXOCR")
    base = os.getenv("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "LaTeXOCR")


def resource_path(relative_path):
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_dir / relative_path


class AppSettings:
    def __init__(self):
        self.path = os.path.join(get_config_dir(), "config.json")
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if isinstance(raw, dict):
                self.data.update(raw)
        except (OSError, json.JSONDecodeError):
            pass

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2)


def strip_latex_markers(text):
    if not text:
        return ""
    cleaned = re.sub(r"```latex\s*|```", "", text)
    cleaned = cleaned.strip()
    if cleaned.startswith("\\[") and cleaned.endswith("\\]"):
        cleaned = cleaned[2:-2].strip()
    if cleaned.startswith("$$") and cleaned.endswith("$$"):
        cleaned = cleaned[2:-2].strip()
    return cleaned


def preview_process_main(html_path, cmd_queue, resp_queue):
    ready = threading.Event()

    html_url = Path(html_path).resolve().as_uri()
    window = webview.create_window(
        "KaTeX Preview",
        url=html_url,
        width=920,
        height=640,
        resizable=True,
    )

    def on_loaded():
        ready.set()

    window.events.loaded += on_loaded

    def process_commands():
        ready.wait()
        while True:
            cmd = cmd_queue.get()
            if not isinstance(cmd, dict):
                continue
            action = cmd.get("type")
            if action == "close":
                window.destroy()
                break
            if action == "set_latex":
                latex = cmd.get("latex", "")
                js = "window.setLatex(%s);" % json.dumps(latex)
                window.evaluate_js(js)
                continue
            if action == "get_mathml":
                latex = cmd.get("latex", "")
                req_id = cmd.get("id")
                js = "window.getMathML(%s);" % json.dumps(latex)
                result = window.evaluate_js(js)
                resp_queue.put({"id": req_id, "result": result})
                continue
            if action == "bring_to_front":
                try:
                    window.bring_to_front()
                except Exception:
                    pass

    webview.start(process_commands, debug=False)


class PreviewWindow:
    def __init__(self, html_path):
        self.html_path = html_path
        self.cmd_queue = mp.Queue()
        self.resp_queue = mp.Queue()
        self.process = mp.Process(
            target=preview_process_main,
            args=(self.html_path, self.cmd_queue, self.resp_queue),
            daemon=True,
        )
        self.process.start()
        self._request_id = 0

    def set_latex(self, latex):
        if not self._is_alive():
            return False
        self.cmd_queue.put({"type": "set_latex", "latex": latex})
        return True

    def get_mathml(self, latex):
        if not self._is_alive():
            return None
        self._request_id += 1
        request_id = self._request_id
        self.cmd_queue.put({"type": "get_mathml", "latex": latex, "id": request_id})
        try:
            while True:
                response = self.resp_queue.get(timeout=6)
                if response.get("id") == request_id:
                    return response.get("result")
        except Exception:
            return None

    def bring_to_front(self):
        if not self._is_alive():
            return
        self.cmd_queue.put({"type": "bring_to_front"})

    def close(self):
        if not self._is_alive():
            return
        self.cmd_queue.put({"type": "close"})
        self.process.join(timeout=2)
        if self.process.is_alive():
            self.process.terminate()

    def _is_alive(self):
        return self.process is not None and self.process.is_alive()


class RegionSelector:
    def __init__(self, root):
        self.root = root
        self.bbox = None
        self.start_x = None
        self.start_y = None
        self.rect_id = None

        self.top = tk.Toplevel(root)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-alpha", 0.25)
        self.top.attributes("-topmost", True)
        self.top.overrideredirect(True)

        self.canvas = tk.Canvas(self.top, cursor="cross", bg="black")
        self.canvas.pack(fill=BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.top.bind("<Escape>", self.on_cancel)

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="red",
            width=2,
        )

    def on_drag(self, event):
        if not self.rect_id:
            return
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if self.start_x is None or self.start_y is None:
            self.on_cancel()
            return
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        if right - left < 2 or bottom - top < 2:
            self.on_cancel()
            return
        self.bbox = (left, top, right, bottom)
        self.top.destroy()

    def on_cancel(self, event=None):
        self.bbox = None
        self.top.destroy()

    def select(self):
        self.root.wait_window(self.top)
        return self.bbox


class LatexOCRApp:
    def __init__(self):
        self.settings = AppSettings()
        self.root = ttkb.Window(themename="sandstone")
        self.root.title("LaTeXOCR (Python)")
        self.root.geometry("1280x820")
        self.root.minsize(1120, 720)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        self.palette = {
            "bg_start": "#fff0e2",
            "bg_end": "#d8f3ee",
            "surface": "#fbf1e4",
            "card_bg": "#ffffff",
            "card_border": "#ead3bf",
            "shadow": "#d1bfae",
            "text": "#1f2937",
            "muted": "#6b7280",
            "accent": "#d97706",
            "accent_alt": "#0f766e",
            "pattern": "#efe4d4",
        }
        self._configure_styles()

        self.preview = None
        self.current_image = None
        self.preview_image = None
        self.latex_text_value = ""
        self.hotkey_listener = None

        self._build_menu()
        self._build_ui()
        self._start_preview()
        self._start_hotkey()

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        app_menu = tk.Menu(menubar, tearoff=0)
        app_menu.add_command(label="Settings", command=self.open_settings)
        app_menu.add_command(label="Exit", command=self.on_exit)
        menubar.add_cascade(label="App", menu=app_menu)
        self.root.config(menu=menubar)

    def _configure_styles(self):
        if os.name == "nt":
            base_family = "Segoe UI"
            title_family = "Segoe UI Semibold"
            mono_family = "Consolas"
        elif sys.platform == "darwin":
            base_family = "Avenir Next"
            title_family = "Avenir Next Demi Bold"
            mono_family = "Menlo"
        else:
            base_family = "DejaVu Sans"
            title_family = "DejaVu Sans"
            mono_family = "DejaVu Sans Mono"

        self.font_title = (title_family, 32, "bold")
        self.font_subtitle = (base_family, 13)
        self.font_body = (base_family, 11)
        self.font_card_title = (base_family, 14, "bold")
        self.font_mono = (mono_family, 11)
        self.root.option_add("*Font", self.font_body)

        style = self.root.style
        style.configure("TButton", font=self.font_body, padding=(10, 6))
        style.configure("TLabel", font=self.font_body)
        style.configure("TEntry", font=self.font_body)
        style.configure("TCombobox", font=self.font_body)
        style.configure("TProgressbar", thickness=6)

    def _build_ui(self):
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0)
        self.bg_canvas.pack(fill=BOTH, expand=True)
        self.content = tk.Frame(self.bg_canvas, bg=self.palette["surface"])
        self.bg_window = self.bg_canvas.create_window(
            (16, 16), window=self.content, anchor="nw"
        )
        self.bg_canvas.bind("<Configure>", self._on_canvas_resize)

        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(2, weight=3, minsize=280)
        self.content.rowconfigure(3, weight=4, minsize=260)

        header = tk.Frame(self.content, bg=self.palette["surface"])
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        title_block = tk.Frame(header, bg=self.palette["surface"])
        title_block.grid(row=0, column=0, sticky="w")
        tk.Label(
            title_block,
            text="LaTeXOCR",
            font=self.font_title,
            bg=self.palette["surface"],
            fg=self.palette["text"],
        ).pack(anchor="w")
        tk.Label(
            title_block,
            text="Capture formulas, render with KaTeX, and copy instantly.",
            font=self.font_subtitle,
            bg=self.palette["surface"],
            fg=self.palette["muted"],
        ).pack(anchor="w", pady=(2, 0))
        accent = tk.Frame(header, bg=self.palette["accent"], height=3)
        accent.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        accent.configure(width=180)

        actions = tk.Frame(header, bg=self.palette["surface"])
        actions.grid(row=0, column=1, sticky="e")
        ttkb.Button(
            actions,
            text="Capture (Ctrl+Shift+A)",
            bootstyle="warning",
            command=self.capture_screen,
            width=24,
        ).pack(anchor="e", pady=(0, 6))
        row = tk.Frame(actions, bg=self.palette["surface"])
        row.pack(anchor="e")
        ttkb.Button(
            row,
            text="Settings",
            bootstyle="secondary",
            command=self.open_settings,
            width=10,
        ).pack(side=LEFT, padx=(0, 6))
        ttkb.Button(
            row,
            text="Focus Preview",
            bootstyle="outline",
            command=self._focus_preview,
            width=12,
        ).pack(side=LEFT)

        status_row = tk.Frame(self.content, bg=self.palette["surface"])
        status_row.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        status_row.columnconfigure(0, weight=1)
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(
            status_row,
            textvariable=self.status_var,
            font=self.font_body,
            bg=self.palette["surface"],
            fg=self.palette["accent_alt"],
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        self.progress = ttkb.Progressbar(
            status_row, mode="indeterminate", length=180
        )
        self.progress.grid(row=0, column=1, sticky="e", padx=(10, 0))

        cards = tk.Frame(self.content, bg=self.palette["surface"])
        cards.grid(row=2, column=0, sticky="nsew", padx=10, pady=(12, 10))
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)
        cards.rowconfigure(0, weight=1)

        image_card, image_body = self._make_card(
            cards,
            "Captured Region",
            "Drag to select the formula area for OCR.",
        )
        image_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.image_body = image_body
        self.image_label = tk.Label(
            image_body,
            text="No screenshot yet",
            bg=self.palette["card_bg"],
            fg=self.palette["muted"],
            font=self.font_body,
        )
        self.image_label.pack(fill=BOTH, expand=True, padx=12, pady=12)

        preview_card, preview_body = self._make_card(
            cards,
            "KaTeX Preview",
            "Preview is rendered in a separate window.",
        )
        preview_card.grid(row=0, column=1, sticky="nsew")
        self.preview_body = preview_body
        self.preview_status = tk.Label(
            preview_body,
            text="Waiting for OCR result.",
            bg=self.palette["card_bg"],
            fg=self.palette["muted"],
            font=self.font_body,
            wraplength=360,
            justify="left",
        )
        self.preview_status.pack(fill=BOTH, expand=True, padx=12, pady=12)

        editor_card, editor_body = self._make_card(
            self.content,
            "LaTeX Output",
            "Edit the formula before copying to your document.",
        )
        editor_card.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.editor_body = editor_body

        action_row = tk.Frame(editor_body, bg=self.palette["card_bg"])
        action_row.pack(fill=X, padx=12, pady=(6, 0))
        ttkb.Button(
            action_row,
            text="Copy LaTeX",
            bootstyle="success",
            command=self.copy_latex,
        ).pack(side=LEFT, padx=(0, 6))
        ttkb.Button(
            action_row,
            text="Copy MathML",
            bootstyle="primary",
            command=self.copy_mathml,
        ).pack(side=LEFT, padx=(0, 6))

        text_frame = tk.Frame(editor_body, bg=self.palette["card_bg"])
        text_frame.pack(fill=BOTH, expand=True, padx=12, pady=10)

        scrollbar = ttkb.Scrollbar(text_frame, orient="vertical")
        self.latex_text = tk.Text(
            text_frame,
            height=10,
            wrap="word",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.latex_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.latex_text.pack(side=tk.LEFT, fill=BOTH, expand=True)
        self.latex_text.configure(
            font=self.font_mono,
            bg="#fffaf1",
            fg=self.palette["text"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.palette["card_border"],
            insertbackground=self.palette["accent_alt"],
        )
        self._stagger_reveal([image_card, preview_card, editor_card])

    def _on_canvas_resize(self, event):
        self.bg_canvas.delete("bg")
        self._draw_gradient(event.width, event.height)
        self.bg_canvas.tag_lower("bg")
        pad = 16
        width = max(1, event.width - pad * 2)
        height = max(1, event.height - pad * 2)
        self.bg_canvas.coords(self.bg_window, pad, pad)
        self.bg_canvas.itemconfigure(self.bg_window, width=width, height=height)

    def _draw_gradient(self, width, height):
        steps = 120
        for step in range(steps):
            ratio = step / max(1, steps - 1)
            color = self._blend_color(
                self.palette["bg_start"], self.palette["bg_end"], ratio
            )
            y1 = int(height * step / steps)
            y2 = int(height * (step + 1) / steps)
            self.bg_canvas.create_rectangle(
                0, y1, width, y2, outline="", fill=color, tags=("bg",)
            )
        for x in range(0, width, 160):
            for y in range(0, height, 160):
                self.bg_canvas.create_oval(
                    x + 22,
                    y + 26,
                    x + 28,
                    y + 32,
                    outline="",
                    fill=self.palette["pattern"],
                    tags=("bg",),
                )

    def _blend_color(self, start_hex, end_hex, ratio):
        start_hex = start_hex.lstrip("#")
        end_hex = end_hex.lstrip("#")
        sr, sg, sb = (
            int(start_hex[0:2], 16),
            int(start_hex[2:4], 16),
            int(start_hex[4:6], 16),
        )
        er, eg, eb = (
            int(end_hex[0:2], 16),
            int(end_hex[2:4], 16),
            int(end_hex[4:6], 16),
        )
        rr = int(sr + (er - sr) * ratio)
        rg = int(sg + (eg - sg) * ratio)
        rb = int(sb + (eb - sb) * ratio)
        return f"#{rr:02x}{rg:02x}{rb:02x}"

    def _make_card(self, parent, title, subtitle):
        card = tk.Frame(
            parent,
            bg=self.palette["card_bg"],
            highlightthickness=1,
            highlightbackground=self.palette["card_border"],
        )
        header = tk.Frame(card, bg=self.palette["card_bg"])
        header.pack(fill=X, padx=12, pady=(10, 0))
        tk.Label(
            header,
            text=title,
            font=self.font_card_title,
            bg=self.palette["card_bg"],
            fg=self.palette["text"],
        ).pack(anchor="w")
        if subtitle:
            tk.Label(
                header,
                text=subtitle,
                font=self.font_body,
                bg=self.palette["card_bg"],
                fg=self.palette["muted"],
            ).pack(anchor="w", pady=(2, 0))
        divider = tk.Frame(card, bg=self.palette["card_border"], height=1)
        divider.pack(fill=X, padx=12, pady=(8, 0))
        body = tk.Frame(card, bg=self.palette["card_bg"])
        body.pack(fill=BOTH, expand=True)
        return card, body

    def _stagger_reveal(self, widgets):
        # Staggered reveal softens the initial load without heavy animation.
        for widget in widgets:
            widget.grid_remove()
        for index, widget in enumerate(widgets):
            self.root.after(120 * (index + 1), widget.grid)

    def _start_preview(self):
        html_path = resource_path("assets/katex_preview.html")
        if not html_path.exists():
            self.set_status("Preview HTML is missing.")
            return
        self.preview = PreviewWindow(str(html_path))
        self.preview_status.configure(text="Opening preview window...")

    def _start_hotkey(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        hotkey = self.settings.data.get("hotkey", DEFAULT_CONFIG["hotkey"])
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(
                {hotkey: lambda: self.root.after(0, self.capture_screen)}
            )
            self.hotkey_listener.start()
        except Exception as exc:
            self.set_status(f"Hotkey error: {exc}")

    def set_status(self, text):
        self.status_var.set(text)

    def capture_screen(self):
        self.preview_status.configure(text="Waiting for capture...")
        selector = RegionSelector(self.root)
        bbox = selector.select()
        if not bbox:
            self.set_status("Capture canceled.")
            self.preview_status.configure(text="Capture canceled.")
            return
        image = ImageGrab.grab(bbox=bbox)
        self.current_image = image
        self._update_image_preview(image)
        self._run_ocr(image)

    def _update_image_preview(self, image):
        preview = image.copy()
        max_width = self.image_body.winfo_width() - 24
        max_height = self.image_body.winfo_height() - 24
        if max_width < 240 or max_height < 160:
            max_width, max_height = 620, 420
        preview.thumbnail((max_width, max_height))
        self.preview_image = ImageTk.PhotoImage(preview)
        self.image_label.configure(image=self.preview_image, text="")

    def _run_ocr(self, image):
        api_url = self.settings.data.get("api_base_url", "").strip()
        api_key = self.settings.data.get("api_key", "").strip()
        model = self.settings.data.get("api_model", "").strip()
        if not api_url or not api_key or not model:
            self.set_status("Missing API settings.")
            self.open_settings()
            return

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")

        self.progress.start(10)
        self.set_status("OCR in progress...")
        self.preview_status.configure(text="Rendering after OCR...")

        def worker():
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Please transcribe it into LaTeX format. "
                                    "please only return LaTeX formula without any "
                                    "other unuseful symbol, so I can patse it to my "
                                    "doc directly."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                            },
                        ],
                    }
                ],
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            try:
                resp = requests.post(api_url, json=payload, headers=headers, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                latex = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                latex = strip_latex_markers(latex)
                self.root.after(0, lambda: self._on_ocr_success(latex))
            except Exception as exc:
                self.root.after(0, lambda: self._on_ocr_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ocr_success(self, latex):
        self.progress.stop()
        self._set_latex_text(latex)
        self.set_status("OCR complete.")
        if self.preview:
            self.preview.set_latex(latex)
        self.preview_status.configure(text="Preview updated.")
        if self.settings.data.get("copy_format") == "mathml":
            self.copy_mathml()
        else:
            self.copy_latex()

    def _on_ocr_error(self, message):
        self.progress.stop()
        self.set_status(f"OCR error: {message}")
        self.preview_status.configure(text="OCR failed. Check settings.")
        messagebox.showerror("OCR error", message)

    def _set_latex_text(self, latex):
        self.latex_text_value = latex or ""
        self.latex_text.delete("1.0", tk.END)
        self.latex_text.insert("1.0", self.latex_text_value)

    def copy_latex(self):
        latex = self._get_current_latex()
        if not latex:
            self.set_status("No LaTeX to copy.")
            return
        self._copy_to_clipboard(latex)
        self.set_status("LaTeX copied.")

    def copy_mathml(self):
        latex = self._get_current_latex()
        if not latex:
            self.set_status("No LaTeX to convert.")
            return
        if not self.preview:
            self.set_status("Preview not available.")
            return
        mathml = self.preview.get_mathml(latex)
        if not mathml:
            self.set_status("MathML not ready.")
            return
        self._copy_to_clipboard(mathml)
        self.set_status("MathML copied.")

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _get_current_latex(self):
        content = self.latex_text.get("1.0", tk.END).strip()
        return content

    def open_settings(self):
        win = ttkb.Toplevel(self.root)
        win.title("Settings")
        win.geometry("640x380")
        win.minsize(600, 360)
        win.transient(self.root)
        win.configure(background=self.palette["surface"])

        frame = tk.Frame(win, bg=self.palette["surface"])
        frame.pack(fill=BOTH, expand=True, padx=14, pady=14)

        title = tk.Label(
            frame,
            text="API & Copy Settings",
            font=self.font_card_title,
            bg=self.palette["surface"],
            fg=self.palette["text"],
        )
        title.pack(anchor="w", pady=(0, 8))

        api_url_var = tk.StringVar(value=self.settings.data.get("api_base_url", ""))
        api_key_var = tk.StringVar(value=self.settings.data.get("api_key", ""))
        api_model_var = tk.StringVar(value=self.settings.data.get("api_model", ""))
        copy_format_var = tk.StringVar(
            value=self.settings.data.get("copy_format", "latex")
        )
        hotkey_var = tk.StringVar(value=self.settings.data.get("hotkey", ""))

        self._add_field(frame, "API Base URL", api_url_var)
        self._add_field(frame, "API Key", api_key_var, show="*")
        self._add_field(frame, "Model", api_model_var)

        tk.Label(
            frame,
            text="Copy Format",
            font=self.font_body,
            bg=self.palette["surface"],
            fg=self.palette["text"],
        ).pack(anchor="w", pady=(6, 0))
        copy_combo = ttkb.Combobox(
            frame,
            textvariable=copy_format_var,
            values=["latex", "mathml"],
            state="readonly",
        )
        copy_combo.pack(fill=X)

        self._add_field(frame, "Hotkey", hotkey_var)
        tk.Label(
            frame,
            text="Hotkey format example: <ctrl>+<shift>+a",
            font=("Trebuchet MS", 9),
            bg=self.palette["surface"],
            fg=self.palette["muted"],
        ).pack(anchor="w", pady=(4, 0))

        button_row = tk.Frame(frame, bg=self.palette["surface"])
        button_row.pack(fill=X, pady=(14, 0))

        ttkb.Button(
            button_row,
            text="Save",
            command=lambda: self._save_settings(
                win,
                api_url_var.get(),
                api_key_var.get(),
                api_model_var.get(),
                copy_format_var.get(),
                hotkey_var.get(),
            ),
        ).pack(side=LEFT)

        ttkb.Button(
            button_row, text="Cancel", command=win.destroy
        ).pack(side=LEFT, padx=(6, 0))

    def _add_field(self, parent, label, variable, show=None):
        tk.Label(
            parent,
            text=label,
            font=self.font_body,
            bg=self.palette["surface"],
            fg=self.palette["text"],
        ).pack(anchor="w", pady=(6, 0))
        entry = ttkb.Entry(parent, textvariable=variable, show=show)
        entry.pack(fill=X)

    def _save_settings(self, win, api_url, api_key, model, copy_format, hotkey):
        self.settings.data["api_base_url"] = api_url.strip()
        self.settings.data["api_key"] = api_key.strip()
        self.settings.data["api_model"] = model.strip() or DEFAULT_CONFIG["api_model"]
        self.settings.data["copy_format"] = copy_format
        self.settings.data["hotkey"] = hotkey.strip() or DEFAULT_CONFIG["hotkey"]
        self.settings.save()
        self._start_hotkey()
        self.set_status("Settings saved.")
        win.destroy()

    def _focus_preview(self):
        if self.preview:
            self.preview.bring_to_front()

    def on_exit(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        if self.preview:
            self.preview.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    mp.freeze_support()
    app = LatexOCRApp()
    app.run()


if __name__ == "__main__":
    main()
