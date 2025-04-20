import os
import hashlib
import base64
import time
from urllib.parse import urlparse
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from config.logger import logger

class Security:
    def __init__(self):
        self._key = self._generate_key()
        self._fernet = Fernet(self._key)
        self._failed_attempts = {}
        self._max_attempts = 3
        self._attempt_timeout = 300  # 5 minutos

    def _generate_key(self):
        """Genera una clave segura para cifrado"""
        try:
            salt = b'YouTubeDownloaderSalt'  # Deberías generar un salt único y guardarlo
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(b"YTDSecretKey"))  # Usa una clave secreta real
            return key
        except Exception as e:
            logger.error(f"Error generando clave de cifrado: {e}")
            return None

    def encrypt_data(self, data: str) -> str:
        """Cifra datos sensibles"""
        try:
            return self._fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Error cifrando datos: {e}")
            return data

    def decrypt_data(self, encrypted_data: str) -> str:
        """Descifra datos sensibles"""
        try:
            return self._fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Error descifrando datos: {e}")
            return encrypted_data

    def verify_file_integrity(self, file_path: str, expected_hash: str = None) -> bool:
        """Verifica la integridad de un archivo"""
        try:
            if not os.path.exists(file_path):
                return False
            
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            calculated_hash = sha256_hash.hexdigest()
            
            if expected_hash:
                return calculated_hash == expected_hash
            return True
        except Exception as e:
            logger.error(f"Error verificando integridad del archivo: {e}")
            return False

    def check_rate_limit(self, ip_address: str) -> bool:
        """Verifica límites de velocidad para descargas"""
        try:
            current_time = time.time()
            if ip_address in self._failed_attempts:
                attempts, last_attempt = self._failed_attempts[ip_address]
                if current_time - last_attempt < self._attempt_timeout:
                    if attempts >= self._max_attempts:
                        return False
                else:
                    self._failed_attempts[ip_address] = (0, current_time)
            return True
        except Exception as e:
            logger.error(f"Error verificando rate limit: {e}")
            return True

    def record_failed_attempt(self, ip_address: str):
        """Registra intentos fallidos"""
        try:
            current_time = time.time()
            attempts, _ = self._failed_attempts.get(ip_address, (0, current_time))
            self._failed_attempts[ip_address] = (attempts + 1, current_time)
        except Exception as e:
            logger.error(f"Error registrando intento fallido: {e}")

    def sanitize_filename(self, filename: str) -> str:
        """Sanitiza nombres de archivo de forma segura"""
        try:
            # Eliminar caracteres peligrosos
            illegal_chars = '<>:"/\\|?*'
            for char in illegal_chars:
                filename = filename.replace(char, '')
            
            # Limitar longitud
            max_length = 255
            if len(filename) > max_length:
                name, ext = os.path.splitext(filename)
                filename = name[:max_length-len(ext)] + ext
            
            return filename.strip()
        except Exception as e:
            logger.error(f"Error sanitizando nombre de archivo: {e}")
            return "download"  # Nombre seguro por defecto

    def validate_url(self, url: str) -> bool:
        """Validación extendida de URLs"""
        try:
            parsed = urlparse(url)
            
            # Verificar esquema
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Verificar dominio
            if not parsed.netloc:
                return False
            
            # Verificar dominio de YouTube
            allowed_domains = {'youtube.com', 'www.youtube.com', 'youtu.be'}
            if parsed.netloc.lower() not in allowed_domains:
                return False
            
            # Verificar caracteres peligrosos
            dangerous_chars = '<>"\'%{}`'
            if any(char in url for char in dangerous_chars):
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validando URL: {e}")
            return False
