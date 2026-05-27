import sys
import math
import random
import sqlite3
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QTimer, QEasingCurve, QPropertyAnimation
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen, QBrush, QLinearGradient, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import pygame as pg

BASE_DIR = Path(__file__).resolve().parent

# Цвета интерфейса. Можно менять здесь, если нужен другой оттенок.
BG_1 = "#090A10"
BG_2 = "#121018"
CARD = "rgba(255, 255, 255, 0.075)"
CARD_BORDER = "rgba(255, 255, 255, 0.14)"
TEXT = "#F4EEE8"
MUTED = "#B8AFA9"
ORANGE = "#FFB35C"
RED = "#EB3D50"
DARK_RED = "#421A22"


# ---------- Общие вспомогательные функции ----------

def read_text(relative_path: str, default: str = "") -> str:
    """Читает текстовый файл из папки проекта. Если файла нет, возвращает default."""
    path = BASE_DIR / relative_path
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default


def set_app_icon(window: QMainWindow) -> None:
    icon_path = BASE_DIR / "icon.png"
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))


def add_shadow(widget: QWidget, blur: int = 35, alpha: int = 130, y: int = 8) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


# ---------- Анимированный фон в стиле референса ----------

class AnimatedBackground(QWidget):
    """Темный фон с гитарой, аккордами, волной и эквалайзером.

    На экране практики декоративные волны отключаются, чтобы они не
    накладывались на текст, аккорды, бой и панель проигрывания.
    """

    def __init__(
        self,
        parent=None,
        *,
        show_wave: bool = True,
        show_chords: bool = True,
        show_equalizer: bool = True,
        particle_opacity: float = 1.0,
    ):
        super().__init__(parent)
        self.show_wave = show_wave
        self.show_chords = show_chords
        self.show_equalizer = show_equalizer
        self.particle_opacity = max(0.0, min(1.0, particle_opacity))
        self.phase = 0.0
        self.particles = [
            (random.random(), random.random(), random.uniform(0.4, 1.2), random.uniform(1.0, 2.8))
            for _ in range(70)
        ]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(35)

    def _tick(self):
        self.phase += 0.055
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0, QColor(BG_2))
        gradient.setColorAt(0.55, QColor(BG_1))
        gradient.setColorAt(1, QColor("#12070B"))
        painter.fillRect(self.rect(), gradient)

        self._draw_particles(painter, w, h)
        self._draw_guitar(painter, w, h)
        if self.show_chords:
            self._draw_chords(painter, w, h)
        if self.show_wave:
            self._draw_wave(painter, w, h)
        if self.show_equalizer:
            self._draw_equalizer(painter, w, h)

    def _draw_particles(self, p: QPainter, w: int, h: int) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        for x_ratio, y_ratio, speed, radius in self.particles:
            x = (x_ratio * w + math.sin(self.phase * speed + y_ratio * 10) * 10) % w
            y = y_ratio * h
            alpha = int((30 + 80 * abs(math.sin(self.phase * speed + x_ratio * 5))) * self.particle_opacity)
            p.setBrush(QColor(255, 125, 70, alpha))
            p.drawEllipse(QtCore.QPointF(x, y), radius, radius)

    def _draw_guitar(self, p: QPainter, w: int, h: int) -> None:
        # Корпус гитары слева, как декоративный элемент, без внешних картинок.
        x0 = -int(w * 0.22)
        y0 = int(h * 0.30)
        body_w = int(w * 0.42)
        body_h = int(h * 0.68)

        outline = QPen(QColor(255, 180, 110, 80), 2)
        p.setPen(outline)
        p.setBrush(QColor(255, 255, 255, 8))
        p.drawEllipse(x0, y0, body_w, body_h)
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawEllipse(x0 + int(body_w * 0.58), y0 + int(body_h * 0.35), int(body_w * 0.16), int(body_w * 0.16))

        # Гриф и струны.
        neck_x = int(w * 0.02)
        p.setPen(QPen(QColor(255, 255, 255, 45), 1))
        for i in range(6):
            x = neck_x + i * 15
            p.drawLine(x, 0, x + 40, h)
        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        for i in range(11):
            y = 15 + i * 47
            p.drawLine(0, y, int(w * 0.16), y)

    def _draw_chords(self, p: QPainter, w: int, h: int) -> None:
        p.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        chord_data = [("Em", 0.83, 0.18), ("C", 0.74, 0.38), ("G", 0.86, 0.62)]
        for name, xr, yr in chord_data:
            x, y = int(w * xr), int(h * yr)
            p.setPen(QPen(QColor(255, 255, 255, 32), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawText(x, y - 10, name)
            for i in range(5):
                p.drawLine(x, y + i * 10, x + 70, y + i * 10)
            for i in range(6):
                p.drawLine(x + i * 14, y, x + i * 14, y + 40)
            p.setBrush(QColor(255, 255, 255, 18))
            p.setPen(Qt.PenStyle.NoPen)
            for i in range(4):
                dot_x = x + 12 + (i * 17) % 58
                dot_y = y + 7 + (i * 11) % 32
                p.drawEllipse(QtCore.QPointF(dot_x, dot_y), 4, 4)

    def _draw_wave(self, p: QPainter, w: int, h: int) -> None:
        base_y = int(h * 0.74)
        start_x = int(w * 0.17)
        end_x = int(w * 0.70)
        p.setPen(QPen(QColor(255, 97, 54, 130), 2))
        last_point = None
        for x in range(start_x, end_x, 8):
            amp = 10 + 28 * abs(math.sin((x / 45.0) + self.phase * 1.4))
            y1 = base_y - amp / 2
            y2 = base_y + amp / 2
            p.drawLine(int(x), int(y1), int(x), int(y2))
            if last_point is not None:
                p.drawLine(last_point.x(), last_point.y(), x, base_y)
            last_point = QtCore.QPoint(int(x), int(base_y))

    def _draw_equalizer(self, p: QPainter, w: int, h: int) -> None:
        x0 = int(w * 0.86)
        y0 = int(h * 0.78)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(9):
            value = 10 + 40 * abs(math.sin(self.phase * 1.3 + i * 0.55))
            color = QColor(255, 107 + i * 7, 68, 120 + i * 8)
            p.setBrush(color)
            p.drawRect(x0 + i * 16, int(y0 - value), 9, int(value))
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(x0, y0 + 28, "уровень вдохновения")


class GlassCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setStyleSheet(f"""
            QFrame#glassCard {{
                background: {CARD};
                border: 1px solid {CARD_BORDER};
                border-radius: 24px;
            }}
        """)
        add_shadow(self, blur=32, alpha=90, y=10)


class GradientLabel(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        # Увеличенная высота нужна, чтобы крупный курсивный заголовок
        # не обрезался снизу и по бокам при отрисовке градиентом.
        self.setMinimumHeight(126)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont("Georgia", 72)
        font.setItalic(True)
        p.setFont(font)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#FFE0A4"))
        grad.setColorAt(0.45, QColor(ORANGE))
        grad.setColorAt(1.0, QColor(RED))
        p.setPen(QPen(QBrush(grad), 0))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class GlowButton(QPushButton):
    def __init__(self, text: str, kind: str = "secondary", parent=None):
        super().__init__(text, parent)
        self.kind = kind
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(64)
        self.setFont(QFont("Segoe UI", 18, QFont.Weight.Medium))
        self._apply_style(False)
        add_shadow(self, blur=24, alpha=90, y=6)

    def enterEvent(self, event):
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)

    def _apply_style(self, hover: bool):
        if self.kind == "primary":
            top = "#FFC76B" if hover else "#FFB35C"
            bottom = "#F0314E" if hover else "#E43A4A"
            border = "rgba(255, 226, 168, 0.75)" if hover else "rgba(255, 226, 168, 0.45)"
            self.setStyleSheet(f"""
                QPushButton {{
                    color: white;
                    border-radius: 22px;
                    border: 1px solid {border};
                    padding: 12px 22px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                stop:0 {top}, stop:0.48 #FF684A, stop:1 {bottom});
                }}
                QPushButton:pressed {{ padding-top: 15px; }}
            """)
        elif self.kind == "danger":
            self.setStyleSheet(f"""
                QPushButton {{
                    color: {TEXT};
                    border-radius: 22px;
                    border: 1px solid rgba(255, 105, 105, 0.36);
                    padding: 12px 22px;
                    background: rgba(255, 255, 255, 0.06);
                }}
                QPushButton:hover {{ background: rgba(235, 61, 80, 0.18); }}
                QPushButton:pressed {{ padding-top: 15px; }}
            """)
        else:
            bg = "rgba(255,255,255,0.105)" if hover else "rgba(255,255,255,0.06)"
            self.setStyleSheet(f"""
                QPushButton {{
                    color: {TEXT};
                    border-radius: 22px;
                    border: 1px solid rgba(255, 255, 255, 0.22);
                    padding: 12px 22px;
                    background: {bg};
                }}
                QPushButton:pressed {{ padding-top: 15px; }}
            """)


class FeatureCard(QFrame):
    def __init__(self, icon: str, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.setObjectName("featureCard")
        self.setStyleSheet(f"""
            QFrame#featureCard {{
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 22px;
            }}
            QLabel {{ color: {TEXT}; background: transparent; }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(16)

        icon_label = QLabel(icon)
        icon_label.setFixedSize(54, 54)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            QLabel {{
                color: {ORANGE};
                border: 1px solid rgba(255, 179, 92, 0.35);
                border-radius: 27px;
                font-size: 28px;
                background: rgba(255, 179, 92, 0.08);
            }}
        """)
        text_box = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        subtitle_label = QLabel(subtitle)
        subtitle_label.setFont(QFont("Segoe UI", 10))
        subtitle_label.setStyleSheet(f"color: {MUTED}; background: transparent;")
        text_box.addWidget(title_label)
        text_box.addWidget(subtitle_label)
        layout.addWidget(icon_label)
        layout.addLayout(text_box)


@dataclass(frozen=True)
class MenuBackgroundTrack:
    """Один фоновый трек главного меню."""

    title: str
    audio_path: Path
    cover_path: Optional[Path]


class MenuBackgroundMusic(QtCore.QObject):
    """Отдельный плеер фоновой музыки меню.

    Использует отдельный pygame Channel и не смешивается с pg.mixer.music,
    который применяется для основного трека в практике.
    """

    trackChanged = QtCore.pyqtSignal()
    volumeChanged = QtCore.pyqtSignal(int)

    MUSIC_DIR = BASE_DIR / "menu_background_music"
    COVER_DIR = BASE_DIR / "menu_background_covers"
    AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav")
    COVER_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.MUSIC_DIR.mkdir(exist_ok=True)
        self.COVER_DIR.mkdir(exist_ok=True)
        self.tracks: list[MenuBackgroundTrack] = []
        self.current_index: int = -1
        self.user_volume: float = 0.25
        self.context_factor: float = 1.0
        self.sound: Optional[pg.mixer.Sound] = None
        self.channel: Optional[pg.mixer.Channel] = None
        self.enabled = True
        self.scan_tracks()
        self.play_first_available()

    def scan_tracks(self) -> None:
        self.tracks = []
        try:
            files = sorted(
                path for path in self.MUSIC_DIR.iterdir()
                if path.is_file() and path.suffix.lower() in self.AUDIO_EXTENSIONS
            )
        except OSError as error:
            print(f"Не удалось открыть папку фоновой музыки: {error}")
            files = []

        for audio_path in files:
            cover_path = self._cover_for(audio_path.stem)
            self.tracks.append(
                MenuBackgroundTrack(
                    title=self._title_from_stem(audio_path.stem),
                    audio_path=audio_path,
                    cover_path=cover_path,
                )
            )

        if not self.tracks:
            self.current_index = -1
            self.sound = None
        elif self.current_index < 0 or self.current_index >= len(self.tracks):
            self.current_index = 0

    def play_first_available(self) -> None:
        if self.current_index >= 0:
            self.select_track(self.current_index, restart=False)
        else:
            print("Фоновая музыка меню не найдена. Добавь mp3/ogg/wav в menu_background_music.")
            self.trackChanged.emit()

    def select_track(self, index: int, restart: bool = True) -> None:
        if index < 0 or index >= len(self.tracks):
            return
        self.current_index = index
        track = self.tracks[index]
        try:
            self._ensure_mixer()
            if self.channel is None:
                self.channel = pg.mixer.Channel(1)
            self.sound = pg.mixer.Sound(str(track.audio_path))
            if restart or not self.channel.get_busy():
                self.channel.play(self.sound, loops=-1)
            self._apply_volume()
        except Exception as error:
            self.sound = None
            print(f"Ошибка фоновой музыки {track.audio_path}: {error}")
        self.trackChanged.emit()

    def set_context(self, context: str) -> None:
        if context == "main":
            self.context_factor = 1.0
            self.resume_if_possible()
        elif context == "choose":
            self.context_factor = 0.5
            self.resume_if_possible()
        elif context == "practice":
            self.context_factor = 0.0
            self.pause()
            return
        self._apply_volume()

    def set_user_volume_percent(self, value: int) -> None:
        self.user_volume = max(0.0, min(1.0, int(value) / 100))
        self._apply_volume()
        self.volumeChanged.emit(int(self.user_volume * 100))

    def current_track(self) -> Optional[MenuBackgroundTrack]:
        if 0 <= self.current_index < len(self.tracks):
            return self.tracks[self.current_index]
        return None

    def resume_if_possible(self) -> None:
        if not self.tracks:
            self.scan_tracks()
        if self.channel is not None and self.sound is not None:
            try:
                self.channel.unpause()
                if not self.channel.get_busy():
                    self.channel.play(self.sound, loops=-1)
            except Exception as error:
                print(f"Не удалось продолжить фоновую музыку: {error}")
        elif self.current_index >= 0:
            self.select_track(self.current_index, restart=False)

    def pause(self) -> None:
        if self.channel is not None:
            try:
                self.channel.pause()
            except Exception:
                pass

    def stop(self) -> None:
        if self.channel is not None:
            try:
                self.channel.stop()
            except Exception:
                pass

    def _apply_volume(self) -> None:
        if self.channel is None:
            return
        try:
            self.channel.set_volume(self.user_volume * self.context_factor)
        except Exception:
            pass

    def _ensure_mixer(self) -> None:
        if not pg.mixer.get_init():
            pg.mixer.init()

    def _cover_for(self, stem: str) -> Optional[Path]:
        for extension in self.COVER_EXTENSIONS:
            candidate = self.COVER_DIR / f"{stem}{extension}"
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _title_from_stem(stem: str) -> str:
        return stem.replace("_", " ").replace("-", " ").strip().title() or "Фоновый трек"


_MENU_BACKGROUND_MUSIC: Optional[MenuBackgroundMusic] = None


def get_menu_background_music() -> MenuBackgroundMusic:
    global _MENU_BACKGROUND_MUSIC
    if _MENU_BACKGROUND_MUSIC is None:
        _MENU_BACKGROUND_MUSIC = MenuBackgroundMusic()
    return _MENU_BACKGROUND_MUSIC


class CoverSquare(QLabel):
    """Маленькая обложка с безопасной заглушкой."""

    def __init__(self, size: int = 42, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            QLabel {{
                color: {ORANGE};
                background: rgba(0,0,0,0.22);
                border: 1px solid rgba(255,179,92,0.25);
                border-radius: 12px;
                font-size: 20px;
            }}
        """)
        self.setText("♪")

    def set_cover(self, cover_path: Optional[Path]) -> None:
        self.clear()
        if cover_path is not None:
            pixmap = QPixmap(str(cover_path))
            if not pixmap.isNull():
                self.setPixmap(
                    pixmap.scaled(
                        self.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        self.setText("♪")


class BackgroundMusicPopup(QFrame):
    """Небольшое glass-меню выбора фонового трека и громкости."""

    def __init__(self, manager: MenuBackgroundMusic, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.manager = manager
        self.setFixedWidth(330)
        self.setObjectName("backgroundMusicPopup")
        self.setStyleSheet(f"""
            QFrame#backgroundMusicPopup {{
                background: rgba(18, 16, 24, 235);
                border: 1px solid rgba(255,255,255,0.16);
                border-radius: 20px;
            }}
            QLabel {{ color: {TEXT}; background: transparent; }}
            QPushButton {{
                color: {TEXT};
                background: rgba(255,255,255,0.065);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 14px;
                padding: 10px 12px;
                text-align: left;
                font-family: 'Segoe UI';
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: rgba(255,179,92,0.16);
                border: 1px solid rgba(255,179,92,0.34);
            }}
        """)
        add_shadow(self, blur=26, alpha=110, y=8)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Фоновая музыка")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        layout.addWidget(title)

        self.manager.scan_tracks()
        if not self.manager.tracks:
            empty = QLabel("Файлы не найдены. Добавь треки в папку\nmenu_background_music")
            empty.setWordWrap(True)
            empty.setStyleSheet(f"color: {MUTED}; background: transparent; font-size: 12px;")
            layout.addWidget(empty)
        else:
            for index, track in enumerate(self.manager.tracks):
                button = QPushButton(track.title)
                button.setMinimumHeight(46)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                if track.cover_path is not None:
                    pixmap = QPixmap(str(track.cover_path))
                    if not pixmap.isNull():
                        button.setIcon(QIcon(pixmap))
                        button.setIconSize(QtCore.QSize(28, 28))
                if index == self.manager.current_index:
                    button.setStyleSheet(button.styleSheet() + f"background: rgba(255,179,92,0.16); border-color: rgba(255,179,92,0.38);")
                button.clicked.connect(lambda checked=False, i=index: self._select_track(i))
                layout.addWidget(button)

        volume_label = QLabel("Громкость фона")
        volume_label.setStyleSheet(f"color: {MUTED}; background: transparent; font-size: 12px;")
        layout.addWidget(volume_label)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(int(self.manager.user_volume * 100))
        self.volume_slider.setStyleSheet(self._slider_style())
        self.volume_slider.valueChanged.connect(self.manager.set_user_volume_percent)
        layout.addWidget(self.volume_slider)

    def _select_track(self, index: int) -> None:
        self.manager.select_track(index, restart=True)
        self.close()

    @staticmethod
    def _slider_style() -> str:
        return f"""
            QSlider::groove:horizontal {{
                height: 8px;
                border-radius: 4px;
                background: rgba(255,255,255,0.16);
            }}
            QSlider::handle:horizontal {{
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
                background: {ORANGE};
            }}
            QSlider::sub-page:horizontal {{
                border-radius: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 {ORANGE}, stop:1 {RED});
            }}
        """


class BackgroundMusicChip(GlassCard):
    """Плашка фонового трека в правом верхнем углу главного меню."""

    def __init__(self, manager: MenuBackgroundMusic, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(310, 66)
        self.setStyleSheet(f"""
            QFrame#glassCard {{
                background: rgba(255,255,255,0.075);
                border: 1px solid rgba(255,255,255,0.16);
                border-radius: 18px;
            }}
            QLabel {{ color: {TEXT}; background: transparent; }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 14, 10)
        layout.setSpacing(10)

        self.cover = CoverSquare(44)
        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self.caption = QLabel("Фон меню")
        self.caption.setStyleSheet(f"color: {MUTED}; background: transparent; font-size: 11px;")
        self.title = QLabel("Нет фонового трека")
        self.title.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.title.setStyleSheet(f"color: {TEXT}; background: transparent;")
        self.title.setWordWrap(False)
        text_box.addWidget(self.caption)
        text_box.addWidget(self.title)

        self.indicator = QLabel("♫")
        self.indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.indicator.setStyleSheet(f"color: {ORANGE}; background: transparent; font-size: 18px;")

        layout.addWidget(self.cover)
        layout.addLayout(text_box, 1)
        layout.addWidget(self.indicator)

        self.manager.trackChanged.connect(self.refresh)
        self.manager.volumeChanged.connect(lambda value: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        track = self.manager.current_track()
        if track is None:
            self.title.setText("Нет фонового трека")
            self.cover.set_cover(None)
            return
        self.title.setText(track.title)
        self.cover.set_cover(track.cover_path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._popup = BackgroundMusicPopup(self.manager, self)
            point = self.mapToGlobal(QtCore.QPoint(self.width() - self._popup.width(), self.height() + 8))
            self._popup.move(point)
            self._popup.show()
            event.accept()
            return
        super().mousePressEvent(event)


class ExitConfirmOverlay(QWidget):
    """Внутреннее подтверждение выхода без системного QMessageBox."""

    confirmed = QtCore.pyqtSignal()
    cancelled = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("exitConfirmOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#exitConfirmOverlay {
                background: rgba(0, 0, 0, 150);
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addStretch(1)

        card = GlassCard()
        card.setFixedWidth(560)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(42, 34, 42, 34)
        card_layout.setSpacing(18)

        title = QLabel("Выйти из приложения?")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 26, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {TEXT}; background: transparent;")

        text = QLabel("Вы действительно хотите выйти из приложения?")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        text.setFont(QFont("Segoe UI", 14))
        text.setStyleSheet(f"color: {MUTED}; background: transparent;")

        buttons = QHBoxLayout()
        buttons.setSpacing(16)
        self.cancel_button = GlowButton("Отмена", "secondary")
        self.cancel_button.setFixedWidth(210)
        self.confirm_button = GlowButton("Выйти", "danger")
        self.confirm_button.setFixedWidth(210)

        buttons.addStretch(1)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.confirm_button)
        buttons.addStretch(1)

        card_layout.addWidget(title)
        card_layout.addWidget(text)
        card_layout.addSpacing(8)
        card_layout.addLayout(buttons)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addStretch(1)

        self.cancel_button.clicked.connect(self.cancelled.emit)
        self.confirm_button.clicked.connect(self.confirmed.emit)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        # Overlay должен вести себя как модальное внутреннее окно и не
        # пропускать клики к кнопкам главного меню под ним.
        event.accept()


# ---------- Главное окно ----------

class LearnTheGuitar(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("learnWindow")
        self.setWindowTitle("Обучись гитаре")
        self.setFixedSize(1200, 720)
        set_app_icon(self)

        self.background_music = get_menu_background_music()
        self.background_music.set_context("main")

        self.bg = AnimatedBackground(self)
        self.setCentralWidget(self.bg)
        self.stack = QStackedWidget()

        root = QVBoxLayout(self.bg)
        root.setContentsMargins(60, 30, 60, 34)
        root.addWidget(self.stack)

        self.menu_page = QWidget()
        self.help_page = QWidget()
        self.stack.addWidget(self.menu_page)
        self.stack.addWidget(self.help_page)

        self._build_menu_page()
        self._build_help_page()

    def _build_menu_page(self):
        page = self.menu_page

        # Плашка фоновой музыки теперь лежит поверх контента в правом верхнем
        # углу и не занимает отдельную строку layout. Из-за этого заголовок
        # и кнопки можно поднять выше, не меняя позицию самой плашки.
        overlay = QGridLayout(page)
        overlay.setContentsMargins(0, 0, 0, 0)
        overlay.setSpacing(0)

        content = QWidget(page)
        content.setStyleSheet("background: transparent;")
        overlay.addWidget(content, 0, 0)

        self.background_chip = BackgroundMusicChip(self.background_music, page)
        overlay.addWidget(
            self.background_chip,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )

        self.exit_confirm_overlay = ExitConfirmOverlay(page)
        self.exit_confirm_overlay.hide()
        overlay.addWidget(self.exit_confirm_overlay, 0, 0)
        self.exit_confirm_overlay.cancelled.connect(self._hide_exit_confirmation)
        self.exit_confirm_overlay.confirmed.connect(self._confirm_exit)

        main = QVBoxLayout(content)
        main.setContentsMargins(0, 8, 0, 0)
        main.setSpacing(0)

        center = QVBoxLayout()
        center.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        center.setSpacing(8)

        title_top = QLabel("Обучись")
        title_top.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_top.setMinimumHeight(94)
        title_top.setFont(QFont("Georgia", 72, QFont.Weight.Normal))
        title_top.setStyleSheet(f"color: {TEXT}; background: transparent;")

        title_bottom = GradientLabel("гитаре")
        title_bottom.setMinimumHeight(126)

        subtitle = QLabel("Практикуйся. Играй. Создавай музыку.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setMinimumHeight(32)
        subtitle.setFont(QFont("Segoe UI", 17))
        subtitle.setStyleSheet(f"color: {MUTED}; background: transparent;")

        self.start_button = GlowButton("▶   Старт", "primary")
        self.start_button.setFixedWidth(470)
        self.help_button = GlowButton("▰   Помощь", "secondary")
        self.help_button.setFixedWidth(470)
        self.exit_button = GlowButton("↪   Выйти из приложения", "danger")
        self.exit_button.setFixedWidth(470)

        center.addWidget(title_top)
        center.addWidget(title_bottom)
        center.addWidget(subtitle)
        center.addSpacing(14)
        center.addWidget(self.start_button)
        center.addWidget(self.help_button)
        center.addWidget(self.exit_button)

        main.addLayout(center)
        main.addStretch(1)

        cards = QHBoxLayout()
        cards.setSpacing(18)
        cards.addWidget(FeatureCard("♬", "Изучай аккорды", "От простых к сложным"))
        cards.addWidget(FeatureCard("♪", "Освой любимые треки", "Практика на реальных песнях"))
        cards.addWidget(FeatureCard("▮", "Развивай ритм", "Шаг за шагом к мастерству"))
        main.addLayout(cards)

        self.start_button.clicked.connect(self.open_choose_screen)
        self.help_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.help_page))
        self.exit_button.clicked.connect(self.close_app)

    def _build_help_page(self):
        page = self.help_page
        layout = QVBoxLayout(page)
        layout.setContentsMargins(210, 90, 210, 90)
        layout.setSpacing(20)

        card = GlassCard()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(42, 36, 42, 36)
        card_layout.setSpacing(18)

        title = QLabel("Помощь")
        title.setFont(QFont("Segoe UI", 30, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {TEXT}; background: transparent;")

        help_text = read_text(
            "help_text.txt",
            "1) Выберите трек из списка и введите его ID.\n"
            "2) Отрегулируйте громкость.\n"
            "3) Используйте паузу и перемотку для повторения сложных мест."
        )
        self.help_text = QPlainTextEdit(help_text)
        self.help_text.setReadOnly(True)
        self.help_text.setMinimumHeight(250)
        self.help_text.setStyleSheet(self._text_edit_style())
        self.back_button = GlowButton("←   Назад", "secondary")
        self.back_button.setFixedWidth(220)
        self.back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.menu_page))

        card_layout.addWidget(title)
        card_layout.addWidget(self.help_text)
        card_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(card)

    def open_choose_screen(self):
        self.background_music.set_context("choose")
        self.next_window = ChooseScreen()
        self.next_window.show()
        self.close()

    def close_app(self):
        self._show_exit_confirmation()

    def _show_exit_confirmation(self):
        self.exit_confirm_overlay.show()
        self.exit_confirm_overlay.raise_()
        self.exit_confirm_overlay.setFocus(Qt.FocusReason.PopupFocusReason)

    def _hide_exit_confirmation(self):
        self.exit_confirm_overlay.hide()

    def _confirm_exit(self):
        self.background_music.stop()
        QApplication.quit()

    @staticmethod
    def _text_edit_style() -> str:
        return f"""
            QPlainTextEdit {{
                color: {TEXT};
                background: rgba(0,0,0,0.22);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 18px;
                padding: 18px;
                font-size: 17px;
                font-family: 'Segoe UI';
            }}
        """


# ---------- Окно выбора трека ----------

# Логический порядок сложности нужен, чтобы значения вроде
# «Легко / Средне / Сложно» не сортировались как обычный текст.
COMPLEXITY_WORD_ORDER = {
    "легко": 1,
    "легкая": 1,
    "легкий": 1,
    "легкое": 1,
    "средне": 2,
    "средняя": 2,
    "средний": 2,
    "среднее": 2,
    "сложно": 3,
    "сложная": 3,
    "сложный": 3,
    "сложное": 3,
}


def normalize_complexity(value: object) -> int | str:
    """Возвращает число для цифровой сложности и строку для словесной."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value).strip()


def complexity_rank(value: object) -> int:
    """Ключ сортировки сложности: числа сортируются как числа, слова — логически."""
    try:
        return int(value)
    except (TypeError, ValueError):
        normalized = str(value).strip().lower().replace("ё", "е")
        return COMPLEXITY_WORD_ORDER.get(normalized, 999)


@dataclass(frozen=True)
class Track:
    """Одна строка из базы Tracks в нормальном Python-виде."""

    id: int
    singer: str
    title: str
    duration: str
    complexity: int | str

    @classmethod
    def from_row(cls, row: Sequence[object]) -> "Track":
        return cls(
            id=int(row[0]),
            singer=str(row[1]).capitalize(),
            title=str(row[2]).capitalize(),
            duration=str(row[3]),
            complexity=normalize_complexity(row[4]),
        )


class TrackRepository:
    """Изолирует работу с SQLite, чтобы окно не смешивало GUI и SQL."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self) -> bool:
        if not self.db_path.exists():
            return False
        self.connection = sqlite3.connect(str(self.db_path))
        return True

    def all_tracks(self) -> list[Track]:
        if self.connection is None:
            return []
        rows = self.connection.execute(
            "SELECT id, singer, track_title, duration, complexity FROM Tracks ORDER BY id ASC"
        ).fetchall()
        return [Track.from_row(row) for row in rows]

    def get_track(self, track_id: int) -> Optional[Track]:
        if self.connection is None:
            return None
        row = self.connection.execute(
            "SELECT id, singer, track_title, duration, complexity FROM Tracks WHERE id = ?",
            (track_id,),
        ).fetchone()
        return Track.from_row(row) if row else None

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None


class SearchPanel(GlassCard):
    """Поиск с задержкой, чтобы таблица не перерисовывалась на каждую букву мгновенно."""

    searchChanged = QtCore.pyqtSignal(str)
    filterClicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(76)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(14)

        search_icon = QLabel("⌕")
        search_icon.setFixedSize(44, 44)
        search_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        search_icon.setStyleSheet(f"color: {ORANGE}; font-size: 34px; background: transparent;")

        self.line = QLineEdit()
        self.line.setPlaceholderText("Поиск по исполнителю или названию...")
        self.line.setMinimumHeight(54)
        self.line.setStyleSheet(self._line_edit_style())

        self.clear_button = GlowButton("×", "secondary")
        self.clear_button.setFixedSize(54, 54)
        self.clear_button.setToolTip("Очистить поиск")

        self.filter_button = GlowButton("☷", "secondary")
        self.filter_button.setFixedSize(68, 54)
        self.filter_button.setToolTip("Фильтр по сложности")

        layout.addWidget(search_icon)
        layout.addWidget(self.line, 1)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.filter_button)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(lambda: self.searchChanged.emit(self.line.text().strip()))

        self.line.textChanged.connect(lambda: self._debounce.start())
        self.line.returnPressed.connect(lambda: self.searchChanged.emit(self.line.text().strip()))
        self.clear_button.clicked.connect(self._clear)
        self.filter_button.clicked.connect(self.filterClicked.emit)

    def _clear(self):
        self.line.clear()
        self.searchChanged.emit("")

    @staticmethod
    def _line_edit_style() -> str:
        return f"""
            QLineEdit {{
                color: {TEXT};
                background: transparent;
                border: none;
                padding-left: 4px;
                font-size: 18px;
                font-family: 'Segoe UI';
            }}
            QLineEdit::placeholder {{ color: rgba(244, 238, 232, 0.46); }}
        """


class FilterPanel(GlassCard):
    """Компактная панель фильтрации по сложности.

    Отдельный выпадающий список сортировки убран: порядок всегда
    фиксированный — от простых треков к сложным.
    """

    filtersChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(86)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 16, 22, 16)
        layout.setSpacing(16)

        label = QLabel("Сложность:")
        label.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        label.setStyleSheet(f"color: {TEXT}; background: transparent;")

        self.complexity_box = QComboBox()
        self.complexity_box.addItems([
            "Любая сложность",
            "1 звезда",
            "2 звезды",
            "3 звезды",
            "4 звезды",
            "5 звёзд",
        ])
        self.complexity_box.setFixedHeight(44)
        self.complexity_box.setMinimumWidth(230)
        self.complexity_box.setStyleSheet(self._combo_style())
        self.complexity_box.currentIndexChanged.connect(self.filtersChanged.emit)

        layout.addWidget(label)
        layout.addWidget(self.complexity_box)
        layout.addStretch(1)

    def complexity_value(self) -> Optional[int]:
        index = self.complexity_box.currentIndex()
        return None if index == 0 else index

    @staticmethod
    def _combo_style() -> str:
        return f"""
            QComboBox {{
                color: {TEXT};
                background: rgba(0,0,0,0.28);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 16px;
                padding-left: 14px;
                padding-right: 14px;
                font-size: 14px;
                font-family: 'Segoe UI';
            }}
            QComboBox::drop-down {{ border: none; width: 26px; }}
            QComboBox QAbstractItemView {{
                color: {TEXT};
                background: #17131A;
                selection-background-color: rgba(255, 118, 72, 0.42);
                outline: none;
            }}
        """


