import re
import os
import subprocess
import sys
from urllib.parse import urlparse, unquote
from config.logger import logger
from yt_dlp.utils import sanitize_path

class Utils:
    @staticmethod
    def validate_youtube_url(url):
        try:
            parsed = urlparse(url)
            if parsed.netloc.lower() not in {'youtube.com', 'www.youtube.com', 'youtu.be'}:
                return False

            patterns = [
                r'(?:v=|\/)([-\w]{11})(?:\S+)?$',  # Video ID
                r'(?:\/shorts\/)([-\w]{11})$',    # Shorts
                r'(?:\/live\/)([-\w]{11})$',      # Live
                r'(?:list=)([-\w]+)$'             # Playlist
            ]
            return any(re.search(pattern, url) for pattern in patterns)
        except Exception as e:
            logger.error(f"Error validando URL: {e}")
            return False

    @staticmethod
    def sanitize_filename(filename):
        return sanitize_path(filename)

    @staticmethod
    def sanitize_url(url):
        sanitized = ''.join(c for c in url.strip() if c.isprintable())
        return unquote(sanitized)
    
    @staticmethod
    def sanitize_filepath(filepath):
        try:
            return sanitize_path(filepath)
        except Exception as e:
            logger.error(f"Error sanitizando ruta con sanitize_path: {str(e)}")
            return None
        
    @staticmethod
    def safe_open_file(file_path):
        try:
            if not Utils.is_safe_path(file_path):
                logger.warning(f"Intento de acceso a ruta no permitida: {file_path}")
                return False

            safe_path = Utils.sanitize_filepath(file_path)
            if not safe_path or not os.path.exists(safe_path):
                logger.warning(f"Ruta no existe o no válida: {safe_path}")
                return False

            # Usar métodos estándar para abrir archivos según el sistema operativo
            if sys.platform == "win32":
                os.startfile(safe_path)
            elif sys.platform == "darwin":
                subprocess.run(['open', safe_path], check=True)
            else:
                subprocess.run(['xdg-open', safe_path], check=True)

            return True
        except Exception as e:
            logger.error(f"Error abriendo archivo: {str(e)}")
            return False
        
    @staticmethod
    def is_safe_path(path):
        try:
            abs_path = os.path.abspath(path)
            normalized = os.path.normpath(abs_path)
            if sys.platform == "win32":
                normalized = normalized.lower()
            forbidden_dirs = [os.path.normpath(d).lower() if sys.platform == "win32" else os.path.normpath(d)
                            for d in {
                                'win32': [
                                    os.path.abspath('C:\\Windows'),
                                    os.path.abspath('C:\\Program Files'),
                                    os.path.abspath('C:\\Program Files (x86)'),
                                    os.path.abspath('C:\\System Volume Information'),
                                    os.path.abspath('C:\\$Recycle.Bin')
                                ],
                                'linux': [
                                    '/bin', '/etc', '/root', '/sbin', '/var', '/usr/lib', '/sys', '/proc'
                                ],
                                'darwin': [
                                    '/System', '/Library', '/private', '/sbin', '/usr/lib', '/var'
                                ]
                            }.get(sys.platform, [])]
            for forbidden in forbidden_dirs:
                if normalized.startswith(forbidden):
                    logger.warning(f"Intento de acceso a directorio prohibido: {normalized}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error validando ruta: {str(e)}")
            return False
