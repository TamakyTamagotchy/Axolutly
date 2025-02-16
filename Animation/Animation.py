from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtSlot

class AnimatedProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animacion = QPropertyAnimation(self, b"value")
        self._animacion.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animacion.setDuration(350)
        self._animacion.finished.connect(self._ajustar_valor_final)
        self.setRange(0, 100)

    def setValue(self, valor):
        """Sobreescribe el valor con animación controlada"""
        try:
            valor_entero = int(valor)
        except (TypeError, ValueError):
            valor_entero = self.value()
        
        valor_ajustado = max(self.minimum(), min(valor_entero, self.maximum()))
        
        if valor_ajustado < self.value():
            self._animacion.stop()
            super().setValue(valor_ajustado)
        else:
            self._animacion.setStartValue(self.value())
            self._animacion.setEndValue(valor_ajustado)
            self._animacion.start()

    @pyqtSlot()
    def _ajustar_valor_final(self):
        """Asegura el valor final después de la animación"""
        super().setValue(self._animacion.endValue())