class TrackTable(QTableWidget):
    """Таблица треков с визуальным выделением выбранной строки и оценкой сложности звездами."""

    HEADERS = ["ID", "Название", "Исполнитель", "Длительность", "Сложность"]

    trackPicked = QtCore.pyqtSignal(int)
    trackActivated = QtCore.pyqtSignal(int)
    sortRequested = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_track_id: Optional[int] = None
        self._tracks: list[Track] = []
        self._setup()

    def _setup(self):
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet(self._table_style())
        self.cellClicked.connect(self._emit_track)
        self.cellDoubleClicked.connect(self._emit_activation)

        header = self.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)
        header.sectionClicked.connect(self.sortRequested.emit)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

    def populate(self, tracks: list[Track], selected_track_id: Optional[int] = None):
        self._tracks = tracks
        if selected_track_id is not None:
            self._selected_track_id = selected_track_id

        self.setRowCount(len(tracks))
        for row_index, track in enumerate(tracks):
            is_selected = track.id == self._selected_track_id
            self._set_item(row_index, 0, f"▮  {track.id}" if is_selected else str(track.id), track.id)
            self._set_item(row_index, 1, track.title, track.id)
            self._set_item(row_index, 2, track.singer, track.id)
            self._set_item(row_index, 3, track.duration, track.id, center=True)
            self._set_item(row_index, 4, self._complexity_text(track.complexity), track.id, stars=True)
            self.setRowHeight(row_index, 58)

        self.refresh_selection()

    def refresh_selection(self):
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if not item:
                continue
            track_id = item.data(Qt.ItemDataRole.UserRole)
            is_selected = track_id == self._selected_track_id
            item.setText(f"▮  {track_id}" if is_selected else str(track_id))
            for col in range(self.columnCount()):
                cell = self.item(row, col)
                if cell is None:
                    continue
                if is_selected:
                    cell.setBackground(QColor(255, 111, 72, 54))
                    if col == 0:
                        cell.setForeground(QColor(ORANGE))
                else:
                    cell.setBackground(QColor(0, 0, 0, 0))
                    if col == 0:
                        cell.setForeground(QColor(TEXT))
            if is_selected:
                self.selectRow(row)

    def set_selected_track(self, track_id: int):
        self._selected_track_id = track_id
        self.refresh_selection()

    def _emit_track(self, row: int, column: int):
        track_id = self.track_id_at(row)
        if track_id is not None:
            self._selected_track_id = track_id
            self.refresh_selection()
            self.trackPicked.emit(track_id)

    def _emit_activation(self, row: int, column: int):
        track_id = self.track_id_at(row)
        if track_id is not None:
            self.trackActivated.emit(track_id)

    def track_id_at(self, row: int) -> Optional[int]:
        item = self.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _set_item(self, row: int, column: int, text: str, track_id: int, center: bool = False, stars: bool = False):
        item = QTableWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, track_id)
        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignCenter if center else Qt.AlignmentFlag.AlignLeft))
        item.setForeground(QColor(ORANGE if stars else TEXT))
        if stars:
            item.setFont(QFont("Segoe UI", 15, QFont.Weight.DemiBold))
        else:
            item.setFont(QFont("Segoe UI", 14))
        self.setItem(row, column, item)

    def set_sort_indicator(self, column: Optional[int], ascending: bool) -> None:
        labels = list(self.HEADERS)
        header = self.horizontalHeader()
        if column is None:
            header.setSortIndicatorShown(False)
        else:
            arrow = "▲" if ascending else "▼"
            labels[column] = f"{labels[column]} {arrow}"
            order = Qt.SortOrder.AscendingOrder if ascending else Qt.SortOrder.DescendingOrder
            header.setSortIndicator(column, order)
            header.setSortIndicatorShown(True)
        self.setHorizontalHeaderLabels(labels)

    @staticmethod
    def _complexity_text(value: int | str) -> str:
        try:
            return TrackTable._stars(int(value))
        except (TypeError, ValueError):
            return str(value).capitalize()

    @staticmethod
    def _stars(value: int) -> str:
        value = max(1, min(5, int(value)))
        return "★ " * value + "☆ " * (5 - value)

    @staticmethod
    def _table_style() -> str:
        return f"""
            QTableWidget {{
                color: {TEXT};
                background: rgba(0,0,0,0.10);
                border: none;
                border-radius: 18px;
                gridline-color: transparent;
                font-family: 'Segoe UI';
                selection-background-color: rgba(255, 118, 72, 0.36);
                selection-color: white;
            }}
            QHeaderView::section {{
                background: rgba(255, 255, 255, 0.02);
                color: #E9C9A3;
                border: none;
                border-right: 1px solid rgba(255,255,255,0.08);
                padding: 12px 18px;
                font-size: 14px;
                font-weight: 600;
            }}
            QTableWidget::item {{
                border-bottom: 1px solid rgba(255,255,255,0.045);
                padding-left: 16px;
            }}
            QScrollBar:vertical {{
                background: rgba(255,255,255,0.04);
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,179,92,0.55);
                border-radius: 5px;
            }}
        """


