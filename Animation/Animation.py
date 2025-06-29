from PyQt6.QtWidgets import QProgressBar,QWidget, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, QParallelAnimationGroup, QSequentialAnimationGroup, pyqtSignal
from PyQt6.QtGui import QColor
from typing import Optional
from enum import Enum


class AnimationType(Enum):
    """Tipos de animación disponibles"""
    EASE_IN = QEasingCurve.Type.InCubic
    EASE_OUT = QEasingCurve.Type.OutCubic
    EASE_IN_OUT = QEasingCurve.Type.InOutCubic
    BOUNCE = QEasingCurve.Type.OutBounce
    ELASTIC = QEasingCurve.Type.OutElastic
    SMOOTH = QEasingCurve.Type.OutQuart


class AnimatedProgressBar(QProgressBar):
    """
    Barra de progreso animada con efectos visuales avanzados y optimización de rendimiento.
    """
    
    # Señales personalizadas
    animation_started = pyqtSignal()
    animation_finished = pyqtSignal()
    value_threshold_reached = pyqtSignal(int)  # Emite cuando se alcanza un umbral específico
    
    def __init__(self, parent=None, animation_duration: Optional[int] = 250):
        super().__init__(parent)
        
        # Configuración básica
        self._animation_duration = animation_duration or 250
        self._setup_animations()
        self._setup_effects()
        self._setup_optimization()
        
        # Estado interno
        self._thresholds = [25, 50, 75, 100]  # Umbrales para notificaciones
        self._reached_thresholds = set()
        self._last_animated_value = 0
        
        # Configuración inicial
        self.setRange(0, 100)
        self.setTextVisible(True)
        self.setFormat("%p%")
        
    def _setup_animations(self):
        """Configura las animaciones principales"""
        self._value_animation = QPropertyAnimation(self, b"value")
        self._value_animation.setEasingCurve(AnimationType.EASE_OUT.value)
        self._value_animation.setDuration(self._animation_duration)
        self._value_animation.finished.connect(self.animation_finished.emit)
        
        # Grupo de animaciones paralelas para efectos visuales
        self._effect_animations = QParallelAnimationGroup()
        
    def _setup_effects(self):
        """Configura efectos visuales"""
        # Efecto de sombra
        self._shadow_effect = QGraphicsDropShadowEffect()
        self._shadow_effect.setBlurRadius(10)
        self._shadow_effect.setColor(QColor(0, 0, 0, 50))
        self._shadow_effect.setOffset(0, 2)
        self.setGraphicsEffect(self._shadow_effect)
        
        # Efecto de opacidad para transiciones suaves
        self._opacity_effect = QGraphicsOpacityEffect()
        self._opacity_effect.setOpacity(1.0)
        
    def _setup_optimization(self):
        """Configura optimizaciones de rendimiento"""
        # Timer para limitar actualizaciones
        self._update_timer = QTimer()
        self._update_timer.setInterval(16)  # 60 FPS máximo
        self._update_timer.timeout.connect(self._process_pending_update)
        self._update_timer.setSingleShot(True)
        
        # Cola de valores pendientes
        self._pending_value = None
        self._animation_queue = []
        
    def setValue(self, value: int) -> None:
        """Establece el valor con animación optimizada"""
        value = max(self.minimum(), min(self.maximum(), value))
        
        # Optimización: evitar animaciones innecesarias
        if value == self.value():
            return
            
        # Control de umbral
        self._check_thresholds(value)
        
        if not self._update_timer.isActive():
            self._process_value(value)
            self._update_timer.start()
        else:
            self._pending_value = value
    
    def _process_pending_update(self) -> None:
        """Procesa actualizaciones pendientes"""
        if self._pending_value is not None:
            self._process_value(self._pending_value)
            self._pending_value = None
    
    def _process_value(self, value: int) -> None:
        """Procesa el valor con animación inteligente"""
        if self._value_animation.state() == QPropertyAnimation.State.Running:
            self._value_animation.stop()
        
        current = self.value()
        difference = abs(current - value)
        
        # Animación adaptativa basada en la diferencia
        if difference > 20:
            # Cambio grande: animación rápida
            self._value_animation.setDuration(100)
            self._value_animation.setEasingCurve(AnimationType.EASE_IN_OUT.value)
        elif difference > 5:
            # Cambio medio: animación normal
            self._value_animation.setDuration(self._animation_duration)
            self._value_animation.setEasingCurve(AnimationType.EASE_OUT.value)
        else:
            # Cambio pequeño: animación suave
            self._value_animation.setDuration(self._animation_duration * 2)
            self._value_animation.setEasingCurve(AnimationType.SMOOTH.value)
        
        self._value_animation.setStartValue(current)
        self._value_animation.setEndValue(value)
        
        self.animation_started.emit()
        self._value_animation.start()
        self._last_animated_value = value
    
    def _check_thresholds(self, value: int):
        """Verifica y emite señales de umbral"""
        for threshold in self._thresholds:
            if (value >= threshold and threshold not in self._reached_thresholds):
                self._reached_thresholds.add(threshold)
                self.value_threshold_reached.emit(threshold)
    
    def setAnimationType(self, animation_type: AnimationType):
        """Establece el tipo de animación"""
        self._value_animation.setEasingCurve(animation_type.value)
    
    def setAnimationDuration(self, duration: int):
        """Establece la duración de la animación"""
        self._animation_duration = duration
        self._value_animation.setDuration(duration)
    
    def addThreshold(self, threshold: int):
        """Añade un umbral personalizado"""
        if self.minimum() <= threshold <= self.maximum():
            self._thresholds.append(threshold)
            self._thresholds.sort()
    
    def removeThreshold(self, threshold: int):
        """Elimina un umbral"""
        if threshold in self._thresholds:
            self._thresholds.remove(threshold)
            self._reached_thresholds.discard(threshold)
    
    def pulse_animation(self, duration: int = 1000):
        """Crea un efecto de pulso en la barra"""
        pulse_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        pulse_animation.setDuration(duration // 2)
        pulse_animation.setStartValue(1.0)
        pulse_animation.setEndValue(0.5)
        pulse_animation.setEasingCurve(AnimationType.EASE_IN_OUT.value)
        
        pulse_back = QPropertyAnimation(self._opacity_effect, b"opacity")
        pulse_back.setDuration(duration // 2)
        pulse_back.setStartValue(0.5)
        pulse_back.setEndValue(1.0)
        pulse_back.setEasingCurve(AnimationType.EASE_IN_OUT.value)
        
        pulse_sequence = QSequentialAnimationGroup()
        pulse_sequence.addAnimation(pulse_animation)
        pulse_sequence.addAnimation(pulse_back)
        pulse_sequence.start()
        
        return pulse_sequence
    
    def glow_effect(self, color: QColor = None, intensity: int = 20):
        """Añade efecto de brillo/resplandor"""
        if color is None:
            color = QColor(99, 102, 241, 100)  # Color primario por defecto
            
        self._shadow_effect.setColor(color)
        self._shadow_effect.setBlurRadius(intensity)
        
        # Animar el brillo
        glow_animation = QPropertyAnimation(self._shadow_effect, b"blurRadius")
        glow_animation.setDuration(500)
        glow_animation.setStartValue(10)
        glow_animation.setEndValue(intensity)
        glow_animation.setEasingCurve(AnimationType.EASE_OUT.value)
        glow_animation.start()
        
        return glow_animation
    
    def shake_animation(self, duration: int = 500, intensity: int = 5):
        """Crea una animación de vibración/shake"""
        shake_group = QSequentialAnimationGroup()
        
        for i in range(4):  # 4 movimientos
            move_right = QPropertyAnimation(self, b"pos")
            move_right.setDuration(duration // 8)
            current_pos = self.pos()
            move_right.setStartValue(current_pos)
            move_right.setEndValue(current_pos + self.rect().topLeft() + self.rect().topLeft() * intensity)
            
            move_left = QPropertyAnimation(self, b"pos")
            move_left.setDuration(duration // 8)
            move_left.setStartValue(current_pos + self.rect().topLeft() * intensity)
            move_left.setEndValue(current_pos)
            
            shake_group.addAnimation(move_right)
            shake_group.addAnimation(move_left)
        
        shake_group.start()
        return shake_group
    
    def reset(self) -> None:
        """Resetea la barra de progreso y limpia el estado"""
        self._value_animation.stop()
        self._reached_thresholds.clear()
        self._pending_value = None
        self._last_animated_value = 0
        super().reset()
    
    def isAnimating(self) -> bool:
        """Verifica si hay una animación en progreso"""
        return self._value_animation.state() == QPropertyAnimation.State.Running
    
    def stopAnimation(self):
        """Detiene todas las animaciones"""
        self._value_animation.stop()
        self._effect_animations.stop()
        self._update_timer.stop()


class AnimatedWidget:
    """
    Clase utilitaria para añadir animaciones a cualquier widget.
    """
    
    @staticmethod
    def fade_in(widget: QWidget, duration: int = 300, delay: int = 0) -> QPropertyAnimation:
        """Animación de aparición gradual con soporte opcional de delay (ms)"""
        def start_animation():
            effect = QGraphicsOpacityEffect()
            widget.setGraphicsEffect(effect)
            animation = QPropertyAnimation(effect, b"opacity")
            animation.setDuration(duration)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.setEasingCurve(AnimationType.EASE_OUT.value)
            animation.start()
            widget._fade_in_animation = animation  # Mantener referencia
            return animation
        if delay > 0:
            QTimer.singleShot(delay, start_animation)
            return None  # No se puede devolver la animación directamente si hay delay
        else:
            return start_animation()
    
    @staticmethod
    def fade_out(widget: QWidget, duration: int = 300) -> QPropertyAnimation:
        """Animación de desaparición gradual"""
        effect = widget.graphicsEffect() or QGraphicsOpacityEffect()
        if not widget.graphicsEffect():
            widget.setGraphicsEffect(effect)
        
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(AnimationType.EASE_IN.value)
        animation.start()
        
        return animation
    
    @staticmethod
    def slide_in(widget: QWidget, direction: str = "up", duration: int = 300) -> QPropertyAnimation:
        """Animación de deslizamiento"""
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setEasingCurve(AnimationType.EASE_OUT.value)
        
        current_pos = widget.pos()
        
        if direction == "up":
            start_pos = current_pos + widget.rect().bottomLeft()
        elif direction == "down":
            start_pos = current_pos - widget.rect().topLeft()
        elif direction == "left":
            start_pos = current_pos + widget.rect().topRight()
        else:  # right
            start_pos = current_pos - widget.rect().topLeft()
        
        animation.setStartValue(start_pos)
        animation.setEndValue(current_pos)
        animation.start()
        
        return animation
    
    @staticmethod
    def scale_animation(widget: QWidget, scale_factor: float = 1.1, duration: int = 200) -> QPropertyAnimation:
        """Animación de escalado"""
        # PyQt6 no tiene scale directo, usar resize como alternativa
        animation = QPropertyAnimation(widget, b"size")
        animation.setDuration(duration)
        animation.setEasingCurve(AnimationType.EASE_OUT.value)
        
        current_size = widget.size()
        scaled_size = current_size * scale_factor
        
        animation.setStartValue(current_size)
        animation.setEndValue(scaled_size)
        animation.start()
        
        return animation
    
    @staticmethod
    def add_drop_shadow(widget: QWidget, color: QColor = None, blur_radius: int = 10, 
                        offset: tuple = (0, 2)) -> QGraphicsDropShadowEffect:
        """Agrega un efecto de sombra a cualquier widget"""
        if color is None:
            color = QColor(0, 0, 0, 50)
            
        shadow_effect = QGraphicsDropShadowEffect(widget)
        shadow_effect.setBlurRadius(blur_radius)
        shadow_effect.setColor(color)
        shadow_effect.setOffset(offset[0], offset[1])
        
        # Preservar efectos previos si existen
        prev_effect = widget.graphicsEffect()
        if prev_effect and isinstance(prev_effect, QGraphicsOpacityEffect):
            # No podemos combinar efectos directamente en PyQt6, pero guardamos referencia
            widget._opacity_effect = prev_effect
            
        widget.setGraphicsEffect(shadow_effect)
        return shadow_effect
    
    @staticmethod
    def add_hover_effect(widget: QWidget, scale: float = 1.05, duration: int = 120):
        """Agrega efecto de hover (escala) al widget evitando acumulación de escalado y usando la geometría real en el primer hover"""
        def enterEvent(event, w=widget):
            original_event = getattr(w.__class__, 'enterEvent', None)
            if original_event:
                original_event(w, event)
            # Guardar la geometría original solo en el primer hover
            if not hasattr(w, '_original_geometry'):
                w._original_geometry = w.geometry()
            rect = w._original_geometry
            width_diff = int(rect.width() * scale) - rect.width()
            height_diff = int(rect.height() * scale) - rect.height()
            anim = QPropertyAnimation(w, b"geometry")
            anim.setDuration(duration)
            anim.setStartValue(rect)
            anim.setEndValue(rect.adjusted(-width_diff//2, -height_diff//2, width_diff//2, height_diff//2))
            anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            anim.start()
            w._hover_anim = anim

        def leaveEvent(event, w=widget):
            original_event = getattr(w.__class__, 'leaveEvent', None)
            if original_event:
                original_event(w, event)
            if hasattr(w, '_hover_anim') and w._hover_anim.state() == QPropertyAnimation.State.Running:
                w._hover_anim.stop()
            if hasattr(w, '_original_geometry'):
                original_rect = w._original_geometry
            else:
                original_rect = w.geometry()
            rect = w.geometry()
            anim = QPropertyAnimation(w, b"geometry")
            anim.setDuration(duration)
            anim.setStartValue(rect)
            anim.setEndValue(original_rect)
            anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            anim.start()
            w._hover_anim = anim

        widget.enterEvent = enterEvent
        widget.leaveEvent = leaveEvent
        return widget
    
    @staticmethod
    def add_click_effect(widget: QWidget, opacity_min: float = 0.7, duration: int = 120):
        """Agrega efecto de clic (opacidad) al widget, robusto ante borrado del QGraphicsOpacityEffect."""
        def ensure_opacity_effect(w):
            effect = getattr(w, '_opacity_effect', None)
            if not effect or not isinstance(effect, QGraphicsOpacityEffect) or effect.parent() is None:
                effect = QGraphicsOpacityEffect(w)
                effect.setOpacity(1.0)
                w.setGraphicsEffect(effect)
                w._opacity_effect = effect
            return effect

        def mousePressEvent(event, w=widget):
            effect = ensure_opacity_effect(w)
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(duration)
            anim.setStartValue(1.0)
            anim.setEndValue(opacity_min)
            anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            anim.start()
            w._click_anim = anim
            if hasattr(w, 'mousePressEvent_orig'):
                w.mousePressEvent_orig(event)

        def mouseReleaseEvent(event, w=widget):
            effect = ensure_opacity_effect(w)
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(duration)
            anim.setStartValue(opacity_min)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            anim.start()
            w._click_anim = anim
            if hasattr(w, 'mouseReleaseEvent_orig'):
                w.mouseReleaseEvent_orig(event)

        # Guardar originales si no existen
        if not hasattr(widget, 'mousePressEvent_orig'):
            widget.mousePressEvent_orig = getattr(widget, 'mousePressEvent', lambda e: None)
        if not hasattr(widget, 'mouseReleaseEvent_orig'):
            widget.mouseReleaseEvent_orig = getattr(widget, 'mouseReleaseEvent', lambda e: None)
        widget.mousePressEvent = mousePressEvent
        widget.mouseReleaseEvent = mouseReleaseEvent
        return widget
    
    @staticmethod
    def add_glow_on_hover(widget: QWidget, color: QColor = None, blur_radius: int = 24, duration: int = 180):
        """Agrega un efecto de glow animado al hacer hover sobre el widget."""
        if color is None:
            color = QColor(99, 102, 241, 120)
        # Asegura que el widget tenga un efecto de sombra
        effect = widget.graphicsEffect()
        if not effect or not isinstance(effect, QGraphicsDropShadowEffect):
            effect = QGraphicsDropShadowEffect(widget)
            effect.setBlurRadius(10)
            effect.setColor(QColor(0, 0, 0, 50))
            effect.setOffset(0, 2)
            widget.setGraphicsEffect(effect)
        widget._glow_effect = effect
        # Animaciones
        def enterEvent(event, w=widget):
            anim = QPropertyAnimation(w._glow_effect, b"blurRadius")
            anim.setDuration(duration)
            anim.setStartValue(w._glow_effect.blurRadius())
            anim.setEndValue(blur_radius)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            w._glow_anim = anim
            w._glow_effect.setColor(color)
            if hasattr(w, 'enterEvent_orig'):
                w.enterEvent_orig(event)
        def leaveEvent(event, w=widget):
            anim = QPropertyAnimation(w._glow_effect, b"blurRadius")
            anim.setDuration(duration)
            anim.setStartValue(w._glow_effect.blurRadius())
            anim.setEndValue(10)
            anim.setEasingCurve(QEasingCurve.Type.InCubic)
            anim.start()
            w._glow_anim = anim
            w._glow_effect.setColor(QColor(0, 0, 0, 50))
            if hasattr(w, 'leaveEvent_orig'):
                w.leaveEvent_orig(event)
        # Guardar originales si no existen
        if not hasattr(widget, 'enterEvent_orig'):
            widget.enterEvent_orig = getattr(widget, 'enterEvent', lambda e: None)
        if not hasattr(widget, 'leaveEvent_orig'):
            widget.leaveEvent_orig = getattr(widget, 'leaveEvent', lambda e: None)
        widget.enterEvent = enterEvent
        widget.leaveEvent = leaveEvent
        return widget

    @staticmethod
    def add_bounce_on_click(widget: QWidget, scale: float = 0.92, duration: int = 90):
        """Agrega un pequeño rebote al hacer clic en el widget."""
        def mousePressEvent(event, w=widget):
            if not hasattr(w, '_original_geometry'):
                w._original_geometry = w.geometry()
            rect = w._original_geometry
            width_diff = int(rect.width() * scale) - rect.width()
            height_diff = int(rect.height() * scale) - rect.height()
            anim = QPropertyAnimation(w, b"geometry")
            anim.setDuration(duration)
            anim.setStartValue(rect)
            anim.setEndValue(rect.adjusted(-width_diff//2, -height_diff//2, width_diff//2, height_diff//2))
            anim.setEasingCurve(QEasingCurve.Type.InCubic)
            anim.start()
            w._bounce_anim = anim
            if hasattr(w, 'mousePressEvent_orig'):
                w.mousePressEvent_orig(event)
        def mouseReleaseEvent(event, w=widget):
            if hasattr(w, '_original_geometry'):
                rect = w.geometry()
                original_rect = w._original_geometry
                anim = QPropertyAnimation(w, b"geometry")
                anim.setDuration(duration)
                anim.setStartValue(rect)
                anim.setEndValue(original_rect)
                anim.setEasingCurve(QEasingCurve.Type.OutBounce)
                anim.start()
                w._bounce_anim = anim
            if hasattr(w, 'mouseReleaseEvent_orig'):
                w.mouseReleaseEvent_orig(event)
        # Guardar originales si no existen
        if not hasattr(widget, 'mousePressEvent_orig'):
            widget.mousePressEvent_orig = getattr(widget, 'mousePressEvent', lambda e: None)
        if not hasattr(widget, 'mouseReleaseEvent_orig'):
            widget.mouseReleaseEvent_orig = getattr(widget, 'mouseReleaseEvent', lambda e: None)
        widget.mousePressEvent = mousePressEvent
        widget.mouseReleaseEvent = mouseReleaseEvent
        return widget

