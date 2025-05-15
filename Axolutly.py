# main.py
import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.ui.main_window import YouTubeDownloader
from config.logger import logger

# Determinamos la ruta base dependiendo de si estamos congelados o no
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)

# Establecemos rutas absolutas para los recursos
resource_path = os.path.join(base_dir, "icons")
ffmpeg_bin_location = os.path.join(base_dir, "Ffmpeg", "bin")
if os.path.isdir(ffmpeg_bin_location):
    os.environ["FFMPEG_LOCATION"] = ffmpeg_bin_location
else:
    logger.warning("No se encontró la carpeta Ffmpeg/bin.")

def excepthook(type, value, traceback):
    logger.error(f"Excepción no capturada: {value}", exc_info=(type, value, traceback))
    QMessageBox.critical(None, "Error crítico", f"Ocurrió un error inesperado:\n{value}")
    sys.exit(1)

sys.excepthook = excepthook

if __name__ == "__main__": 
    app = QApplication(sys.argv)
    ex = YouTubeDownloader()
    ex.show()
    logger.info("Aplicación iniciada")
    sys.exit(app.exec())