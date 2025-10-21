# -*- coding: utf-8 -*-
import sys
import json
import os
import warnings
from PyQt6.QtWidgets import (QApplication, QWidget, QSystemTrayIcon, QMenu, QDialog,
                             QVBoxLayout, QFormLayout, QPushButton, QSpinBox,
                             QFontComboBox, QColorDialog, QHBoxLayout, QMessageBox,
                             QMainWindow, QTextEdit, QLabel, QCheckBox, QGridLayout,
                             QSlider, QStatusBar, QComboBox, QLineEdit, QInputDialog)
from PyQt6.QtCore import Qt, QPoint, QPointF, QObject, pyqtSignal, QRect
from PyQt6.QtGui import (QPainter, QColor, QFont, QPainterPath, QPen, QIcon,
                         QPixmap, QAction, QTextCursor, QFontMetrics)

# --- КОНСТАНТЫ ---
APP_NAME = "NardiLens"
APP_VERSION = "1.5"
CONFIG_FILE = "config.json"
ICON_FILE = "icon.png"
# Нумерация теперь жестко задана в коде и не зависит от конфига
NUMBER_MAPPING = {str(i): i for i in range(1, 25)}

# --- СТРУКТУРА КОНФИГУРАЦИИ ПО УМОЛЧАНИЮ ---
def get_default_profile():
    """Возвращает структуру для одного профиля."""
    return {
        "font_settings": {
            "family": "Arial",
            "size": 30,
            "color_rgb": [255, 255, 0],   # Ярко-желтый
            "outline_color_rgb": [0, 0, 0], # Черный
            "outline_width": 4
        },
        "coordinates": []
    }

DEFAULT_CONFIG = {
    "profiles": {
        "Default": get_default_profile()
    },
    "active_profile_name": "Default",
    "main_window_geometry": [], # x, y, width, height
    "show_overlay_on_startup": True
}

# --- Вспомогательные функции ---
def get_total_screens_geometry():
    """Более надежно вычисляет общий размер всех экранов."""
    screens = QApplication.screens()
    total_rect = QRect()
    for screen in screens:
        total_rect = total_rect.united(screen.geometry())
    return total_rect

