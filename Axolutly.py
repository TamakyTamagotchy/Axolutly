# main.py
import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.ui.main_window import YouTubeDownloader
from config.logger import logger

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
    # Para cx_Freeze, sys._MEIPASS puede no estar definido. Si existe se usa, sino se utiliza la ruta del ejecutable.
    if hasattr(sys, '_MEIPASS'):
        resource_path = os.path.join(sys._MEIPASS, "icons")
    else:
        resource_path = os.path.join(os.path.dirname(sys.executable), "icons")
    # Puedes usar resource_path para acceder a otros recursos si es necesario.

def excepthook(type, value, traceback):
    # Muestra un mensaje de error si ocurre una excepción no capturada
    logger.error("Excepción no capturada", exc_info=(type, value, traceback))
    QMessageBox.critical(None, "Error crítico", f"Ocurrió un error inesperado:\n{value}")
    sys.exit(1)

sys.excepthook = excepthook

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = YouTubeDownloader()
    ex.show()
    logger.info("Aplicación iniciada")
    sys.exit(app.exec())