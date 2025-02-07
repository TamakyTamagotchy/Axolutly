import re
import os
import subprocess
import sys
from urllib.parse import urlparse, unquote
from pathlib import Path
from config.logger import logger

class Utils:
    @staticmethod
    def validate_youtube_url(url):
        """Valida URLs de YouTube con múltiples formatos y límite de caracteres"""
        try:
            if len(url) > 110:
                return False
                
            cleaned_url = Utils.sanitize_url(url)
            parsed = urlparse(cleaned_url)
            
            # Dominios permitidos
            allowed_domains = {
                'youtube.com',
                'www.youtube.com',
                'm.youtube.com',
                'youtu.be',
                'music.youtube.com',
                'shorts.youtube.com'
            }
            
            if parsed.netloc.lower() not in allowed_domains:
                return False
                
            # Patrón mejorado para múltiples formatos
            youtube_pattern = r'^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|shorts\/|&v=)([^#&?]{11}).*'
            match = re.match(youtube_pattern, cleaned_url)
            
            # Verificar si el ID del video es válido (11 caracteres)
            return bool(match) and len(match.group(2)) == 11
            
        except Exception as e:
            logger.error(f"Error validando URL: {str(e)}")
            return False

    @staticmethod
    def sanitize_url(url):
        """Sanitiza una URL eliminando caracteres peligrosos."""
        # Eliminar espacios y caracteres no permitidos
        sanitized = ''.join(c for c in url.strip() if c.isprintable())
        return unquote(sanitized)
    
    @staticmethod
    def sanitize_filepath(filepath):
        """Sanitiza rutas manteniendo la estructura de directorios"""
        try:
            # Preservar barras en la ruta
            cleaned = re.sub(r'[<>"|?*\x00-\x1F]', '', filepath)  # No eliminar '/' ni '\'
            
            # Decodificar URL encoding conservando la estructura
            decoded = unquote(cleaned)
            
            # Normalización avanzada de rutas
            normalized = os.path.normpath(decoded)
            
            # Resolver rutas sin verificar existencia
            resolved = str(Path(normalized).resolve(strict=False))
            
            # Limitar longitud y mantener codificación
            max_length = 260 if sys.platform == "win32" else 4096
            return resolved[:max_length]
            
        except Exception as e:
            logger.error(f"Error sanitizando ruta: {str(e)}")
            return None
        
    @staticmethod
    def safe_open_file(file_path):
        """Abre archivos de forma segura con protección contra inyecciones y path traversal"""
        try:
            # Validación de seguridad preliminar
            if not Utils.is_safe_path(file_path):
                logger.warning(f"Intento de acceso a ruta no permitida: {file_path}")
                return False

            # Sanitización y normalización
            safe_path = Utils.sanitize_filepath(file_path)
            if not safe_path or not os.path.exists(safe_path):
                logger.warning(f"Ruta no existe o no válida: {safe_path}")
                return False

            # Ejecución segura por sistema operativo
            if sys.platform == "win32":
                # Método seguro para Windows sin shell=True
                args = [
                    'cmd', '/c', 'start', '',
                    'explorer', '/select,', 
                    os.path.normpath(safe_path)
                ]
                subprocess.run(
                    args,
                    check=True,
                    shell=False,
                    timeout=30,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
            elif sys.platform == "darwin":
                subprocess.run(
                    ["open", "-R", safe_path],
                    check=True,
                    shell=False,
                    timeout=30
                )
            else:
                subprocess.run(
                    ["xdg-open", os.path.dirname(safe_path)],
                    check=True,
                    shell=False,
                    timeout=30
                )
            
            logger.info(f"Archivo abierto exitosamente: {safe_path}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Error en subproceso: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error general abriendo archivo: {str(e)}")
            return False
        
    @staticmethod
    def is_safe_path(path):
        """Verifica que la ruta no esté en directorios sensibles del sistema"""
        system_dirs = {
            'win32': [
                os.path.abspath('C:\\Windows'),
                os.path.abspath('C:\\Program Files'),
                os.path.abspath('C:\\Program Files (x86)'),
                os.path.abspath('C:\\System Volume Information'),
                os.path.abspath('C:\\$Recycle.Bin')
            ],
            'linux': [
                '/bin',
                '/etc',
                '/root',
                '/sbin',
                '/var',
                '/usr/lib',
                '/sys',
                '/proc'
            ],
            'darwin': [
                '/System',
                '/Library',
                '/private',
                '/sbin',
                '/usr/lib',
                '/var'
            ]
        }
        """Verifica que la ruta no esté en directorios sensibles del sistema"""
        try:
            # Normalización case-insensitive solo para Windows
            abs_path = os.path.abspath(path)
            normalized = os.path.normpath(abs_path)
            if sys.platform == "win32":
                normalized = normalized.lower()

            forbidden_dirs = [os.path.normpath(d).lower() if sys.platform == "win32" 
                            else os.path.normpath(d) 
                            for d in system_dirs.get(sys.platform, [])]

            for forbidden in forbidden_dirs:
                if normalized.startswith(forbidden):
                    logger.warning(f"Intento de acceso a directorio prohibido: {normalized}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validando ruta: {str(e)}")
            return False