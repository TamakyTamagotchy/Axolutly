import os
import logging
from logging.handlers import RotatingFileHandler

class Config:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DIR_LOGS = os.path.join(BASE_DIR, "Registros")
    LOG_FILE = "Registro_Youtube.log"
    ERROR_LOG_FILE = "errores_youtube.log"
    DEBUG_LOG_FILE = "debug_youtube.log"
    ANIMATION_DURATION = 300
    ICON_DIR = os.path.join(BASE_DIR, "icons")
    ICON_YOUTUBE = "icono_youtube.png"
    ICON_DOWNLOAD = "icono_descarga.png"
    ICON_CANCEL = "icono_cancelar.png"
    ICON_FOLDER = "icono_carpeta.png"
    MAX_LOG_SIZE = 1024 * 1024  # 1MB
    NUM_LOG_BACKUPS = 3
    APP_MODE = "production"  # Cambiar a "development" para mayor verbosidad
    
def configure_logger():
    logger = logging.getLogger('YouTubeDownloader')
    logger.setLevel(logging.DEBUG if Config.APP_MODE == "development" else logging.INFO)
    
    # Asegurarse de que el directorio de logs existe
    os.makedirs(Config.DIR_LOGS, exist_ok=True)
    
    # Handler para todos los logs
    main_handler = RotatingFileHandler(
        os.path.join(Config.DIR_LOGS, Config.LOG_FILE),
        maxBytes=Config.MAX_LOG_SIZE,
        backupCount=Config.NUM_LOG_BACKUPS,
        encoding='utf-8'
    )
    main_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    main_handler.setLevel(logging.INFO)
    
    # Handler específico para errores
    error_handler = RotatingFileHandler(
        os.path.join(Config.DIR_LOGS, Config.ERROR_LOG_FILE),
        maxBytes=Config.MAX_LOG_SIZE,
        backupCount=Config.NUM_LOG_BACKUPS,
        encoding='utf-8'
    )
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(pathname)s:%(lineno)d\n'
        'Mensaje: %(message)s\n'
    ))
    error_handler.setLevel(logging.ERROR)
    
    # Handler para debug en modo desarrollo
    if Config.APP_MODE == "development":
        debug_handler = RotatingFileHandler(
            os.path.join(Config.DIR_LOGS, Config.DEBUG_LOG_FILE),
            maxBytes=Config.MAX_LOG_SIZE,
            backupCount=Config.NUM_LOG_BACKUPS,
            encoding='utf-8'
        )
        debug_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
        ))
        debug_handler.setLevel(logging.DEBUG)
        logger.addHandler(debug_handler)
    
    logger.addHandler(main_handler)
    logger.addHandler(error_handler)
    
    return logger

logger = configure_logger()