class MiniEqualizer(QWidget):
    """Небольшой индикатор громкости, который движется только во время воспроизведения."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(74, 52)
        self.phase = 0.0
        self._animated = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def set_animated(self, animated: bool) -> None:
        self._animated = animated
        if animated:
            if not self.timer.isActive():
                self.timer.start(70)
        else:
            self.timer.stop()
        self.update()

    def _tick(self):
        self.phase += 0.18
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(7):
            value = 8 + 28 * abs(math.sin(self.phase + i * 0.7))
            alpha = 150 if self._animated else 82
            painter.setBrush(QColor(255, 120 + i * 9, 72, alpha))
            painter.drawRect(8 + i * 9, int(42 - value), 5, int(value))


class ChooseBottomBar(GlassCard):
    """Нижняя панель выбора ID и запуска практики."""

    backRequested = QtCore.pyqtSignal()
    startRequested = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(108)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(26, 20, 26, 20)
        layout.setSpacing(20)

        self.back_button = GlowButton("←   Назад", "secondary")
        self.back_button.setFixedWidth(210)

        label = QLabel("ID трека:")
        label.setFont(QFont("Segoe UI", 15, QFont.Weight.DemiBold))
        label.setStyleSheet(f"color: {TEXT}; background: transparent;")

        self.song_id = QSpinBox()
        self.song_id.setMinimum(1)
        self.song_id.setMaximum(9999)
        self.song_id.setFixedSize(230, 56)
        self.song_id.setStyleSheet(self._spin_style())

        self.start_button = GlowButton("▶   Начать", "primary")
        self.start_button.setFixedWidth(290)
        self.hint = QLabel("Выбери строку или введи ID вручную  ♫")
        self.hint.setStyleSheet(f"color: rgba(244, 238, 232, 0.52); background: transparent; font-size: 12px;")

        start_box = QVBoxLayout()
        start_box.setSpacing(4)
        start_box.addWidget(self.start_button)
        start_box.addWidget(self.hint, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.back_button)
        layout.addStretch(1)
        layout.addWidget(label)
        layout.addWidget(self.song_id)
        layout.addStretch(1)
        layout.addLayout(start_box)

        self.back_button.clicked.connect(self.backRequested.emit)
        self.start_button.clicked.connect(self._emit_start)
        self.song_id.lineEdit().returnPressed.connect(self._emit_start)

    def set_track_id(self, track_id: int):
        self.song_id.setValue(track_id)

    def track_id(self) -> int:
        return self.song_id.value()

    def _emit_start(self):
        self.startRequested.emit(self.song_id.value())

    @staticmethod
    def _spin_style() -> str:
        return f"""
            QSpinBox {{
                color: {TEXT};
                background: rgba(0,0,0,0.26);
                border: 1px solid rgba(255,179,92,0.42);
                border-radius: 16px;
                padding-left: 18px;
                padding-right: 18px;
                font-size: 18px;
                font-family: 'Segoe UI';
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 26px;
                border: none;
                background: transparent;
            }}
        """


class ChooseScreen(QMainWindow):
    """Вторая страница: выбор трека в стиле присланного референса."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Выбор трека")
        self.setFixedSize(1280, 760)
        set_app_icon(self)

        self.repository = TrackRepository(BASE_DIR / "tracks.sqlite")
        self.all_tracks: list[Track] = []
        self.visible_tracks: list[Track] = []
        self.selected_track_id: Optional[int] = None
        self.current_search = ""
        self.sort_column: Optional[int] = None
        self.sort_ascending = True
        self.background_music = get_menu_background_music()
        self.background_music.set_context("choose")

        self.bg = AnimatedBackground(self)
        self.setCentralWidget(self.bg)
        self._build_ui()
        self._connect_database()

    def _build_ui(self):
        root = QVBoxLayout(self.bg)
        root.setContentsMargins(52, 36, 52, 36)
        root.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(24)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Выбор трека")
        title.setFont(QFont("Georgia", 42, QFont.Weight.Normal))
        title.setStyleSheet(f"color: {TEXT}; background: transparent;")
        subtitle = QLabel("Выбери песню и начни практику")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setStyleSheet(f"color: {MUTED}; background: transparent;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.search_panel = SearchPanel()
        self.search_panel.setFixedWidth(640)

        header.addLayout(title_box)
        header.addStretch(1)
        header.addWidget(self.search_panel)
        root.addLayout(header)

        self.filter_panel = FilterPanel()
        self.filter_panel.hide()
        root.addWidget(self.filter_panel)

        self.table_card = GlassCard()
        table_layout = QVBoxLayout(self.table_card)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_layout.setSpacing(0)
        self.tableWidget = TrackTable()
        table_layout.addWidget(self.tableWidget)
        root.addWidget(self.table_card, 1)

        self.status_label = QLabel("Готово к выбору трека")
        self.status_label.setStyleSheet(f"color: rgba(244, 238, 232, 0.58); background: transparent; font-size: 12px;")
        root.addWidget(self.status_label)

        self.bottom_bar = ChooseBottomBar()
        root.addWidget(self.bottom_bar)

        self.search_panel.searchChanged.connect(self.on_search_changed)
        self.search_panel.filterClicked.connect(self.toggle_filters)
        self.filter_panel.filtersChanged.connect(self.apply_filters)
        self.tableWidget.trackPicked.connect(self.select_track)
        self.tableWidget.trackActivated.connect(self.run_practice)
        self.tableWidget.sortRequested.connect(self.on_table_header_clicked)
        self.bottom_bar.backRequested.connect(self.back_to_main)
        self.bottom_bar.startRequested.connect(self.run_practice)

    def _connect_database(self):
        try:
            if not self.repository.connect():
                self.status_label.setText("Файл tracks.sqlite не найден. Проверь расположение базы данных.")
                return
            self.all_tracks = self.repository.all_tracks()
            if self.all_tracks:
                self.selected_track_id = self.all_tracks[0].id
                self.bottom_bar.set_track_id(self.selected_track_id)
            self.apply_filters()
            self.status_label.setText(f"Загружено треков: {len(self.all_tracks)}")
        except sqlite3.Error as error:
            self.status_label.setText(f"Ошибка базы данных: {error}")

    def on_search_changed(self, text: str):
        self.current_search = text.strip().lower()
        self.apply_filters()

    def toggle_filters(self):
        self.filter_panel.setVisible(not self.filter_panel.isVisible())

    def on_table_header_clicked(self, column: int):
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
        self.apply_filters()

    def apply_filters(self):
        tracks = list(self.all_tracks)
        if self.current_search:
            tracks = [
                track for track in tracks
                if self.current_search in track.singer.lower() or self.current_search in track.title.lower()
            ]

        complexity = self.filter_panel.complexity_value()
        if complexity is not None:
            tracks = [track for track in tracks if complexity_rank(track.complexity) == complexity]

        self._apply_sorting(tracks)

        self.visible_tracks = tracks
        self.tableWidget.populate(self.visible_tracks, self.selected_track_id)
        self.tableWidget.set_sort_indicator(self.sort_column, self.sort_ascending)
        self._sync_selection_after_filter()
        self.status_label.setText(self._status_text())

    def _sync_selection_after_filter(self):
        if not self.visible_tracks:
            return
        visible_ids = {track.id for track in self.visible_tracks}
        if self.selected_track_id not in visible_ids:
            self.select_track(self.visible_tracks[0].id)
        else:
            self.tableWidget.set_selected_track(int(self.selected_track_id))

    def select_track(self, track_id: int):
        self.selected_track_id = track_id
        self.bottom_bar.set_track_id(track_id)
        self.tableWidget.set_selected_track(track_id)
        track = self.repository.get_track(track_id)
        if track:
            self.status_label.setText(f"Выбран трек: {track.singer} — {track.title}")

    def run_practice(self, track_id: Optional[int] = None):
        target_id = int(track_id if track_id is not None else self.bottom_bar.track_id())
        try:
            track = self.repository.get_track(target_id)
        except sqlite3.Error as error:
            self.status_label.setText(f"Ошибка базы данных: {error}")
            return

        if track is None:
            self.status_label.setText("Трека с таким ID нет в базе данных")
            return

        self.background_music.set_context("practice")
        self.next_window = PracticeScreen(str(track.id), track.singer, track.title, track.duration)
        self.next_window.show()
        self.close()

    def back_to_main(self):
        self.background_music.set_context("main")
        self.next_window = LearnTheGuitar()
        self.next_window.show()
        self.close()

    def closeEvent(self, event):
        self.repository.close()
        super().closeEvent(event)

    def _status_text(self) -> str:
        if not self.visible_tracks:
            return "Ничего не найдено. Очисти поиск или измени фильтр."
        if self.current_search or self.filter_panel.complexity_value() is not None:
            return f"Найдено треков: {len(self.visible_tracks)}"
        return f"Доступно треков: {len(self.visible_tracks)}"

    def _apply_sorting(self, tracks: list[Track]) -> None:
        if self.sort_column is None:
            # Дефолтное состояние окна выбора: ID от меньшего к большему.
            # Это не мешает дальнейшей сортировке по клику на заголовки.
            tracks.sort(key=lambda track: track.id)
            return

        # Стабильная вторичная сортировка по ID не дает строкам случайно
        # «прыгать» внутри одинаковых значений выбранного столбца.
        tracks.sort(key=lambda track: track.id)
        tracks.sort(key=self._sort_value(self.sort_column), reverse=not self.sort_ascending)

    @staticmethod
    def _duration_seconds(duration: str) -> int:
        try:
            minutes, seconds = duration.split(":")[:2]
            return int(minutes) * 60 + int(seconds)
        except (ValueError, AttributeError):
            return 0

    def _sort_value(self, column: int):
        if column == 1:
            return lambda track: track.title.lower()
        if column == 2:
            return lambda track: track.singer.lower()
        if column == 3:
            return lambda track: self._duration_seconds(track.duration)
        if column == 4:
            return lambda track: complexity_rank(track.complexity)
        return lambda track: track.id



# ---------- Окно практики ----------

@dataclass
class PracticeData:
    """Данные третьей страницы, отделенные от интерфейса."""

    song_text: str
    battle_text: str
    chord_names: list[str]
    chord_texts: list[str]
    image_path: Optional[Path]
    audio_path: Optional[Path]
    lrc_path: Optional[Path]


@dataclass(frozen=True)
class LrcEntry:
    """Одна строка LRC с временем начала в секундах."""

    time_seconds: float
    text: str


class LrcParser:
    """Отдельный парсер LRC без привязки к GUI и плееру."""

    TIME_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:[\.:](\d{1,3}))?\]")

    @classmethod
    def parse_file(cls, path: Path) -> list[LrcEntry]:
        text = path.read_text(encoding="utf-8-sig")
        entries: list[LrcEntry] = []

        for raw_line in text.splitlines():
            matches = list(cls.TIME_RE.finditer(raw_line))
            if not matches:
                continue
            lyric_text = cls.TIME_RE.sub("", raw_line).strip()
            for match in matches:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                fraction_text = match.group(3) or "0"
                fraction = int(fraction_text) / (10 ** len(fraction_text))
                entries.append(LrcEntry(minutes * 60 + seconds + fraction, lyric_text))

        entries.sort(key=lambda item: item.time_seconds)
        if not entries:
            raise ValueError(f"в LRC нет строк с таймкодами: {path}")
        return entries


