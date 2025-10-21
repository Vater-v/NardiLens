import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QPainter, QColor, QFont

# Создаем общий список для хранения координат со всех экранов
collected_points = []

class CoordinateFinder(QMainWindow):
    """
    Улучшенная версия для сбора координат.
    - Работает на нескольких мониторах.
    - Показывает номера сразу после клика.
    - Позволяет отменять последнее действие правой кнопкой мыши.
    """
    def __init__(self, screen_geometry):
        super().__init__()
        self.setGeometry(screen_geometry)
        
        # Флаги окна: без рамки, всегда наверху
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowOpacity(0.3) # Полупрозрачность
        
        # Включаем отслеживание мыши, чтобы показывать превью номера
        self.setMouseTracking(True)
        self.mouse_pos = QPoint(0, 0)

        # Обновляем инструкцию
        self.label = QLabel(
            "ЛКМ: добавить номер\n"
            "ПКМ: убрать последний номер\n"
            "ESC: завершить и вывести координаты",
            self
        )
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 24px; background-color: rgba(0, 0, 0, 0.7); padding: 10px; border-radius: 5px;")
        self.label.adjustSize()
        self.label.move(
            int((self.width() - self.label.width()) / 2),
            int((self.height() - self.label.height()) / 2)
        )

    def mousePressEvent(self, event: QMouseEvent):
        """ Обработчик клика мыши. """
        # Левая кнопка - добавить точку
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint()
            collected_points.append((pos.x(), pos.y()))
            print(f"Добавлена точка {len(collected_points)}: ({pos.x()}, {pos.y()})")
        
        # Правая кнопка - убрать последнюю точку
        elif event.button() == Qt.MouseButton.RightButton:
            if collected_points:
                removed = collected_points.pop()
                print(f"Удалена последняя точка: {removed}")
            else:
                print("Список точек пуст.")
        
        # Обновляем все открытые окна, чтобы перерисовать номера
        for window in QApplication.instance().topLevelWidgets():
            if isinstance(window, CoordinateFinder):
                window.update()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """ Отслеживание курсора для превью. """
        self.mouse_pos = event.pos()
        self.update() # Перерисовываем, чтобы показать превью

    def keyPressEvent(self, event: QKeyEvent):
        """ Обработчик нажатия клавиши. """
        if event.key() == Qt.Key.Key_Escape:
            print("\n--- Сбор координат завершен ---")
            print("Скопируйте этот список в overlay_app.py:\n")
            print("COORDS = [")
            for point in collected_points:
                print(f"    {point},")
            print("]")
            # Закрываем всё приложение
            QApplication.instance().quit()

    def paintEvent(self, event):
        """ Событие отрисовки номеров на экране. """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont('Arial', 16, QFont.Weight.Bold))

        # Рисуем все подтвержденные номера
        for i, (x, y) in enumerate(collected_points):
            # Координаты глобальные, а рисовать надо в локальных координатах окна
            # Поэтому переводим глобальные в локальные
            local_pos = self.mapFromGlobal(QPoint(x, y))
            painter.drawText(local_pos, str(i + 1))
            
        # Рисуем полупрозрачное превью следующего номера под курсором
        next_number = str(len(collected_points) + 1)
        painter.setPen(QColor(255, 255, 255, 150)) # Белый, но полупрозрачный
        painter.drawText(self.mouse_pos, next_number)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Получаем геометрию всех экранов и создаем окно для каждого
    screens = app.screens()
    windows = []
    for screen in screens:
        finder = CoordinateFinder(screen.geometry())
        finder.show()
        windows.append(finder)

    sys.exit(app.exec())

