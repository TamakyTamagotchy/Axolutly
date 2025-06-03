from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer
from typing import Optional

class AnimatedProgressBar(QProgressBar):
    """
    Barra de progreso animada con control de velocidad y optimización de actualizaciones.
    """
    def __init__(self, parent=None, animation_duration: Optional[int] = 250):
        super().__init__(parent)
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.setDuration(animation_duration or 250)
        self.setRange(0, 100)
        self.setTextVisible(True)
        self.setFormat("%p%")
        
        # Optimización de actualizaciones
        self._update_timer = QTimer()
        self._update_timer.setInterval(100)  # Limitar actualizaciones a 10 por segundo
        self._update_timer.timeout.connect(self._process_pending_update)
        self._pending_value = None
        
    def setValue(self, value: int) -> None:
        """Establece el valor de la barra de progreso con animación."""
        if not self._update_timer.isActive():
            self._process_value(value)
            self._update_timer.start()
        else:
            self._pending_value = value
            
    def _process_pending_update(self) -> None:
        if self._pending_value is not None:
            self._process_value(self._pending_value)
            self._pending_value = None
        self._update_timer.stop()
            
    def _process_value(self, value: int) -> None:
        if self._animation.state() == QPropertyAnimation.State.Running:
            self._animation.stop()
        
        current = self.value()
        if abs(current - value) > 10:
            # Animación más rápida para cambios grandes
            self._animation.setDuration(150)
        else:
            self._animation.setDuration(250)
            
        self._animation.setStartValue(current)
        self._animation.setEndValue(value)
        self._animation.start()

    def reset(self) -> None:
        """Resetea la barra de progreso y detiene la animación."""
        self._animation.stop()
        super().reset()