def draw_number(painter, local_pos, text, font, font_color, outline_color, outline_width):
    """Универсальная функция для отрисовки текста с обводкой."""
    path = QPainterPath()
    metrics = painter.fontMetrics()
    text_width = metrics.horizontalAdvance(text)
    text_height = metrics.boundingRect(text).height()
    adjusted_pos = QPointF(local_pos.x() - text_width / 2, local_pos.y() + text_height / 2)

    path.addText(adjusted_pos, font, text)
    painter.setPen(QPen(outline_color, outline_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(font_color)
    painter.drawPath(path)

def get_tray_icon():
    """Загружает иконку из файла icon.png или создает ее, если файл не найден."""
    if os.path.exists(ICON_FILE):
        return QIcon(ICON_FILE)
    
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#fdd835"))
    painter.drawEllipse(4, 4, 56, 56)
    painter.setPen(QColor("black"))
    painter.setFont(QFont("Arial", 32, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "N")
    painter.end()
    return QIcon(pixmap)

# --- Классы для перенаправления вывода в GUI ---
class Stream(QObject):
    """Перенаправляет вывод консоли (stdout, stderr) в QTextEdit."""
    new_text = pyqtSignal(str)
    def write(self, text): self.new_text.emit(str(text))
    def flush(self): pass

# --- Классы Окон ---

class MainWindow(QMainWindow):
    """Главное окно приложения с логом и кнопками управления."""
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(550, 450)
        self.statusBar().showMessage("Загрузка...")
        self._create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Profile Management
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Профиль:"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self.controller.switch_profile)
        profile_layout.addWidget(self.profile_combo)
        
        self.add_profile_button = QPushButton("+")
        self.add_profile_button.setToolTip("Создать новый профиль")
        self.add_profile_button.setFixedWidth(30)
        self.add_profile_button.clicked.connect(self.controller.add_profile)
        profile_layout.addWidget(self.add_profile_button)

        self.rename_profile_button = QPushButton("Переименовать")
        self.rename_profile_button.setToolTip("Переименовать текущий профиль")
        self.rename_profile_button.clicked.connect(self.controller.rename_profile)
        profile_layout.addWidget(self.rename_profile_button)

        self.remove_profile_button = QPushButton("-")
        self.remove_profile_button.setToolTip("Удалить текущий профиль")
        self.remove_profile_button.setFixedWidth(30)
        self.remove_profile_button.clicked.connect(self.controller.remove_profile)
        profile_layout.addWidget(self.remove_profile_button)
        layout.addLayout(profile_layout)

        button_grid = QGridLayout()
        self.toggle_button = QPushButton("Скрыть оверлей")
        self.toggle_button.setToolTip("Показать или скрыть номера на экране")
        self.toggle_button.clicked.connect(self.controller.toggle_overlay_visibility)
        
        self.config_button = QPushButton("Настроить координаты")
        self.config_button.setToolTip("Перейти в режим расстановки номеров на экране")
        self.config_button.clicked.connect(self.controller.start_config_mode)

        self.settings_button = QPushButton("Настройки оформления...")
        self.settings_button.setToolTip("Открыть окно для изменения шрифта, цвета и размера номеров")
        self.settings_button.clicked.connect(self.controller.open_settings_window)

        self.clear_coords_button = QPushButton("Очистить координаты")
        self.clear_coords_button.setToolTip("Удалить текущую расстановку номеров для этого профиля")
        self.clear_coords_button.clicked.connect(self.controller.clear_coordinates)
        
        button_grid.addWidget(self.toggle_button, 0, 0, 1, 2)
        button_grid.addWidget(self.config_button, 1, 0)
        button_grid.addWidget(self.clear_coords_button, 1, 1)
        button_grid.addWidget(self.settings_button, 2, 0, 1, 2)
        layout.addLayout(button_grid)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)
        
        self.autostart_checkbox = QCheckBox("Показывать оверлей при запуске")
        self.autostart_checkbox.setToolTip("Если включено, номера будут показаны сразу после запуска программы")
        self.autostart_checkbox.setChecked(self.controller.config.get("show_overlay_on_startup", True))
        self.autostart_checkbox.toggled.connect(self.controller.set_autostart_overlay)
        layout.addWidget(self.autostart_checkbox)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&Файл")
        exit_action = QAction("&Выход", self)
        exit_action.triggered.connect(self.controller.app.quit)
        file_menu.addAction(exit_action)
        help_menu = menu_bar.addMenu("&Справка")
        about_action = QAction("&О программе", self)
        about_action.triggered.connect(self.controller.show_about_dialog)
        help_menu.addAction(about_action)

    def update_log(self, text):
        self.log_box.moveCursor(QTextCursor.MoveOperation.End)
        self.log_box.insertPlainText(text)

    def closeEvent(self, event):
        self.controller.config['main_window_geometry'] = self.geometry().getRect()
        self.controller.save_config()
        event.ignore()
        self.hide()
        self.controller.tray_icon.showMessage(
            f"{APP_NAME} работает",
            "Окно свернуто в трей. Для выхода используйте меню.",
            QSystemTrayIcon.MessageIcon.Information, 2000
        )

    def update_toggle_button_text(self, is_visible):
        self.toggle_button.setText("Скрыть оверлей" if is_visible else "Показать оверлей")

    def update_profile_list(self, profiles, active_profile):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(profiles)
        self.profile_combo.setCurrentText(active_profile)
        self.profile_combo.blockSignals(False)


class SettingsWindow(QDialog):
    """Окно для визуальной настройки с живым предпросмотром."""
    def __init__(self, current_font_config, parent=None):
        super().__init__(parent)
        self.font_config = current_font_config
        self.setWindowTitle("Настройки оформления")
        self.setModal(True)
        self.initUI()
        self._update_preview()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        fs = self.font_config

        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(fs['family']))
        self.font_combo.currentFontChanged.connect(self._update_preview)
        form_layout.addRow("Шрифт:", self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.setValue(fs['size'])
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(8, 72)
        self.font_size_slider.setValue(fs['size'])
        self.font_size_spin.valueChanged.connect(self.font_size_slider.setValue)
        self.font_size_slider.valueChanged.connect(self.font_size_spin.setValue)
        self.font_size_spin.valueChanged.connect(self._update_preview)
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.font_size_spin)
        size_layout.addWidget(self.font_size_slider)
        form_layout.addRow("Размер шрифта:", size_layout)

        self.font_color_button = QPushButton()
        self.font_color = QColor(*fs['color_rgb'])
        self.update_button_color(self.font_color_button, self.font_color)
        self.font_color_button.clicked.connect(lambda: self.select_color('font'))
        form_layout.addRow("Цвет текста:", self.font_color_button)

        self.outline_color_button = QPushButton()
        self.outline_color = QColor(*fs['outline_color_rgb'])
        self.update_button_color(self.outline_color_button, self.outline_color)
        self.outline_color_button.clicked.connect(lambda: self.select_color('outline'))
        form_layout.addRow("Цвет обводки:", self.outline_color_button)

        self.outline_width_spin = QSpinBox()
        self.outline_width_spin.setRange(0, 20)
        self.outline_width_spin.setValue(fs['outline_width'])
        self.outline_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.outline_width_slider.setRange(0, 20)
        self.outline_width_slider.setValue(fs['outline_width'])
        self.outline_width_spin.valueChanged.connect(self.outline_width_slider.setValue)
        self.outline_width_slider.valueChanged.connect(self.outline_width_spin.setValue)
        self.outline_width_spin.valueChanged.connect(self._update_preview)
        width_layout = QHBoxLayout()
        width_layout.addWidget(self.outline_width_spin)
        width_layout.addWidget(self.outline_width_slider)
        form_layout.addRow("Толщина обводки:", width_layout)
        
        main_layout.addLayout(form_layout)

        self.preview_label = QLabel("Предпросмотр")
        self.preview_label.setMinimumSize(200, 100)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #555; border: 1px solid #888; border-radius: 5px;")
        main_layout.addWidget(self.preview_label)

        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("Сбросить по умолчанию")
        self.reset_button.clicked.connect(self._reset_to_defaults)
        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

    def _update_preview(self):
        font = self.font_combo.currentFont()
        font.setPointSize(self.font_size_spin.value())
        font.setBold(True)
        pixmap = QPixmap(self.preview_label.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_number(painter, pixmap.rect().center(), "12", font, 
                    self.font_color, self.outline_color, 
                    self.outline_width_spin.value())
        painter.end()
        self.preview_label.setPixmap(pixmap)
        
    def _reset_to_defaults(self):
        defaults = get_default_profile()['font_settings']
        self.font_combo.setCurrentFont(QFont(defaults['family']))
        self.font_size_spin.setValue(defaults['size'])
        self.font_color = QColor(*defaults['color_rgb'])
        self.update_button_color(self.font_color_button, self.font_color)
        self.outline_color = QColor(*defaults['outline_color_rgb'])
        self.update_button_color(self.outline_color_button, self.outline_color)
        self.outline_width_spin.setValue(defaults['outline_width'])
        self._update_preview()

    def select_color(self, target):
        initial_color = self.font_color if target == 'font' else self.outline_color
        color = QColorDialog.getColor(initial_color, self, "Выберите цвет")
        if color.isValid():
            if target == 'font':
                self.font_color = color
                self.update_button_color(self.font_color_button, color)
            else:
                self.outline_color = color
                self.update_button_color(self.outline_color_button, color)
            self._update_preview()

    def update_button_color(self, button, color):
        button.setStyleSheet(f"background-color: {color.name()}; color: {'white' if color.lightness() < 128 else 'black'}; border: 1px solid #888;")
        button.setText(color.name())

    def get_settings(self):
        return {
            "family": self.font_combo.currentFont().family(),
            "size": self.font_size_spin.value(),
            "color_rgb": self.font_color.getRgb()[:3],
            "outline_color_rgb": self.outline_color.getRgb()[:3],
            "outline_width": self.outline_width_spin.value()
        }

class OverlayWindow(QWidget):
    """Основное окно оверлея, отображающее номера на заданных координатах."""
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setGeometry(get_total_screens_geometry())
        self.update_fonts_from_config()
        self.initUI()

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def update_fonts_from_config(self):
        active_profile = self.controller.get_active_profile()
        if not active_profile: return
        fs = active_profile['font_settings']
        self.main_font = QFont(fs['family'], fs['size'], QFont.Weight.Bold)
        self.font_color = QColor(*fs['color_rgb'])
        self.outline_color = QColor(*fs['outline_color_rgb'])
        self.outline_width = fs['outline_width']
        self.update()

    def paintEvent(self, event):
        active_profile = self.controller.get_active_profile()
        if not active_profile or not active_profile.get("coordinates"): return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, (x, y) in enumerate(active_profile["coordinates"]):
            local_pos = self.mapFromGlobal(QPoint(x, y))
            display_num = NUMBER_MAPPING.get(str(i + 1))
            if display_num is not None:
                draw_number(painter, local_pos, str(display_num), self.main_font,
                            self.font_color, self.outline_color, self.outline_width)

class ConfigOverlay(QWidget):
    """Окно для режима настройки координат."""
    config_finished = pyqtSignal(list)
    config_cancelled = pyqtSignal()

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setGeometry(get_total_screens_geometry())
        self.new_coords = []
        self.mouse_pos = QPoint(0, 0)
        self.update_fonts_from_config()
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def update_fonts_from_config(self):
        active_profile = self.controller.get_active_profile()
        if not active_profile: return
        fs = active_profile['font_settings']
        self.main_font = QFont(fs['family'], fs['size'], QFont.Weight.Bold)
        self.font_color = QColor(*fs['color_rgb'])
        self.outline_color = QColor(*fs['outline_color_rgb'])
        self.outline_width = fs['outline_width']
        self.title_font = QFont("Arial", 28, QFont.Weight.Bold)
        self.info_font = QFont("Arial", 18)
        self.total_points = len(NUMBER_MAPPING)

    def wheelEvent(self, event):
        active_profile = self.controller.get_active_profile()
        if not active_profile: return
        current_size = active_profile['font_settings']['size']
        delta = 1 if event.angleDelta().y() > 0 else -1
        new_size = max(8, min(72, current_size + delta))
        
        if new_size != current_size:
            active_profile['font_settings']['size'] = new_size
            self.update_fonts_from_config()
            self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape: self.config_cancelled.emit()

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.position().toPoint()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if len(self.new_coords) < self.total_points:
                pos = event.globalPosition().toPoint()
                self.new_coords.append([pos.x(), pos.y()])
                click_num = len(self.new_coords)
                display_num = NUMBER_MAPPING.get(str(click_num), '?')
                print(f"Точка {click_num}/{self.total_points} добавлена. Отображаемый номер: {display_num}.")
                if len(self.new_coords) >= self.total_points:
                    self.config_finished.emit(self.new_coords)
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            if self.new_coords:
                self.new_coords.pop()
                print(f"Последняя точка удалена. Осталось {len(self.new_coords)}.")
                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))
        for i, pos in enumerate(self.new_coords):
            local_pos = self.mapFromGlobal(QPoint(pos[0], pos[1]))
            display_num = NUMBER_MAPPING.get(str(i + 1))
            if display_num is not None:
                draw_number(painter, local_pos, str(display_num), self.main_font,
                            self.font_color, self.outline_color, self.outline_width)
        current_index = len(self.new_coords)
        if current_index < self.total_points:
            painter.setOpacity(0.7)
            preview_num = NUMBER_MAPPING.get(str(current_index + 1))
            if preview_num is not None:
                draw_number(painter, self.mouse_pos, str(preview_num), self.main_font,
                            self.font_color, self.outline_color, self.outline_width)
            painter.setOpacity(1.0)
            
            center_point = self.rect().center()
            banner_width, banner_height = 600, 240
            banner_rect = QRect(0, 0, banner_width, banner_height)
            banner_rect.moveCenter(center_point)

            painter.setBrush(QColor(0, 0, 0, 180))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(banner_rect, 15, 15)
            
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(self.title_font)
            title_rect = QRect(banner_rect.x(), banner_rect.y() + 15, banner_width, 50)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignHCenter, "РЕЖИМ НАСТРОЙКИ")

            painter.setFont(self.info_font)
            info_text = (
                f"Кликните на пункт №{current_index + 1} / {self.total_points}\n\n"
                "Правая кнопка мыши: отменить последнее действие\n"
                "Колесико мыши: изменить размер шрифта\n"
                "ESC: выйти из настройки"
            )
            text_rect = QRect(banner_rect.x(), banner_rect.y() + 60, banner_width, 160)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, info_text)