class PracticeDataLoader:
    """Загружает текст, бой, аккорды, картинку и аудио без привязки к виджетам."""

    CHORD_RE = QtCore.QRegularExpression(r"\b[A-G](?:#|b)?(?:m|maj|min|sus|dim|aug|add)?\d*(?:/[A-G](?:#|b)?)?\b")

    def __init__(self, song_id: str, song_title: str = ""):
        self.song_id = str(song_id)
        self.song_title = song_title

    def load(self) -> PracticeData:
        song_text = read_text(f"songs_texts/{self.song_id}.txt", "Текст песни не найден.")
        settings = read_text(f"songs_settings/{self.song_id}.txt")
        lines = settings.splitlines()

        battle_name = lines[0].strip() if lines else ""
        chord_names = lines[1].split() if len(lines) > 1 else self._extract_chords(song_text)

        battle_text = read_text(f"battle/{battle_name}.txt", "↓ ↓ ✱ ↑ ↑ ↓ ✱ ↑").strip()
        chord_texts = [read_text(f"accords/{name}.txt", f"{name}: схема аккорда не найдена") for name in chord_names]

        image_path = BASE_DIR / f"pics/{self.song_id}.png"
        audio_path = BASE_DIR / f"songs_audios/{self.song_id}.mp3"
        lrc_path = self._find_lrc_path(audio_path)

        return PracticeData(
            song_text=song_text,
            battle_text=battle_text or "↓ ↓ ✱ ↑ ↑ ↓ ✱ ↑",
            chord_names=chord_names or ["Em", "Am", "C", "G", "D"],
            chord_texts=chord_texts or ["Аккорды не найдены."],
            image_path=image_path if image_path.exists() else None,
            audio_path=audio_path if audio_path.exists() else None,
            lrc_path=lrc_path,
        )

    def _find_lrc_path(self, audio_path: Path) -> Optional[Path]:
        lrc_dir = BASE_DIR / "lrc"
        if not lrc_dir.exists():
            print("LRC-файл не найден: папка lrc отсутствует")
            return None

        candidates: list[Path] = []
        for stem in (self.song_id, audio_path.stem, self.song_title.strip(), self._safe_stem(self.song_title)):
            if stem:
                candidates.append(lrc_dir / f"{stem}.lrc")

        for candidate in candidates:
            if candidate.exists():
                return candidate

        print(f"LRC-файл не найден для трека {self.song_id}: проверены {[path.name for path in candidates]}")
        return None

    @staticmethod
    def _safe_stem(value: str) -> str:
        cleaned = "".join(char.lower() if char.isalnum() else "_" for char in value.strip())
        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")
        return cleaned.strip("_")

    def _extract_chords(self, text: str) -> list[str]:
        found: list[str] = []
        for match in self.CHORD_RE.globalMatch(text):
            chord = match.captured(0)
            if chord and chord not in found:
                found.append(chord)
            if len(found) >= 8:
                break
        return found


