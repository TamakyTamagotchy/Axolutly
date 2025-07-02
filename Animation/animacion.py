"""
Ejemplo estructurado de uso de la barra de progreso animada (AnimatedProgressBar)
y utilidades de animación de widgets de Axolutly.
Este archivo es solo demostrativo y no contiene la lógica interna del programa.
"""

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from Animation.Animation import AnimatedProgressBar, AnimatedWidget
import sys

class DemoAnimacion(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo de Animación Axolutly")
        self.setGeometry(100, 100, 400, 200)
        layout = QVBoxLayout()
        self.progress = AnimatedProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        btn_pulse = QPushButton("Animar pulso")
        btn_pulse.clicked.connect(lambda: self.progress.pulse_animation())
        layout.addWidget(btn_pulse)

        btn_glow = QPushButton("Animar brillo")
        btn_glow.clicked.connect(lambda: self.progress.glow_effect())
        layout.addWidget(btn_glow)

        btn_shake = QPushButton("Animar sacudida")
        btn_shake.clicked.connect(lambda: self.progress.shake_animation())
        layout.addWidget(btn_shake)

        # Ejemplo de animación en un botón
        AnimatedWidget.add_hover_effect(btn_pulse)
        AnimatedWidget.add_click_effect(btn_glow)
        AnimatedWidget.add_bounce_on_click(btn_shake)

        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo = DemoAnimacion()
    demo.show()
    print("Demo de animaciones de barra de progreso y botones (solo ejemplo)")
    sys.exit(app.exec())