# --- Главный класс приложения ---
class TrayAppController(QObject):
    """Управляет окнами, конфигурацией и иконкой в системном трее."""
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.app.setQuitOnLastWindowClosed(False)
        self.is_config_mode = False
        
        self.load_config()
        self.main_window = MainWindow(self)
        self.main_window.update_profile_list(list(self.config['profiles'].keys()), self.config['active_profile_name'])

        if self.config.get("main_window_geometry"):
            try: self.main_window.setGeometry(*self.config["main_window_geometry"])
            except Exception as e: print(f"Не удалось восстановить геометрию окна: {e}")

        self.redirect_stdout()
        
        self.overlay_window = OverlayWindow(self)
        self.config_window = ConfigOverlay(self)

        self.config_window.config_finished.connect(self.on_config_finished)
        self.config_window.config_cancelled.connect(lambda: self.stop_config_mode(cancelled=True))

        self.setup_tray_icon()
        self.main_window.show()
        
        active_profile = self.get_active_profile()
        if self.config.get("show_overlay_on_startup", True) and active_profile and active_profile.get("coordinates"):
            self.overlay_window.show()
        else:
            self.overlay_window.hide()
            if not active_profile or not active_profile.get("coordinates"):
                 print(f"--- Добро пожаловать в {APP_NAME}! ---\nКоординаты для профиля '{self.config['active_profile_name']}' еще не настроены.")
        
        self.update_all_ui()

    def redirect_stdout(self):
        sys.stdout = Stream(new_text=self.main_window.update_log)
        sys.stderr = Stream(new_text=self.main_window.update_log)

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(get_tray_icon(), self)
        self.tray_icon.setToolTip(APP_NAME)
        menu = QMenu()
        show_main_window_action = QAction("Панель управления", self)
        show_main_window_action.triggered.connect(self.show_main_window)
        self.toggle_action = QAction("Скрыть оверлей", self)
        self.toggle_action.triggered.connect(self.toggle_overlay_visibility)
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.app.quit)
        menu.addAction(show_main_window_action)
        menu.addAction(self.toggle_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def show_about_dialog(self):
        QMessageBox.about(self.main_window, f"О программе {APP_NAME}", f"<h3>{APP_NAME} v{APP_VERSION}</h3>"
            "<p>Утилита для отображения числового оверлея поверх экрана.</p>"
            "<p>Все управление доступно из панели управления.</p>")

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick: self.show_main_window()

    def show_main_window(self):
        self.main_window.show()
        self.main_window.activateWindow()

    def migrate_old_config(self, old_config):
        """Преобразует старый формат конфига в новый с профилями."""
        print("Обнаружена старая версия конфига. Выполняется миграция...")
        new_config = get_default_profile()
        new_config["font_settings"] = old_config.get("font_settings", new_config["font_settings"])
        new_config["coordinates"] = old_config.get("coordinates", new_config["coordinates"])
        
        final_config = DEFAULT_CONFIG.copy()
        final_config["profiles"]["Default"] = new_config
        final_config["main_window_geometry"] = old_config.get("main_window_geometry", [])
        final_config["show_overlay_on_startup"] = old_config.get("show_overlay_on_startup", True)
        return final_config

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: config_data = json.load(f)
                if "profiles" not in config_data:
                    self.config = self.migrate_old_config(config_data)
                    self.save_config()
                else:
                    self.config = config_data
            except (json.JSONDecodeError, IOError): self.config = DEFAULT_CONFIG.copy()
        else: self.config = DEFAULT_CONFIG.copy()
        
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=4, ensure_ascii=False)
            print(f"Конфигурация сохранена в {CONFIG_FILE}.")
        except IOError as e: print(f"Не удалось сохранить конфигурацию: {e}")
    
    def get_active_profile(self):
        return self.config["profiles"].get(self.config["active_profile_name"])

    def set_autostart_overlay(self, checked):
        self.config['show_overlay_on_startup'] = checked
        self.save_config()

    def open_settings_window(self):
        if self.is_config_mode: return
        active_profile = self.get_active_profile()
        if not active_profile: return
        dialog = SettingsWindow(active_profile['font_settings'], self.main_window)
        if dialog.exec():
            active_profile['font_settings'] = dialog.get_settings()
            self.save_config()
            self.overlay_window.update_fonts_from_config()
            self.config_window.update_fonts_from_config()
            print("Настройки оформления обновлены.")
            
    def update_all_ui(self):
        self.update_toggle_action_text()
        self.update_button_states()
        self.update_status_bar()
        self.main_window.update_profile_list(list(self.config['profiles'].keys()), self.config['active_profile_name'])
        self.overlay_window.update_fonts_from_config()

    def update_status_bar(self):
        active_profile = self.get_active_profile()
        if not active_profile or not active_profile.get("coordinates"):
            status = f"Профиль '{self.config['active_profile_name']}': Координаты не настроены"
        else:
            status = f"Профиль '{self.config['active_profile_name']}': Оверлей {'активен' if self.overlay_window.isVisible() else 'скрыт'}"
        self.main_window.statusBar().showMessage(status)

    def update_button_states(self):
        active_profile = self.get_active_profile()
        has_coords = bool(active_profile and active_profile.get("coordinates"))
        self.main_window.toggle_button.setEnabled(has_coords)
        self.main_window.clear_coords_button.setEnabled(has_coords)
        self.toggle_action.setEnabled(has_coords)
        tooltip = "Сначала настройте координаты" if not has_coords else ""
        self.main_window.toggle_button.setToolTip(tooltip)
        self.main_window.clear_coords_button.setToolTip(tooltip)
        self.toggle_action.setToolTip(tooltip)
        # Нельзя удалить последний профиль
        self.main_window.remove_profile_button.setEnabled(len(self.config['profiles']) > 1)

    def update_toggle_action_text(self):
        is_visible = self.overlay_window.isVisible()
        text = "Скрыть оверлей" if is_visible else "Показать оверлей"
        self.toggle_action.setText(text)
        self.main_window.update_toggle_button_text(is_visible)

    def toggle_overlay_visibility(self):
        if self.is_config_mode: return
        active_profile = self.get_active_profile()
        if not active_profile or not active_profile.get("coordinates"): return
        self.overlay_window.setVisible(not self.overlay_window.isVisible())
        self.update_toggle_action_text()
        print(f"Оверлей {'показан.' if self.overlay_window.isVisible() else 'скрыт.'}")
        self.update_status_bar()

    def start_config_mode(self):
        if self.is_config_mode: return
        self.is_config_mode = True
        self.overlay_window.hide()
        self.config_window.new_coords.clear()
        self.config_window.update_fonts_from_config()
        self.config_window.update()
        self.config_window.show()
        self.config_window.activateWindow()
        self.config_window.raise_()
        self.main_window.hide()
        print("\n--- Режим настройки АКТИВИРОВАН ---")
        self.main_window.statusBar().showMessage("Режим настройки...")

    def stop_config_mode(self, cancelled=False):
        if not self.is_config_mode: return
        self.is_config_mode = False
        self.config_window.hide()
        self.show_main_window()
        active_profile = self.get_active_profile()
        if self.config.get("show_overlay_on_startup", True) and active_profile and active_profile.get("coordinates"):
             self.overlay_window.show()
        self.update_all_ui()
        if cancelled: print("Настройка отменена пользователем.")
        print("--- Режим настройки ВЫКЛЮЧЕН ---\n")

    def clear_coordinates(self):
        if self.is_config_mode: return
        active_profile = self.get_active_profile()
        if not active_profile: return
        reply = QMessageBox.question(self.main_window, "Подтверждение",
                                     f"Вы уверены, что хотите очистить все координаты для профиля '{self.config['active_profile_name']}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            active_profile["coordinates"] = []
            self.save_config()
            self.overlay_window.update()
            self.overlay_window.hide()
            self.update_all_ui()
            print("Координаты очищены.")

    def on_config_finished(self, new_coords):
        active_profile = self.get_active_profile()
        if not active_profile: return
        print(f"Настройка завершена. Получено {len(new_coords)} точек.")
        active_profile["coordinates"] = new_coords
        self.save_config()
        self.stop_config_mode()

    # --- Profile Management Methods ---
    def switch_profile(self, index):
        profile_name = self.main_window.profile_combo.itemText(index)
        if not profile_name or profile_name == self.config['active_profile_name']: return
        self.config['active_profile_name'] = profile_name
        print(f"Активен профиль: {profile_name}")
        self.overlay_window.hide()
        if self.config.get("show_overlay_on_startup", True):
            active_profile = self.get_active_profile()
            if active_profile and active_profile.get("coordinates"):
                self.overlay_window.show()
        self.update_all_ui()

    def add_profile(self):
        text, ok = QInputDialog.getText(self.main_window, 'Новый профиль', 'Введите имя нового профиля:')
        if ok and text:
            if text in self.config['profiles']:
                QMessageBox.warning(self.main_window, "Ошибка", "Профиль с таким именем уже существует.")
                return
            self.config['profiles'][text] = get_default_profile()
            self.config['active_profile_name'] = text
            self.save_config()
            self.update_all_ui()
            print(f"Создан и активирован профиль: {text}")

    def rename_profile(self):
        old_name = self.config['active_profile_name']
        text, ok = QInputDialog.getText(self.main_window, 'Переименовать профиль', 'Введите новое имя:', text=old_name)
        if ok and text and text != old_name:
            if text in self.config['profiles']:
                QMessageBox.warning(self.main_window, "Ошибка", "Профиль с таким именем уже существует.")
                return
            self.config['profiles'][text] = self.config['profiles'].pop(old_name)
            self.config['active_profile_name'] = text
            self.save_config()
            self.update_all_ui()
            print(f"Профиль '{old_name}' переименован в '{text}'.")

    def remove_profile(self):
        if len(self.config['profiles']) <= 1:
            QMessageBox.warning(self.main_window, "Ошибка", "Нельзя удалить последний профиль.")
            return
        
        profile_to_remove = self.config['active_profile_name']
        reply = QMessageBox.question(self.main_window, "Подтверждение",
                                     f"Вы уверены, что хотите удалить профиль '{profile_to_remove}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.config['profiles'][profile_to_remove]
            # Switch to the first available profile
            self.config['active_profile_name'] = next(iter(self.config['profiles']))
            self.save_config()
            self.overlay_window.hide()
            self.update_all_ui()
            print(f"Профиль '{profile_to_remove}' удален.")


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    app = QApplication(sys.argv)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Ошибка", "Системный трей недоступен. Приложение не может быть запущено.")
        return -1
    
    controller = TrayAppController(app)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