class SmallPillButton(QPushButton):
    """Небольшая кнопка для панелей практики."""

    def __init__(self, text: str, primary: bool = False, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(50)
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self._apply_style(False)

    def enterEvent(self, event):
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)

    def _apply_style(self, hover: bool):
        if self.primary:
            bg = "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #FFBE66, stop:0.55 #FF674B, stop:1 #E53B4E)"
            border = "rgba(255, 226, 168, 0.75)" if hover else "rgba(255, 226, 168, 0.42)"
        else:
            bg = "rgba(255,255,255,0.105)" if hover else "rgba(255,255,255,0.055)"
            border = "rgba(255, 255, 255, 0.28)" if hover else "rgba(255, 255, 255, 0.16)"
        self.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT};
                border: 1px solid {border};
                border-radius: 16px;
                padding: 8px 18px;
                background: {bg};
            }}
            QPushButton:pressed {{ padding-top: 10px; }}
        """)


class RoundControlButton(QPushButton):
    """Круглая кнопка аудиоплеера."""

    def __init__(self, text: str, size: int = 58, primary: bool = False, parent=None):
        super().__init__(text, parent)
        self.size_value = size
        self.primary = primary
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 20 if primary else 17, QFont.Weight.Bold))
        self._apply_style(False)

    def enterEvent(self, event):
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)

    def _apply_style(self, hover: bool):
        radius = self.size_value // 2
        if self.primary:
            bg = "qradialgradient(cx:0.5, cy:0.5, radius:0.75, stop:0 #FFD18A, stop:0.50 #FF6C4C, stop:1 #B9223D)"
            border = "rgba(255, 210, 132, 0.95)" if hover else "rgba(255, 210, 132, 0.55)"
        else:
            bg = "rgba(255,255,255,0.115)" if hover else "rgba(255,255,255,0.060)"
            border = "rgba(255,255,255,0.26)" if hover else "rgba(255,255,255,0.13)"
        self.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT};
                border-radius: {radius}px;
                border: 1px solid {border};
                background: {bg};
            }}
        """)


