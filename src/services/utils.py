import os
import subprocess
import sys
import re
import shlex
from urllib.parse import urlparse
from config.logger import logger

# Funciones utilitarias
class Utils:
    """Clase de funciones utilitarias, Validar url de youtube y abrir ultima ubicacion."""
    
    @staticmethod
    def validate_youtube_url(url):
        try:
            result = urlparse(url)
            if all([result.scheme, result.netloc]):
                # Expresión regular más estricta para validar URLs de YouTube
                youtube_regex = re.compile(
                    r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$',
                    re.IGNORECASE
                )
                return youtube_regex.match(url) is not None
        except ValueError:
            pass
        return False

    @staticmethod
    def open_last_download(file_path):
        if file_path and os.path.exists(file_path):
            try:
                if sys.platform == "win32":
                    subprocess.run(['explorer', '/select,', os.path.normpath(file_path)], check=True)
                elif sys.platform == "darwin":
                    subprocess.run(["open", "-R", shlex.quote(file_path)], check=True)
                else:
                    subprocess.run(["xdg-open", shlex.quote(os.path.dirname(file_path))], check=True)
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error al abrir la última descarga: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"Error inesperado al abrir la última descarga: {str(e)}")
                return False
        return False

