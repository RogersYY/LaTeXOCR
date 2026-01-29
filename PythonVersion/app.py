import base64
import json
import os
import re
import sys
import threading
from pathlib import Path

import requests
from pynput import keyboard
from PySide6 import QtCore, QtGui, QtWidgets, QtWebEngineCore, QtWebEngineWidgets


DEFAULT_CONFIG = {
    "api_base_url": "",
    "api_key": "",
    "api_model": "gpt-5.2",
    "copy_format": "latex",
    "hotkey": "<ctrl>+<shift>+A",
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


class SignalBus(QtCore.QObject):
    ocr_success = QtCore.Signal(str)
    ocr_error = QtCore.Signal(str)
    status_update = QtCore.Signal(str)


class SelectionOverlay(QtWidgets.QWidget):
    selection_made = QtCore.Signal(QtGui.QImage)
    selection_canceled = QtCore.Signal()

    def __init__(self, screen):
        super().__init__(None)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setCursor(QtCore.Qt.CrossCursor)
        self.setMouseTracking(True)

        self.screen = screen
        self.screen_geometry = screen.geometry()
        self.setGeometry(self.screen_geometry)
        self.pixmap = screen.grabWindow(0)
        self.origin = None
        self.rubber_band = QtWidgets.QRubberBand(
            QtWidgets.QRubberBand.Rectangle, self
        )

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        painter.fillRect(self.rect(), QtGui.QColor(15, 23, 42, 90))
        painter.setPen(QtGui.QColor(255, 255, 255, 200))
        painter.setFont(QtGui.QFont("Segoe UI", 12, QtGui.QFont.Bold))
        painter.drawText(
            QtCore.QRect(24, 20, 480, 40),
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            "Drag to select area (Esc to cancel)",
        )

    def mousePressEvent(self, event):
        self.origin = event.pos()
        self.rubber_band.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
        self.rubber_band.show()

    def mouseMoveEvent(self, event):
        if self.origin is None:
            return
        rect = QtCore.QRect(self.origin, event.pos()).normalized()
        self.rubber_band.setGeometry(rect)

    def mouseReleaseEvent(self, event):
        if self.origin is None:
            self.cancel()
            return
        rect = QtCore.QRect(self.origin, event.pos()).normalized()
        if rect.width() < 4 or rect.height() < 4:
            self.cancel()
            return
        self.rubber_band.hide()
        dpr = self.pixmap.devicePixelRatio()
        rect_px = QtCore.QRect(
            int(rect.x() * dpr),
            int(rect.y() * dpr),
            int(rect.width() * dpr),
            int(rect.height() * dpr),
        )
        selected = self.pixmap.copy(rect_px)
        image = selected.toImage()
        self.selection_made.emit(image)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.cancel()

    def cancel(self):
        self.rubber_band.hide()
        self.selection_canceled.emit()
        self.close()


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(520, 320)
        self.settings = settings

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)

        self.api_url = QtWidgets.QLineEdit(settings.data.get("api_base_url", ""))
        self.api_url.setPlaceholderText("https://api.openai.com/v1")
        self.api_key = QtWidgets.QLineEdit(settings.data.get("api_key", ""))
        self.api_key.setEchoMode(QtWidgets.QLineEdit.Password)
        current_model = settings.data.get("api_model", "gpt-5.2").strip() or "gpt-5.2"
        self.api_model_combo = QtWidgets.QComboBox()
        self.api_model_combo.addItems(["gpt-5.2", "其他"])
        self.api_model_custom = QtWidgets.QLineEdit()
        self.api_model_custom.setPlaceholderText("输入自定义模型名")
        if current_model in ("gpt-5.2", "其他"):
            self.api_model_combo.setCurrentText(current_model)
        else:
            self.api_model_combo.setCurrentText("其他")
            self.api_model_custom.setText(current_model)
        self._toggle_custom_model()
        self.api_model_combo.currentTextChanged.connect(self._toggle_custom_model)
        self.copy_format = QtWidgets.QComboBox()
        self.copy_format.addItems(["latex", "mathml"])
        self.copy_format.setCurrentText(settings.data.get("copy_format", "latex"))
        self.hotkey = QtWidgets.QLineEdit(settings.data.get("hotkey", ""))

        form.addRow("API Base URL", self.api_url)
        form.addRow("API Key", self.api_key)
        model_row = QtWidgets.QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.setSpacing(6)
        self.api_model_combo.setFixedWidth(120)
        model_row.addWidget(self.api_model_combo)
        model_row.addWidget(self.api_model_custom, 1)
        model_container = QtWidgets.QWidget()
        model_container.setLayout(model_row)
        form.addRow("Model", model_container)
        form.addRow("Copy Format", self.copy_format)
        form.addRow("Hotkey", self.hotkey)

        api_hint = QtWidgets.QLabel("API Base URL 填到 /v1 即可，例如: https://api.openai.com/v1")
        api_hint.setStyleSheet("color: #6b7280;")
        layout.addWidget(api_hint)

        hint = QtWidgets.QLabel("Hotkey example: <ctrl>+<shift>+a")
        hint.setStyleSheet("color: #6b7280;")
        layout.addWidget(hint)

        button_row = QtWidgets.QHBoxLayout()
        layout.addLayout(button_row)
        button_row.addStretch()
        save_btn = QtWidgets.QPushButton("Save")
        cancel_btn = QtWidgets.QPushButton("Cancel")
        button_row.addWidget(save_btn)
        button_row.addWidget(cancel_btn)
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def get_values(self):
        selected = self.api_model_combo.currentText().strip()
        if selected == "其他":
            model_value = self.api_model_custom.text().strip()
        else:
            model_value = selected
        if not model_value:
            model_value = "gpt-5.2"
        return {
            "api_base_url": self.api_url.text().strip(),
            "api_key": self.api_key.text().strip(),
            "api_model": model_value,
            "copy_format": self.copy_format.currentText().strip(),
            "hotkey": self.hotkey.text().strip(),
        }

    def _toggle_custom_model(self):
        is_custom = self.api_model_combo.currentText().strip() == "其他"
        self.api_model_custom.setEnabled(is_custom)


