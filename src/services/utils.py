import re
import os
import subprocess
import sys
from urllib.parse import urlparse, unquote
from config.logger import logger
from yt_dlp.utils import sanitize_path
from typing import Optional
import ctypes

class Utils:
    """
    Utilidades generales para validación, sanitización y manejo seguro de rutas y URLs.
    """
    # Variable de clase para cachear si la DLL existe y su instancia
    _security_dll_checked = False
    _security_dll_exists = False
    _security_dll = None

    @staticmethod
    def validate_youtube_url(url: str) -> bool:
        """Valida si una URL corresponde a un video, short, live, playlist o cualquier recurso válido de YouTube."""
        try:
            parsed = urlparse(url)
            # Aceptar todos los subdominios de youtube.com y youtu.be
            valid_domains = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be'}
            if not any(parsed.netloc.lower().endswith(domain) for domain in valid_domains):
                logger.debug(f"Dominio no válido: {parsed.netloc}")
                return False
            # Solo requiere que tenga algún parámetro relevante o path
            if parsed.path.startswith(('/watch', '/shorts', '/live', '/playlist')) or parsed.netloc == 'youtu.be':
                return True
            # También aceptar URLs con parámetro v= o list= en la query
            if 'v=' in url or 'list=' in url:
                return True
            return False
        except Exception as e:
            logger.exception(f"Error validando URL: {e}")
            return False

    @staticmethod
    def validate_twitch_url(url: str) -> bool:
        """Valida si una URL corresponde a un canal, directo o VOD de Twitch."""
        try:
            parsed = urlparse(url)
            if parsed.netloc.lower() not in {'twitch.tv', 'www.twitch.tv'}:
                logger.debug(f"Dominio no válido para Twitch: {parsed.netloc}")
                return False
            # Ejemplo de URLs válidas:
            # https://www.twitch.tv/videos/123456789
            # https://www.twitch.tv/nombre_canal/clip/clipid
            twitch_patterns = [
                r'twitch\.tv\/videos\/\d+',  # VOD
                r'twitch\.tv\/[\w\-]+\/clip\/[\w\-]+'  # Clip
            ]
            for pattern in twitch_patterns:
                if re.search(pattern, url):
                    logger.debug(f"URL válida de Twitch: {url}")
                    return True
            logger.debug(f"URL de Twitch no coincide con ningún patrón válido: {url}")
            return False
        except Exception as e:
            logger.exception(f"Error validando URL de Twitch: {e}")
            return False

    @staticmethod
    def validate_tiktok_url(url: str) -> bool:
        """Valida si una URL corresponde a un video de TikTok."""
        try:
            parsed = urlparse(url)
            if parsed.netloc.lower() not in {'tiktok.com', 'www.tiktok.com', 'vm.tiktok.com'}:
                logger.debug(f"Dominio no válido para TikTok: {parsed.netloc}")
                return False
            # Ejemplo de URLs válidas:
            # https://www.tiktok.com/@usuario/video/1234567890123456789
            # https://vm.tiktok.com/xxxx/
            tiktok_patterns = [
                r'tiktok\.com/@[\w.-]+/video/\d+',
                r'vm\.tiktok\.com/\w+',
                r'tiktok\.com/t/\w+',
            ]
            for pattern in tiktok_patterns:
                if re.search(pattern, url):
                    logger.debug(f"URL válida de TikTok: {url}")
                    return True
            logger.debug(f"URL de TikTok no coincide con ningún patrón válido: {url}")
            return False
        except Exception as e:
            logger.exception(f"Error validando URL de TikTok: {e}")
            return False

    @staticmethod
    def validate_supported_url(url: str) -> bool:
        """Valida si la URL es de YouTube, Twitch o TikTok."""
        return (
            Utils.validate_youtube_url(url)
            or Utils.validate_twitch_url(url)
            or Utils.validate_tiktok_url(url)
        )

    @staticmethod
    def get_dll_path(dll_name: str) -> str:
        """Obtiene la ruta correcta de un DLL tanto en desarrollo como empaquetado."""
        if getattr(sys, 'frozen', False):
            # Empaquetado: buscar en la carpeta de la app (o subcarpetas)
            base_dir = os.path.dirname(sys.executable)
            dll_path = os.path.join(base_dir, 'lib', 'src', 'services', dll_name)
            if not os.path.exists(dll_path):
                # Alternativa: buscar en la raíz
                dll_path = os.path.join(base_dir, dll_name)
        else:
            # Desarrollo: buscar junto al archivo actual
            dll_path = os.path.join(os.path.dirname(__file__), dll_name)
        return dll_path

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitiza un nombre de archivo usando security.dll (C++). Si falla, usa sanitize_path de yt-dlp."""
        dll_path = Utils.get_dll_path("security.dll")
        # Solo comprobar una vez por ejecución
        if not Utils._security_dll_checked:
            Utils._security_dll_exists = os.path.exists(dll_path)
            if Utils._security_dll_exists:
                try:
                    Utils._security_dll = ctypes.CDLL(dll_path)
                    Utils._security_dll.sanitize_filename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
                    Utils._security_dll.sanitize_filename.restype = None
                except Exception as e:
                    logger.warning(f"No se pudo cargar security.dll: {e}. Usando método Python de respaldo.")
                    Utils._security_dll_exists = False
            else:
                logger.warning(f"No se encontró security.dll en {dll_path}. Usando método Python de respaldo.")
            Utils._security_dll_checked = True

        if Utils._security_dll_exists and Utils._security_dll:
            try:
                out = ctypes.create_string_buffer(256)
                Utils._security_dll.sanitize_filename(filename.encode('utf-8'), out, 256)
                sanitized = out.value.decode('utf-8').strip()
                if sanitized:
                    return sanitized
                else:
                    logger.warning(f"Sanitización con DLL falló, usando método Python de respaldo.")
            except Exception as e:
                logger.error(f"Error usando security.dll para sanitizar: {e}. Usando método Python de respaldo.")
        return sanitize_path(filename)

    @staticmethod
    def sanitize_url(url: str) -> str:
        """Elimina caracteres no imprimibles y decodifica la URL."""
        sanitized = ''.join(c for c in url.strip() if c.isprintable())
        return unquote(sanitized)
    
    @staticmethod
    def sanitize_filepath(filepath: str) -> Optional[str]:
        """Sanitiza una ruta de archivo usando sanitize_path."""
        try:
            return sanitize_path(filepath)
        except Exception as e:
            logger.error(f"Error sanitizando ruta con sanitize_path: {str(e)}")
            return None
        
    @staticmethod
    def safe_open_file(file_path: str) -> bool:
        """Abre un archivo de forma segura según el sistema operativo."""
        try:
            if not Utils.is_safe_path(file_path):
                logger.warning(f"Intento de acceso a ruta no permitida: {file_path}")
                return False
            safe_path = Utils.sanitize_filepath(file_path)
            if not safe_path or not os.path.exists(safe_path):
                logger.warning(f"Ruta no existe o no válida: {safe_path}")
                return False
            if sys.platform == "win32":
                os.startfile(safe_path)
            elif sys.platform == "darwin":
                subprocess.run(['open', safe_path], check=True)
            else:
                subprocess.run(['xdg-open', safe_path], check=True)
            return True
        except Exception as e:
            logger.exception(f"Error abriendo archivo: {str(e)}")
            return False
    
    @staticmethod
    def is_safe_path(path: str, allowed_dirs: Optional[list] = None) -> bool:
        """Valida que la ruta no apunte a directorios prohibidos."""
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
            if allowed_dirs:
                forbidden_dirs = [d for d in forbidden_dirs if d not in allowed_dirs]
            for forbidden in forbidden_dirs:
                if normalized.startswith(forbidden):
                    logger.warning(f"Intento de acceso a directorio prohibido: {normalized}")
                    return False
            return True
        except Exception as e:
            logger.exception(f"Error validando ruta: {str(e)}")
            return False
    
    @staticmethod
    def is_twitch_live_channel_url(url: str) -> bool:
        """Detecta si la URL es solo de canal en vivo de Twitch (no VOD, no clip)."""
        try:
            parsed = urlparse(url)
            if parsed.netloc.lower() not in {'twitch.tv', 'www.twitch.tv'}:
                return False
            # Solo canal: https://www.twitch.tv/usuario
            # No debe contener /videos/ ni /clip/
            path = parsed.path.strip('/').split('/')
            if len(path) == 1 and path[0] and path[0] not in ("videos", "directory", "p", "settings", "downloads", "friends"):
                return True
            return False
        except Exception:
            return False
