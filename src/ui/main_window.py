"""
Ejemplo de uso de la interfaz principal de Axolutly (YouTubeDownloader)
Este archivo es solo demostrativo y no contiene la lógica interna del programa.
"""

from PyQt6.QtWidgets import QApplication
from src.ui.main_window import YouTubeDownloader
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = YouTubeDownloader()
    ventana.show()
    print("Ventana principal de Axolutly iniciada (solo ejemplo, sin lógica interna)")
    sys.exit(app.exec())