def normalize_base_url(url):
    normalized = url.strip()
    while normalized.endswith("/"):
        normalized = normalized[:-1]
    if normalized.endswith("/responses"):
        normalized = normalized[: -len("/responses")]
    return normalized


def extract_output_text(output):
    parts = []
    for item in output or []:
        content = item.get("content", [])
        for content_item in content:
            if content_item.get("type") == "output_text":
                text = content_item.get("text", "")
                if text:
                    parts.append(text)
    return "\n".join(parts)


class LatexOCRWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = AppSettings()
        self.signals = SignalBus()
        self.http_session = requests.Session()

        self.setWindowTitle("LaTeXOCR for 415课题组")
        self.resize(1120, 620)
        self.setMinimumSize(960, 520)
        icon_path = resource_path("assets/icon.png")
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))

        self.hotkey_listener = None
        self.preview_ready = False
        self.current_image = None
        self._pending_preview_text = ""
        self.preview_timer = QtCore.QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._refresh_preview_from_editor)
        self.output_hint_timer = QtCore.QTimer(self)
        self.output_hint_timer.setSingleShot(True)
        self.output_hint_timer.timeout.connect(self._clear_output_hint)
        self.status_timer = QtCore.QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self._clear_status_label)

        self._build_ui()
        self._apply_styles()
        self._connect_signals()
        self._start_hotkey()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QtWidgets.QFrame()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(header)

        title_box = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("LaTeXOCR for 415课题组")
        title.setObjectName("Title")
        title_box.addWidget(title)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        action_box = QtWidgets.QVBoxLayout()
        self.capture_btn = QtWidgets.QPushButton(self._capture_label())
        self.capture_btn.setObjectName("PrimaryButton")
        action_row = QtWidgets.QHBoxLayout()
        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMaximum(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setFixedWidth(80)
        self.progress.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        self.progress.setVisible(False)
        action_row.addWidget(self.progress)
        action_row.addSpacing(8)
        action_row.addWidget(self.capture_btn)
        action_row.addWidget(self.settings_btn)
        action_box.addLayout(action_row)
        header_layout.addLayout(action_box)

        main_row = QtWidgets.QHBoxLayout()
        layout.addLayout(main_row, 2)

        self.image_card = self._make_card("Captured Region")
        self.image_label = QtWidgets.QLabel("No screenshot yet.")
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setObjectName("PreviewLabel")
        self.image_label.setStyleSheet("background: #ffffff;")
        self.image_card["body"].layout().addWidget(self.image_label)
        self.image_card["frame"].setMinimumWidth(260)
        self.image_card["frame"].setMinimumHeight(200)
        self.image_card["frame"].setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding
        )
        main_row.addWidget(self.image_card["frame"], 1)

        self.preview_card = self._make_card("KaTeX Preview")
        self.webview = QtWebEngineWidgets.QWebEngineView()
        html_path = resource_path("assets/katex_preview.html")
        self.webview.setUrl(QtCore.QUrl.fromLocalFile(str(html_path)))
        self.webview.settings().setAttribute(
            QtWebEngineCore.QWebEngineSettings.ShowScrollBars, False
        )
        self.preview_card["body"].layout().addWidget(self.webview)
        self.preview_card["frame"].setMinimumHeight(200)
        self.preview_card["frame"].setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        main_row.addWidget(self.preview_card["frame"], 1)
        main_row.setStretch(0, 1)
        main_row.setStretch(1, 1)

        self.output_card = self._make_card("LaTeX Output")
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.output_card["header_layout"].addWidget(
            self.status_label, 0, 1, alignment=QtCore.Qt.AlignCenter
        )
        output_layout = self.output_card["body"].layout()
        self.output_hint = QtWidgets.QLabel("")
        self.output_hint.setObjectName("OutputHint")
        self.output_hint.setVisible(False)
        output_layout.addWidget(self.output_hint)
        output_layout.setSpacing(4)
        self.copy_latex_btn = QtWidgets.QPushButton("Copy LaTeX")
        self.copy_mathml_btn = QtWidgets.QPushButton("Copy MathML")
        buttons_container = QtWidgets.QWidget()
        buttons_container.setObjectName("OutputButtonRow")
        button_row = QtWidgets.QHBoxLayout(buttons_container)
        button_row.setContentsMargins(8, 4, 8, 4)
        button_row.setSpacing(8)
        button_row.addStretch()
        button_row.addWidget(self.copy_latex_btn)
        button_row.addWidget(self.copy_mathml_btn)
        button_row.addStretch()
        output_layout.addWidget(buttons_container)
        self.latex_text = QtWidgets.QTextEdit()
        self.latex_text.setObjectName("LatexText")
        self.latex_text.setMinimumHeight(80)
        output_layout.addWidget(self.latex_text, 1)
        self.output_card["frame"].setMaximumHeight(280)
        layout.addWidget(self.output_card["frame"], 2)

        self.capture_btn.clicked.connect(self.capture_screen)
        self.settings_btn.clicked.connect(self.open_settings)
        self.copy_latex_btn.clicked.connect(self.copy_latex)
        self.copy_mathml_btn.clicked.connect(self.copy_mathml)
        self.webview.loadFinished.connect(self._on_preview_loaded)
        self.latex_text.textChanged.connect(self._schedule_preview_update)

    def _make_card(self, title, subtitle=""):
        frame = QtWidgets.QFrame()
        frame.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(4)

        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("CardTitle")
        title_stack = QtWidgets.QVBoxLayout()
        title_stack.setContentsMargins(0, 0, 0, 0)
        title_stack.setSpacing(2)
        title_stack.addWidget(title_label)
        subtitle_label = None
        if subtitle:
            subtitle_label = QtWidgets.QLabel(subtitle)
            subtitle_label.setObjectName("CardSubtitle")
            title_stack.addWidget(subtitle_label)

        header = QtWidgets.QWidget()
        header.setObjectName("CardHeader")
        header_layout = QtWidgets.QGridLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setColumnStretch(0, 1)
        header_layout.setColumnStretch(1, 1)
        header_layout.setColumnStretch(2, 1)
        title_container = QtWidgets.QWidget()
        title_container.setLayout(title_stack)
        header_layout.addWidget(title_container, 0, 0, alignment=QtCore.Qt.AlignLeft)

        body = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(6)

        layout.addWidget(header)
        layout.addWidget(body, 1)
        return {"frame": frame, "body": body, "header_layout": header_layout}

    def _apply_styles(self):
        font = QtGui.QFont()
        if os.name == "nt":
            font.setFamily("Segoe UI")
        else:
            font.setFamily("Avenir Next")
        font.setPointSize(11)
        self.setFont(font)

        style = """
        QWidget {
            background: #fbf1e4;
            color: #1f2937;
        }
        QFrame#Card {
            background: #ffffff;
            border: 1px solid #ead3bf;
            border-radius: 14px;
        }
        QWidget#CardHeader {
            background: #ffffff;
        }
        QLabel#Title {
            font-size: 30px;
            font-weight: 600;
        }
        QLabel#Subtitle {
            color: #6b7280;
        }
        QLabel#CardTitle {
            font-size: 14px;
            font-weight: 600;
            background: #ffffff;
        }
        QLabel#CardSubtitle {
            color: #6b7280;
            background: #ffffff;
        }
        QLabel#StatusLabel {
            color: #0f766e;
            font-weight: 600;
            background: #ffffff;
        }
        QWidget#StatusContainer {
            background: transparent;
        }
        QPushButton {
            padding: 8px 14px;
            border-radius: 8px;
            border: 1px solid #e7d5c4;
            background: #fff8ee;
        }
        QPushButton#PrimaryButton {
            background: #d97706;
            color: white;
            border: none;
            font-weight: 600;
        }
        QTextEdit#LatexText {
            background: #ffffff;
            border: 1px solid #ead3bf;
            border-radius: 8px;
        }
        QLabel#OutputHint {
            color: #9a3412;
            font-weight: 600;
            background: #ffffff;
        }
        QWidget#OutputButtonRow {
            background: #ffffff;
            border-radius: 0px;
        }
        """
        self.setStyleSheet(style)

    def _connect_signals(self):
        self.signals.ocr_success.connect(self._on_ocr_success)
        self.signals.ocr_error.connect(self._on_ocr_error)
        self.signals.status_update.connect(self._set_status)

    def _start_hotkey(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        hotkey = self.settings.data.get("hotkey", DEFAULT_CONFIG["hotkey"])
        emitter = self.signals

        def trigger():
            QtCore.QMetaObject.invokeMethod(
                self, "capture_screen", QtCore.Qt.QueuedConnection
            )
            emitter.status_update.emit("Capturing...")

        try:
            self.hotkey_listener = keyboard.GlobalHotKeys({hotkey: trigger})
            self.hotkey_listener.start()
            self.capture_btn.setText(self._capture_label())
        except Exception as exc:
            self._set_status(f"Hotkey error: {exc}")

    @QtCore.Slot()
    def capture_screen(self):
        screen = QtGui.QGuiApplication.screenAt(QtGui.QCursor.pos())
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
        self._set_status("Drag to select area (Esc to cancel).")
        overlay = SelectionOverlay(screen)
        loop = QtCore.QEventLoop()
        result = {"image": None}

        def on_done(image):
            result["image"] = image
            loop.quit()

        def on_cancel():
            loop.quit()

        overlay.selection_made.connect(on_done)
        overlay.selection_canceled.connect(on_cancel)
        overlay.showFullScreen()
        overlay.activateWindow()
        loop.exec()

        image = result["image"]
        if image is None:
            self._set_status("Capture canceled.")
            return
        self.current_image = image
        self._update_image_preview(image)
        self._run_ocr(image)

    def _update_image_preview(self, image):
        pixmap = QtGui.QPixmap.fromImage(image)
        target = self.image_label.size()
        if target.width() <= 0 or target.height() <= 0:
            target = QtCore.QSize(520, 360)
        scaled = pixmap.scaled(
            target, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def _run_ocr(self, image):
        api_url = self.settings.data.get("api_base_url", "").strip()
        api_key = self.settings.data.get("api_key", "").strip()
        model = self.settings.data.get("api_model", "").strip()
        if not api_url or not api_key or not model:
            self._set_status("Missing API settings.")
            self.open_settings()
            return

        self._set_status("OCR in progress...")
        self.progress.setVisible(True)

        def worker():
            buffer = QtCore.QBuffer()
            buffer.open(QtCore.QIODevice.ReadWrite)
            image.save(buffer, "JPG", quality=90)
            image_b64 = base64.b64encode(buffer.data()).decode("ascii")
            base_url = normalize_base_url(api_url)
            request_url = f"{base_url}/responses"
            payload = {
                "model": model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "Please transcribe it into LaTeX format. "
                                    "please only return LaTeX formula without any "
                                    "other unuseful symbol, so I can patse it to my "
                                    "doc directly."
                                ),
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{image_b64}",
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
                resp = self.http_session.post(
                    request_url, json=payload, headers=headers, timeout=60
                )
                resp.raise_for_status()
                data = resp.json()
                latex = extract_output_text(data.get("output", []))
                latex = strip_latex_markers(latex)
                self.signals.ocr_success.emit(latex)
            except Exception as exc:
                self.signals.ocr_error.emit(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ocr_success(self, latex):
        self.progress.setVisible(False)
        self.latex_text.setPlainText(latex)
        self._set_status("OCR complete.")
        self._update_preview(latex)
        if self.settings.data.get("copy_format") == "mathml":
            self.copy_mathml()
        else:
            self.copy_latex()

    def _on_ocr_error(self, message):
        self.progress.setVisible(False)
        self._set_status(f"OCR error: {message}")
        QtWidgets.QMessageBox.critical(self, "OCR error", message)

    def _set_status(self, message, duration_ms=None):
        self.status_label.setText(message)
        if duration_ms:
            self.status_timer.start(duration_ms)
        else:
            self.status_timer.stop()

    def _update_preview(self, latex):
        if not self.preview_ready:
            return
        js = f"window.setLatex({json.dumps(latex)});"
        self.webview.page().runJavaScript(js)

    def _on_preview_loaded(self, ok):
        self.preview_ready = ok
        if ok:
            text = self._pending_preview_text or self.latex_text.toPlainText()
            self._update_preview(text)

    def _schedule_preview_update(self):
        self._pending_preview_text = self.latex_text.toPlainText()
        if self.preview_ready:
            self.preview_timer.start(250)

    def _refresh_preview_from_editor(self):
        text = self._pending_preview_text
        if text:
            self._update_preview(text)

    def _get_mathml(self, latex):
        if not self.preview_ready:
            return None
        loop = QtCore.QEventLoop()
        result = {"value": None}

        def handle(value):
            result["value"] = value
            loop.quit()

        js = f"window.getMathML({json.dumps(latex)});"
        self.webview.page().runJavaScript(js, handle)
        loop.exec()
        return result["value"]

    def copy_latex(self):
        latex = self.latex_text.toPlainText().strip()
        if not latex:
            self._set_status("No LaTeX to copy.", duration_ms=3000)
            return
        QtGui.QGuiApplication.clipboard().setText(latex)
        self._set_status("LaTeX copied.", duration_ms=3000)

    def copy_mathml(self):
        latex = self.latex_text.toPlainText().strip()
        if not latex:
            self._set_status("No LaTeX to convert.", duration_ms=3000)
            return
        mathml = self._get_mathml(latex)
        if not mathml:
            self._set_status("MathML not ready.", duration_ms=3000)
            return
        QtGui.QGuiApplication.clipboard().setText(mathml)
        self._set_status("MathML copied.", duration_ms=3000)

    def _show_output_hint(self, message, duration_ms=3000):
        self.output_hint.setText(message)
        self.output_hint.setVisible(True)
        self.output_hint_timer.start(duration_ms)

    def _clear_output_hint(self):
        self.output_hint_timer.stop()
        self.output_hint.setText("")
        self.output_hint.setVisible(False)

    def _clear_status_label(self):
        self.status_label.setText("")

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            values = dialog.get_values()
            self.settings.data.update(values)
            self.settings.save()
            self._start_hotkey()
            self._set_status("Settings saved.")

    def closeEvent(self, event):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        super().closeEvent(event)

    def _capture_label(self):
        hotkey = self.settings.data.get("hotkey", DEFAULT_CONFIG["hotkey"])
        display = hotkey.replace("<", "").replace(">", "")
        display = display.replace("+", "+").replace("ctrl", "Ctrl").replace(
            "shift", "Shift"
        ).replace("alt", "Alt").replace("cmd", "Cmd")
        return f"Capture ({display})"


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = LatexOCRWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
