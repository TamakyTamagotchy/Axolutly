import os
import sys
import logging
from logging.handlers import RotatingFileHandler

class Config:
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DIR_LOGS = os.path.join(BASE_DIR, "Registros")
    ERROR_LOG_FILE = "errores_youtube.log"
    ANIMATION_DURATION = 300
    ICON_DIR = os.path.join(BASE_DIR, "icons")
    ICON_YOUTUBE = "icono_youtube.png"
    ICON_DOWNLOAD = "icono_descarga.png"
    ICON_CANCEL = "icono_cancelar.png"
    ICON_FOLDER = "icono_carpeta.png"    
    MAX_LOG_SIZE = 1024 * 1024  # 1MB
    NUM_LOG_BACKUPS = 3
    APP_MODE = "production"
    
def configure_logger():
    logger = logging.getLogger('YouTubeDownloader')
    logger.setLevel(logging.DEBUG if Config.APP_MODE == "development" else logging.INFO)
    os.makedirs(Config.DIR_LOGS, exist_ok=True)
    error_handler = RotatingFileHandler(
        os.path.join(Config.DIR_LOGS, Config.ERROR_LOG_FILE),
        maxBytes=Config.MAX_LOG_SIZE,
        backupCount=Config.NUM_LOG_BACKUPS,
        encoding='utf-8'
    )
    # Solo nivel, línea y mensaje
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - Línea %(lineno)d\nMensaje: %(message)s\n'
    ))
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)
    return logger

logger = configure_logger()
