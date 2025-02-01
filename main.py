# main.py
import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import YouTubeDownloader
from config.logger import logger

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = YouTubeDownloader()
    ex.show()
    logger.info("Aplicación iniciada")
    sys.exit(app.exec())