class CoverCard(GlassCard):
    """Левая карточка: обложка, название трека и быстрые действия."""

    accordsRequested = QtCore.pyqtSignal()
    battleRequested = QtCore.pyqtSignal()

    def __init__(self, song: str, singer: str, image_path: Optional[Path], parent=None):
        super().__init__(parent)
        self.setFixedWidth(490)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(12)

        self.image_label = QLabel()
        self.image_label.setFixedSize(390, 285)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(f"""
            QLabel {{
                color: rgba(244,238,232,0.45);
                background: rgba(0,0,0,0.26);
                border: 1px solid rgba(255,179,92,0.28);
                border-radius: 22px;
                font-size: 18px;
            }}
        """)
        if image_path is not None:
            pixmap = QPixmap(str(image_path)).scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(pixmap)
        else:
            self.image_label.setText("обложка\nне найдена")

        self.track_label = QLabel(song)
        self.track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.track_label.setWordWrap(True)
        self.track_label.setFont(QFont("Georgia", 30, QFont.Weight.Normal))
        self.track_label.setStyleSheet(f"color: {TEXT}; background: transparent;")

        self.singer_label = QLabel(singer)
        self.singer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.singer_label.setFont(QFont("Segoe UI", 14))
        self.singer_label.setStyleSheet(f"color: {MUTED}; background: transparent;")

        actions = QHBoxLayout()
        actions.setSpacing(14)
        self.accords_button = SmallPillButton("▦   Показать аккорды", primary=True)
        self.battle_button = SmallPillButton("↕   Показать бой")
        actions.addWidget(self.accords_button)
        actions.addWidget(self.battle_button)

        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.track_label)
        layout.addWidget(self.singer_label)
        layout.addSpacing(4)
        layout.addLayout(actions)
        layout.addStretch(1)

        self.accords_button.clicked.connect(self.accordsRequested.emit)
        self.battle_button.clicked.connect(self.battleRequested.emit)

    def set_accords_visible(self, visible: bool) -> None:
        self.accords_button.setText("▦   Скрыть аккорды" if visible else "▦   Показать аккорды")

    def set_battle_visible(self, visible: bool) -> None:
        self.battle_button.setText("↕   Скрыть бой" if visible else "↕   Показать бой")


class LyricsPanel(GlassCard):
    """Правая карточка текста: обычный текст или LRC-синхронизация."""

    CHORD_LINE_RE = QtCore.QRegularExpression(
        r"^\s*([A-G](?:#|b)?(?:m|maj|min|sus|dim|aug|add)?\d*(?:/[A-G](?:#|b)?)?\s+)*"
        r"[A-G](?:#|b)?(?:m|maj|min|sus|dim|aug|add)?\d*(?:/[A-G](?:#|b)?)?\s*$"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lines: list[str] = []
        self.lrc_entries: list[LrcEntry] = []
        self.current_line: Optional[int] = None
        self._scroll_animation: Optional[QPropertyAnimation] = None
        self._last_scroll_target: Optional[int] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 22, 22)
        layout.setSpacing(10)

        self.editor = QtWidgets.QTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setFrameShape(QFrame.Shape.NoFrame)
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                color: {TEXT};
                background: transparent;
                border: none;
                font-family: 'Segoe UI';
                font-size: 18px;
                line-height: 1.5;
            }}
            QScrollBar:vertical {{
                background: rgba(255,255,255,0.045);
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,110,72,0.78);
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self.editor)

    def set_lyrics(self, text: str) -> None:
        self._stop_scroll_animation()
        self.lrc_entries = []
        self.lines = text.splitlines() or ["Текст песни не найден."]
        self.current_line = None
        self._last_scroll_target = None
        self._render()

    def set_lrc_entries(self, entries: list[LrcEntry]) -> None:
        self._stop_scroll_animation()
        self.lrc_entries = entries
        self.lines = [entry.text if entry.text else " " for entry in entries]
        self.current_line = 0 if self.lines else None
        self._last_scroll_target = None
        self._render(scroll_to_current=True, animated=False)

    def update_by_time(self, seconds: float, *, force: bool = False) -> None:
        if not self.lrc_entries:
            return
        index = self._entry_index_for_time(seconds)
        if index != self.current_line or force:
            self.current_line = index
            self._render(scroll_to_current=True, animated=True, fast_scroll=force)

    def set_progress(self, progress: float) -> None:
        # Без LRC принудительную подсветку по проценту не делаем.
        return

    def _entry_index_for_time(self, seconds: float) -> int:
        if not self.lrc_entries:
            return 0
        seconds = max(0.0, float(seconds))
        left = 0
        right = len(self.lrc_entries) - 1
        answer = 0
        while left <= right:
            middle = (left + right) // 2
            if self.lrc_entries[middle].time_seconds <= seconds:
                answer = middle
                left = middle + 1
            else:
                right = middle - 1
        return answer

    def _render(
        self,
        scroll_to_current: bool = False,
        animated: bool = True,
        fast_scroll: bool = False,
    ) -> None:
        scrollbar = self.editor.verticalScrollBar()
        previous_scroll = scrollbar.value()
        html_lines = []
        for index, line in enumerate(self.lines):
            safe = self._escape(line) if line.strip() else "&nbsp;"
            if self.current_line is not None and index == self.current_line and line.strip():
                html_lines.append(
                    f"<div style='margin:8px 0; padding:12px 14px; border-radius:14px; "
                    f"background:rgba(255,97,72,0.18); border:1px solid rgba(255,118,72,0.28);'>"
                    f"<span style='color:#FFB35C; font-weight:700;'>▶&nbsp;</span>{safe}</div>"
                )
            elif self._is_chord_line(line):
                html_lines.append(f"<div style='color:#FF8F5A; font-weight:700; margin-top:5px;'>{safe}</div>")
            else:
                html_lines.append(f"<div style='color:rgba(244,238,232,0.82); margin:3px 0;'>{safe}</div>")

        self.editor.setUpdatesEnabled(False)
        self.editor.setHtml("".join(html_lines))
        scrollbar.setValue(max(0, min(previous_scroll, scrollbar.maximum())))
        self.editor.setUpdatesEnabled(True)

        if scroll_to_current and self.current_line is not None:
            line_index = self.current_line
            QtCore.QTimer.singleShot(
                0,
                lambda index=line_index: self._scroll_to_line(index, animated=animated, fast=fast_scroll),
            )

    def _scroll_to_line(self, index: int, animated: bool = True, fast: bool = False) -> None:
        scrollbar = self.editor.verticalScrollBar()
        maximum = scrollbar.maximum()
        if maximum <= 0 or not self.lines:
            return

        clamped_index = max(0, min(index, len(self.lines) - 1))
        target = self._line_scroll_target(clamped_index, maximum)
        current_value = scrollbar.value()

        if abs(current_value - target) <= 3:
            self._last_scroll_target = target
            return
        if self._last_scroll_target == target and self._scroll_animation is not None:
            if self._scroll_animation.state() == QtCore.QAbstractAnimation.State.Running:
                return

        self._last_scroll_target = target
        if animated:
            self._stop_scroll_animation()
            self._scroll_animation = QPropertyAnimation(scrollbar, b"value", self)
            self._scroll_animation.setDuration(320 if fast else 560)
            self._scroll_animation.setStartValue(current_value)
            self._scroll_animation.setEndValue(target)
            self._scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._scroll_animation.start()
        else:
            scrollbar.setValue(target)

    def _line_scroll_target(self, index: int, maximum: int) -> int:
        viewport_height = max(1, self.editor.viewport().height())
        block = self.editor.document().findBlockByNumber(index)
        if block.isValid():
            block_rect = self.editor.document().documentLayout().blockBoundingRect(block)
            active_line_center = int(block_rect.center().y())
            reading_zone = int(viewport_height * 0.42)
            target = active_line_center - reading_zone
        else:
            denominator = max(1, len(self.lines) - 1)
            target = int(maximum * index / denominator)
        return max(0, min(maximum, target))

    def _stop_scroll_animation(self) -> None:
        if self._scroll_animation is not None:
            self._scroll_animation.stop()

    def _is_chord_line(self, line: str) -> bool:
        stripped = line.strip()
        return bool(stripped) and self.CHORD_LINE_RE.match(stripped).hasMatch()

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace(" ", "&nbsp;")
        )


class ChordDiagramWidget(QWidget):
    """Рисует простую схему аккорда без внешних изображений."""

    COMMON_FINGERINGS = {
        "Em": {"mute": [], "open": [1, 2, 3, 4, 5, 6], "dots": [(5, 2), (4, 2)]},
        "Am": {"mute": [6], "open": [1, 5], "dots": [(4, 2), (3, 2), (2, 1)]},
        "C": {"mute": [6], "open": [1, 3], "dots": [(5, 3), (4, 2), (2, 1)]},
        "G": {"mute": [], "open": [3, 4], "dots": [(6, 3), (5, 2), (2, 3), (1, 3)]},
        "D": {"mute": [5, 6], "open": [4], "dots": [(3, 2), (2, 3), (1, 2)]},
        "E": {"mute": [], "open": [1, 2, 6], "dots": [(5, 2), (4, 2), (3, 1)]},
        "A": {"mute": [6], "open": [1, 5], "dots": [(4, 2), (3, 2), (2, 2)]},
    }

    def __init__(self, chord_name: str, active: bool = False, parent=None):
        super().__init__(parent)
        self.chord_name = chord_name
        self.active = active
        self.setFixedSize(116, 122)
        self.setToolTip(chord_name)

    def set_active(self, active: bool) -> None:
        self.active = active
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.setPen(QPen(QColor(ORANGE if self.active else TEXT), 1))
        p.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        p.drawText(QtCore.QRect(0, 0, self.width(), 24), Qt.AlignmentFlag.AlignCenter, self.chord_name)

        x0, y0 = 22, 38
        grid_w, grid_h = 72, 68
        string_gap = grid_w / 5
        fret_gap = grid_h / 4

        if self.active:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 112, 68, 36))
            p.drawRoundedRect(8, 28, 100, 88, 14, 14)

        p.setPen(QPen(QColor(255, 255, 255, 130), 1))
        for i in range(6):
            x = x0 + i * string_gap
            p.drawLine(int(x), y0, int(x), y0 + grid_h)
        for i in range(5):
            y = y0 + i * fret_gap
            width = 3 if i == 0 else 1
            p.setPen(QPen(QColor(255, 255, 255, 155), width))
            p.drawLine(x0, int(y), x0 + grid_w, int(y))

        fingering = self._fingering()
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        for string in range(1, 7):
            x = x0 + (6 - string) * string_gap
            if string in fingering["mute"]:
                p.setPen(QColor(200, 195, 190, 150))
                p.drawText(QtCore.QRectF(x - 5, y0 - 20, 10, 12), Qt.AlignmentFlag.AlignCenter, "×")
            elif string in fingering["open"]:
                p.setPen(QColor(240, 235, 230, 160))
                p.drawText(QtCore.QRectF(x - 5, y0 - 20, 10, 12), Qt.AlignmentFlag.AlignCenter, "o")

        p.setPen(Qt.PenStyle.NoPen)
        for number, (string, fret) in enumerate(fingering["dots"], start=1):
            x = x0 + (6 - string) * string_gap
            y = y0 + (fret - 0.5) * fret_gap
            p.setBrush(QColor(255, 110, 68, 230))
            p.drawEllipse(QtCore.QPointF(x, y), 7, 7)
            p.setPen(QPen(QColor(255, 255, 255, 210), 1))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.drawText(QtCore.QRectF(x - 7, y - 7, 14, 14), Qt.AlignmentFlag.AlignCenter, str(min(number, 4)))
            p.setPen(Qt.PenStyle.NoPen)

    def _fingering(self) -> dict[str, list]:
        normalized = self.chord_name.strip().replace("♯", "#")
        if normalized in self.COMMON_FINGERINGS:
            return self.COMMON_FINGERINGS[normalized]
        base = sum(ord(ch) for ch in normalized) or 1
        dots = []
        for i in range(3):
            string = 1 + ((base + i * 2) % 6)
            fret = 1 + ((base + i) % 3)
            dots.append((string, fret))
        return {"mute": [], "open": [1, 6], "dots": dots}


