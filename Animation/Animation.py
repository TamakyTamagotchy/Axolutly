from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
from config.logger import Config

# Clase de barra de progreso animada
class AnimatedProgressBar(QProgressBar):
    """Barra de progreso animada."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.setDuration(Config.ANIMATION_DURATION)
        self._animation.finished.connect(self._on_animation_finished)

    def setValue(self, value):
        if value < self.value():
            super().setValue(value)
        else:
            self._animation.stop()
            self._animation.setStartValue(self.value())
            self._animation.setEndValue(value)
            self._animation.start()

    def _on_animation_finished(self):
        # Asegurarse de que el valor final se establezca correctamente
        super().setValue(self._animation.endValue())
