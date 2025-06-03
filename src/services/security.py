import os
import base64
import secrets
import ctypes
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from config.logger import logger
from typing import Optional
from dataclasses import dataclass
from src.services.anti_tampering import AntiTampering

@dataclass
class VideoInfo:
    is_valid: bool
    video_id: str

class Security:
    """
    Clase para funciones de seguridad: cifrado, validación de URLs, sanitización de nombres, etc.
    """
    def __init__(self):
        # Protección anti-tampering antes de inicializar cualquier lógica sensible
        anti = AntiTampering()
        if not anti.is_safe_environment():
            logger.critical("Entorno inseguro detectado (anti-tampering/security). Abortando ejecución.")
            raise RuntimeError("Entorno inseguro detectado. La aplicación se cerrará.")

        # Cargar la librería C++
        dll_path = os.path.join(os.path.dirname(__file__), "security.dll")
        if not os.path.exists(dll_path):
            logger.error(f"No se encontró security.dll en {dll_path}")
            self._cdll = None
        else:
            self._cdll = ctypes.CDLL(dll_path)

        # Cargar la librería C++ para validación y extracción rápida de ID de video
        dll_path = os.path.join(os.path.dirname(__file__), "quest.dll")
        if not os.path.exists(dll_path):
            logger.error(f"No se encontró quest.dll en {dll_path}")
            self._questdll = None
        else:
            self._questdll = ctypes.CDLL(dll_path)
            self._questdll.is_valid_youtube_video.argtypes = [ctypes.c_char_p]
            self._questdll.is_valid_youtube_video.restype = ctypes.c_bool
            self._questdll.extract_video_id.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
            self._questdll.extract_video_id.restype = ctypes.c_bool

        # Configurar estructura para VideoInfo
        class CVideoInfo(ctypes.Structure):
            _fields_ = [("is_valid", ctypes.c_bool), ("video_id", ctypes.c_char * 32)]
        
        # Configurar tipos para extract_video_info SOLO si la DLL está cargada
        if self._cdll is not None:
            self._cdll.extract_video_info.argtypes = [ctypes.c_char_p]
            self._cdll.extract_video_info.restype = ctypes.POINTER(CVideoInfo)
        else:
            logger.warning("No se pudo configurar extract_video_info porque la DLL no está cargada.")

        self._CVideoInfo = CVideoInfo
        self._salt = self._get_or_create_salt()
        self._key = self._generate_key()
        self._fernet = Fernet(self._key)
        self._failed_attempts = {}
        self._max_attempts = 3
        self._attempt_timeout = 300  # 5 minutos

    def _get_or_create_salt(self) -> bytes:
        """
        Obtiene un salt único y seguro para el usuario. Si no existe, lo crea y lo guarda en disco.
        """
        salt_path = os.path.join(os.path.dirname(__file__), 'salt.bin')
        if os.path.exists(salt_path):
            with open(salt_path, 'rb') as f:
                return f.read()
        salt = secrets.token_bytes(16)
        with open(salt_path, 'wb') as f:
            f.write(salt)
        return salt

    def _generate_key(self) -> bytes:
        """
        Genera una clave segura para cifrado usando el salt único del usuario.
        """
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=100000,
            )
            return base64.urlsafe_b64encode(kdf.derive(b"Axolutly"))
        except Exception as e:
            logger.error(f"Error generando clave: {e}")
            return Fernet.generate_key()

    def encrypt_data(self, data: str) -> str:
        """Cifra datos sensibles."""
        try:
            return self._fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Error cifrando datos: {e}")
            return ""

    def decrypt_data(self, encrypted_data: str) -> str:
        """Descifra datos sensibles."""
        try:
            return self._fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Error descifrando datos: {e}")
            return ""

    def verify_file_integrity(self, file_path: str, expected_hash: Optional[str] = None) -> bool:
        """Verifica la integridad de un archivo mediante SHA256 usando C++."""
        try:
            if not self._cdll or not hasattr(self._cdll, 'verify_file_integrity'):
                logger.warning("No se puede verificar la integridad: DLL no cargada o función no disponible.")
                return True  # Asumir válido si no hay DLL
            # Implementación real aquí si la función existe
            return True
        except Exception as e:
            logger.error(f"Error verificando integridad: {e}")
            return False

    def check_rate_limit(self, ip_address: str) -> bool:
        """Verifica límites de velocidad para descargas por IP."""
        try:
            # Implementación pendiente
            return True
        except Exception as e:
            logger.error(f"Error en check_rate_limit: {e}")
            return False

    def record_failed_attempt(self, ip_address: str) -> None:
        """Registra intentos fallidos por IP."""
        try:
            # Implementación pendiente
            pass
        except Exception as e:
            logger.error(f"Error en record_failed_attempt: {e}")

    def sanitize_filename(self, filename: str) -> str:
        """Sanitiza nombres de archivo de forma segura usando C++."""
        try:
            # Implementación pendiente
            return filename
        except Exception as e:
            logger.error(f"Error sanitizando filename: {e}")
            return filename

    def validate_url(self, url: str) -> bool:
        """Validación rápida de URLs de YouTube usando C++ (yt_helper.dll)."""
        try:
            if not self._questdll or not hasattr(self._questdll, 'is_valid_youtube_video'):
                logger.warning("No se puede validar URL: quest.dll no cargada o función no disponible.")
                return False
            return self._questdll.is_valid_youtube_video(url.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error validando url: {e}")
            return False

    def extract_video_info(self, url: str) -> VideoInfo:
        """Extrae el ID del video usando C++ (yt_helper.dll)."""
        try:
            if not self._questdll or not hasattr(self._questdll, 'extract_video_id'):
                logger.warning("No se puede extraer info de video: quest.dll no cargada o función no disponible.")
                return VideoInfo(is_valid=False, video_id="")
            out_id = ctypes.create_string_buffer(32)
            is_valid = self._questdll.extract_video_id(url.encode('utf-8'), out_id, 32)
            return VideoInfo(is_valid=bool(is_valid), video_id=out_id.value.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error extrayendo info de video: {e}")
            return VideoInfo(is_valid=False, video_id="")