class ChordCarouselPanel(GlassCard):
    """Панель аккордов с перелистыванием."""

    def __init__(self, chord_names: list[str], chord_texts: list[str], parent=None):
        super().__init__(parent)
        self.chord_names = chord_names
        self.chord_texts = chord_texts
        self.offset = 0
        self.page_size = 5
        self.widgets: list[ChordDiagramWidget] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Аккорды")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {TEXT}; background: transparent;")
        self.info = QLabel("выбраны из настроек песни")
        self.info.setStyleSheet(f"color: {MUTED}; background: transparent; font-size: 12px;")
        header.addWidget(title)
        header.addWidget(self.info)
        header.addStretch(1)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.prev_button = SmallPillButton("‹")
        self.next_button = SmallPillButton("›")
        self.prev_button.setFixedSize(46, 64)
        self.next_button.setFixedSize(46, 64)
        self.diagram_box = QHBoxLayout()
        self.diagram_box.setSpacing(18)
        body.addWidget(self.prev_button)
        body.addLayout(self.diagram_box, 1)
        body.addWidget(self.next_button)
        layout.addLayout(body)

        self.dots_label = QLabel()
        self.dots_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dots_label.setStyleSheet(f"color: rgba(255,255,255,0.28); background: transparent; font-size: 20px;")
        layout.addWidget(self.dots_label)

        self.prev_button.clicked.connect(lambda: self.shift(-1))
        self.next_button.clicked.connect(lambda: self.shift(1))
        self.refresh()

    def shift(self, direction: int) -> None:
        if len(self.chord_names) <= self.page_size:
            return
        self.offset = (self.offset + direction) % len(self.chord_names)
        self.refresh()

    def refresh(self) -> None:
        while self.diagram_box.count():
            item = self.diagram_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.widgets.clear()

        names = self._visible_names()
        for index, name in enumerate(names):
            widget = ChordDiagramWidget(name, active=index == 0)
            self.widgets.append(widget)
            self.diagram_box.addWidget(widget)
        self.diagram_box.addStretch(1)

        total_pages = max(1, math.ceil(len(self.chord_names) / self.page_size))
        active_page = min(total_pages, self.offset // self.page_size + 1)
        self.dots_label.setText("  ".join("●" if i == active_page - 1 else "●" for i in range(total_pages)))
        self.dots_label.setStyleSheet(f"color: rgba(255,112,68,0.85); background: transparent; font-size: 16px;")
        self.prev_button.setEnabled(len(self.chord_names) > self.page_size)
        self.next_button.setEnabled(len(self.chord_names) > self.page_size)

    def _visible_names(self) -> list[str]:
        if len(self.chord_names) <= self.page_size:
            return self.chord_names
        doubled = self.chord_names + self.chord_names
        return doubled[self.offset:self.offset + self.page_size]


class BattlePatternWidget(QWidget):
    """Статичная схема боя в одну строку без прыжков и автоподсветки."""

    def __init__(self, pattern_text: str, parent=None):
        super().__init__(parent)
        self.pattern_text = pattern_text
        self.tokens = self._normalize(pattern_text)
        self.setMinimumHeight(86)
        self.setMinimumWidth(self._estimated_width())
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)

    def _estimated_width(self) -> int:
        return max(520, 34 + sum(max(52, len(token) * 22 + 28) + 10 for token in self.tokens))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.tokens:
            return

        x = 18
        y = 14
        gap = 10
        for index, token in enumerate(self.tokens):
            font_size = 26 if len(token) < 3 else 22
            p.setFont(QFont("Segoe UI", font_size, QFont.Weight.DemiBold))
            text_width = p.fontMetrics().horizontalAdvance(token)
            cell_width = max(52, text_width + 28)

            p.setPen(QPen(QColor(255, 179, 92, 95), 1))
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(QtCore.QRectF(x, y, cell_width, 48), 14, 14)

            p.setPen(QColor(244, 238, 232, 220))
            p.drawText(QtCore.QRectF(x, y, cell_width, 42), Qt.AlignmentFlag.AlignCenter, token)

            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            p.setPen(QColor(244, 238, 232, 92))
            p.drawText(QtCore.QRectF(x, y + 42, cell_width, 18), Qt.AlignmentFlag.AlignCenter, str(index + 1))
            x += cell_width + gap

    def _normalize(self, text: str) -> list[str]:
        raw = text.replace("\\n", " ").replace("\n", " ").strip()
        if not raw:
            raw = "↓ ↓ ✱ ↑ ↑ ↓ ✱ ↑"

        replacements = {
            "v": "↓", "V": "↓", "d": "↓", "D": "↓", "down": "↓", "низ": "↓",
            "^": "↑", "u": "↑", "U": "↑", "up": "↑", "верх": "↑",
            "x": "✱", "X": "✱", "*": "✱", "-": "—",
        }
        symbol_replacements = {
            "v": "↓", "V": "↓", "d": "↓", "D": "↓", "^": "↑",
            "u": "↑", "U": "↑", "x": "✱", "X": "✱", "*": "✱", "-": "—",
        }
        battle_symbols = set("↓↑✱—vVdD^uUxX*-")
        tokens: list[str] = []

        for part in raw.split():
            normalized = replacements.get(part, part)
            if len(normalized) > 1 and any(char in battle_symbols for char in normalized):
                for char in normalized:
                    if char in battle_symbols:
                        tokens.append(symbol_replacements.get(char, char))
            else:
                tokens.append(normalized)

        return [token for token in tokens if token] or ["↓", "↓", "✱", "↑", "↑", "↓", "✱", "↑"]


class BattlePanel(GlassCard):
    def __init__(self, pattern_text: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Схема боя")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {TEXT}; background: transparent;")
        subtitle = QLabel("статичная схема")
        subtitle.setStyleSheet(f"color: {MUTED}; background: transparent; font-size: 12px;")
        header.addWidget(title)
        header.addWidget(subtitle)
        header.addStretch(1)
        layout.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFixedHeight(104)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:horizontal {{
                background: rgba(255,255,255,0.045);
                height: 9px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: rgba(255,179,92,0.58);
                border-radius: 4px;
            }}
        """)
        self.pattern = BattlePatternWidget(pattern_text)
        self.pattern.setStyleSheet("background: transparent;")
        self.scroll.setWidget(self.pattern)
        layout.addWidget(self.scroll)


class WaveformWidget(QWidget):
    """Декоративная волна с реальным прогрессом трека и перемоткой по клику."""

    seekRequested = QtCore.pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0.0
        self.phase = 0.0
        self._animated = False
        self.setMinimumHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def set_progress(self, progress: float) -> None:
        self.progress = max(0.0, min(1.0, progress))
        self.update()

    def set_animated(self, animated: bool) -> None:
        self._animated = animated
        if animated:
            if not self.timer.isActive():
                self.timer.start(70)
        else:
            self.timer.stop()
        self.update()

    def _tick(self):
        self.phase += 0.08
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._emit_seek(event.position().x())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._emit_seek(event.position().x())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _emit_seek(self, x: float) -> None:
        width = max(1, self.width())
        progress = max(0.0, min(1.0, x / width))
        self.set_progress(progress)
        self.seekRequested.emit(progress)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mid = h / 2
        count = max(40, w // 8)
        active_until = int(count * self.progress)

        p.setPen(QPen(QColor(255, 107, 68, 120), 2, Qt.PenStyle.DotLine))
        p.drawLine(0, int(mid), w, int(mid))

        for i in range(count):
            x = 4 + i * (w - 8) / count
            amp = 6 + 26 * abs(math.sin(i * 0.23 + self.phase)) * (0.35 + 0.65 * math.sin(i * 0.05) ** 2)
            color = QColor(255, 112, 68, 215) if i <= active_until else QColor(244, 238, 232, 55)
            p.setPen(QPen(color, 2))
            p.drawLine(int(x), int(mid - amp / 2), int(x), int(mid + amp / 2))

        knob_x = int((w - 10) * self.progress + 5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 179, 92, 190))
        p.drawEllipse(QtCore.QPointF(knob_x, mid), 4, 22)


class PlayerBar(GlassCard):
    """Нижний аудиоплеер: выход, прогресс, кнопки, громкость."""

    backRequested = QtCore.pyqtSignal()
    playPauseRequested = QtCore.pyqtSignal()
    rewindRequested = QtCore.pyqtSignal()
    forwardRequested = QtCore.pyqtSignal()
    restartRequested = QtCore.pyqtSignal()
    seekRequested = QtCore.pyqtSignal(float)
    volumeChanged = QtCore.pyqtSignal(int)

    def __init__(self, duration: str, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.setFixedHeight(168)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 12, 26, 14)
        layout.setSpacing(8)

        wave_row = QHBoxLayout()
        self.current_time = QLabel("0:00")
        self.total_time = QLabel(duration)
        for label in (self.current_time, self.total_time):
            label.setFixedWidth(70)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"color: {MUTED}; background: transparent; font-size: 14px;")
        self.waveform = WaveformWidget()
        wave_row.addWidget(self.current_time)
        wave_row.addWidget(self.waveform, 1)
        wave_row.addWidget(self.total_time)
        layout.addLayout(wave_row)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(14)
        self.exit_button = SmallPillButton("↪   Выйти")
        self.exit_button.setFixedWidth(190)
        self.restart_button = RoundControlButton("⟳", 50)
        self.rewind_button = RoundControlButton("◀", 54)
        self.play_button = RoundControlButton("▶", 72, primary=True)
        self.forward_button = RoundControlButton("▶", 54)
        self.loop_button = RoundControlButton("↻", 50)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(250)
        self.volume_slider.setStyleSheet(PracticeScreen.slider_style())
        volume_icon = QLabel("🔊")
        volume_icon.setStyleSheet("background: transparent; font-size: 24px;")
        self.volume_equalizer = MiniEqualizer()

        controls.addWidget(self.exit_button)
        controls.addStretch(1)
        controls.addWidget(self.restart_button)
        controls.addWidget(self.rewind_button)
        controls.addWidget(self.play_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        controls.addWidget(self.forward_button)
        controls.addWidget(self.loop_button)
        controls.addStretch(1)
        controls.addWidget(volume_icon)
        controls.addWidget(self.volume_slider)
        controls.addWidget(self.volume_equalizer)
        layout.addLayout(controls)

        self.exit_button.clicked.connect(self.backRequested.emit)
        self.play_button.clicked.connect(self.playPauseRequested.emit)
        self.rewind_button.clicked.connect(self.rewindRequested.emit)
        self.forward_button.clicked.connect(self.forwardRequested.emit)
        self.restart_button.clicked.connect(self.restartRequested.emit)
        self.loop_button.clicked.connect(self.restartRequested.emit)
        self.volume_slider.valueChanged.connect(self.volumeChanged.emit)
        self.waveform.seekRequested.connect(self.seekRequested.emit)
        self.set_playing(False)

    def set_playing(self, playing: bool) -> None:
        self.play_button.setText("⏸" if playing else "▶")
        self.waveform.set_animated(playing)
        self.volume_equalizer.set_animated(playing)

    def set_time(self, current_text: str, progress: float) -> None:
        self.current_time.setText(current_text)
        self.waveform.set_progress(progress)


class PracticeScreen(QMainWindow):
    """Третья страница: практика песни в стиле отправленного референса."""

    def __init__(self, song_id: str, singer: str, song: str, duration: str = "0:00"):
        super().__init__()
        self.song_id = song_id
        self.singer = singer
        self.song = song
        self.duration = duration
        self.song_length = self._duration_to_seconds(duration)
        self.play = False
        self.start_pos = 0.0
        self.audio_ready = False
        self.background_music = get_menu_background_music()
        self.background_music.set_context("practice")

        self.data = PracticeDataLoader(song_id, song).load()
        self.lrc_entries: list[LrcEntry] = []

        self.setWindowTitle("Практика")
        self.setFixedSize(1320, 820)
        set_app_icon(self)

        self.bg = AnimatedBackground(
            self,
            show_wave=False,
            show_chords=False,
            show_equalizer=False,
            particle_opacity=0.35,
        )
        self.setCentralWidget(self.bg)
        self._build_ui()
        self._init_audio()
        self._start_timers()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self.bg)
        root.setContentsMargins(36, 28, 36, 28)
        root.setSpacing(16)

        header = QHBoxLayout()
        header_title = QLabel("🎸  Практика")
        header_title.setFont(QFont("Segoe UI", 15, QFont.Weight.DemiBold))
        header_title.setStyleSheet(f"color: {TEXT}; background: transparent;")
        header.addWidget(header_title)
        header.addStretch(1)
        root.addLayout(header)

        top = QHBoxLayout()
        top.setSpacing(18)

        self.cover_card = CoverCard(self.song, self.singer, self.data.image_path)
        self.lyrics_panel = LyricsPanel()
        self.lyrics_panel.setMinimumHeight(300)
        self._load_lrc_or_plain_text()

        top.addWidget(self.cover_card)
        top.addWidget(self.lyrics_panel, 1)
        root.addLayout(top, 1)

        middle = QHBoxLayout()
        middle.setSpacing(18)
        self.chords_panel = ChordCarouselPanel(self.data.chord_names, self.data.chord_texts)
        self.battle_panel = BattlePanel(self.data.battle_text)
        middle.addWidget(self.chords_panel, 1)
        middle.addWidget(self.battle_panel, 1)
        root.addLayout(middle)

        self.player_bar = PlayerBar(self.duration)
        root.addWidget(self.player_bar)

        self.cover_card.accordsRequested.connect(self.toggle_accords)
        self.cover_card.battleRequested.connect(self.toggle_battle)
        self.player_bar.backRequested.connect(self.back_to_choice)
        self.player_bar.playPauseRequested.connect(self.pause_play)
        self.player_bar.rewindRequested.connect(self.minus_time)
        self.player_bar.forwardRequested.connect(self.plus_time)
        self.player_bar.restartRequested.connect(self.restart_audio)
        self.player_bar.seekRequested.connect(self.seek_to_progress)
        self.player_bar.volumeChanged.connect(self.change_volume)

        self.cover_card.set_accords_visible(True)
        self.cover_card.set_battle_visible(True)


    def _load_lrc_or_plain_text(self) -> None:
        self.lyrics_panel.set_lyrics(self.data.song_text)
        self.lrc_entries = []

        if self.data.lrc_path is None:
            return

        try:
            self.lrc_entries = LrcParser.parse_file(self.data.lrc_path)
            self.lyrics_panel.set_lrc_entries(self.lrc_entries)
            print(f"LRC-файл загружен: {self.data.lrc_path}")
        except Exception as error:
            self.lrc_entries = []
            self.lyrics_panel.set_lyrics(self.data.song_text)
            print(f"Ошибка чтения LRC-файла {self.data.lrc_path}: {error}")

    def _init_audio(self) -> None:
        try:
            if not pg.mixer.get_init():
                pg.mixer.init(22100)
            if self.data.audio_path is None:
                self.statusBar().showMessage("Аудиофайл не найден")
                return
            pg.mixer.music.load(str(self.data.audio_path))
            pg.mixer.music.set_volume(self.player_bar.volume_slider.value() / 100)
            pg.mixer.music.play()
            pg.mixer.music.pause()
            self.audio_ready = True
        except pg.error as error:
            self.statusBar().showMessage(f"Ошибка аудио: {error}")
            self.audio_ready = False

    def _start_timers(self) -> None:
        self.position_timer = QTimer(self)
        self.position_timer.timeout.connect(self.update_audio_position)
        self.position_timer.start(250)

    def toggle_accords(self) -> None:
        visible = not self.chords_panel.isVisible()
        self.chords_panel.setVisible(visible)
        self.cover_card.set_accords_visible(visible)

    def toggle_battle(self) -> None:
        visible = not self.battle_panel.isVisible()
        self.battle_panel.setVisible(visible)
        self.cover_card.set_battle_visible(visible)

    def back_to_choice(self) -> None:
        self.background_music.set_context("choose")
        try:
            pg.mixer.music.stop()
        except pg.error:
            pass
        self.next_window = ChooseScreen()
        self.next_window.show()
        self.close()

    def pause_play(self) -> None:
        if not self.audio_ready:
            self.statusBar().showMessage("Нечего воспроизводить: аудиофайл не загружен", 2500)
            return
        self.play = not self.play
        try:
            if self.play:
                pg.mixer.music.unpause()
            else:
                pg.mixer.music.pause()
            self.player_bar.set_playing(self.play)
        except pg.error as error:
            self.statusBar().showMessage(f"Ошибка воспроизведения: {error}")

    def seek_to_progress(self, progress: float) -> None:
        if not self.audio_ready or not self.song_length:
            return
        target = max(0.0, min(1.0, progress)) * self.song_length
        self._seek_to(target)

    def _seek_to(self, seconds: float) -> None:
        if not self.audio_ready:
            return
        try:
            self.start_pos = max(0.0, min(float(seconds), float(self.song_length or seconds)))
            pg.mixer.music.play(0, self.start_pos)
            if not self.play:
                pg.mixer.music.pause()
            self.update_audio_position(force_lrc=True)
        except pg.error as error:
            self.statusBar().showMessage(f"Ошибка перемотки: {error}")

    def change_volume(self, value: int) -> None:
        try:
            pg.mixer.music.set_volume(value / 100)
        except pg.error:
            pass

    def plus_time(self) -> None:
        self._seek(5)

    def minus_time(self) -> None:
        self._seek(-5)

    def restart_audio(self) -> None:
        if not self.audio_ready:
            return
        self.start_pos = 0.0
        try:
            pg.mixer.music.play(0, 0.0)
            if not self.play:
                pg.mixer.music.pause()
            self.update_audio_position(force_lrc=True)
        except pg.error as error:
            self.statusBar().showMessage(f"Ошибка перезапуска: {error}")

    def _seek(self, seconds: int) -> None:
        if not self.audio_ready:
            return
        self._seek_to(self.current_seconds() + seconds)

    def current_seconds(self) -> float:
        try:
            position = max(0.0, pg.mixer.music.get_pos() / 1000)
        except pg.error:
            position = 0.0
        return self.start_pos + position

    def update_audio_position(self, force_lrc: bool = False) -> None:
        current = self.current_seconds() if self.audio_ready else 0.0
        if self.song_length and current > self.song_length:
            current = float(self.song_length)
        progress = current / self.song_length if self.song_length else 0.0
        self.player_bar.set_time(self._seconds_to_time(current), progress)
        if self.lrc_entries:
            self.lyrics_panel.update_by_time(current, force=force_lrc)

    @staticmethod
    def _duration_to_seconds(value: str) -> int:
        try:
            minutes, seconds = value.split(":")[:2]
            return int(minutes) * 60 + int(seconds)
        except (ValueError, AttributeError):
            return 0

    @staticmethod
    def _seconds_to_time(value: float) -> str:
        value = max(0, int(value))
        return f"{value // 60}:{value % 60:02d}"

    @staticmethod
    def text_edit_style(font_size: int = 15) -> str:
        return f"""
            QPlainTextEdit {{
                color: {TEXT};
                background: rgba(0,0,0,0.24);
                border: 1px solid rgba(255,255,255,0.11);
                border-radius: 18px;
                padding: 14px;
                font-size: {font_size}px;
                font-family: 'Segoe UI';
            }}
        """

    @staticmethod
    def slider_style() -> str:
        return f"""
            QSlider::groove:horizontal {{
                height: 8px;
                border-radius: 4px;
                background: rgba(255,255,255,0.16);
            }}
            QSlider::handle:horizontal {{
                width: 20px;
                height: 20px;
                margin: -7px 0;
                border-radius: 10px;
                background: {ORANGE};
            }}
            QSlider::sub-page:horizontal {{
                border-radius: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 {ORANGE}, stop:1 {RED});
            }}
        """

    # Методы-совместимость со старым вариантом. Они не мешают новой логике.
    def show_battle(self):
        self.battle_panel.setVisible(True)
        self.cover_card.set_battle_visible(True)

    def hide_battle(self):
        self.battle_panel.setVisible(False)
        self.cover_card.set_battle_visible(False)

    def show_accords(self):
        self.chords_panel.setVisible(True)
        self.cover_card.set_accords_visible(True)

    def hide_accords(self):
        self.chords_panel.setVisible(False)
        self.cover_card.set_accords_visible(False)


if __name__ == "__main__":
    pg.init()
    app = QApplication(sys.argv)
    app.setApplicationName("Обучись гитаре")
    window = LearnTheGuitar()
    window.show()
    sys.exit(app.exec())
