import json
import os
from typing import Any, Optional
from config.logger import logger, Config

class Settings:
    """
    Singleton para la gestión de configuración de usuario.
    """
    _instance = None
    _defaults = {
        "theme": "light",
        "default_quality": "1080p",
        "download_dir": "",
        "audio_only": False,
        "browser_preference": ["brave", "chrome", "firefox", "edge"],
        "cookie_retention_days": 7,
        "download_retries": 3
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._load_settings()
        return cls._instance

    def _get_settings_path(self) -> str:
        return os.path.join(Config.BASE_DIR, "config", "user_settings.json")

    def _load_settings(self) -> None:
        self._settings = self._defaults.copy()
        try:
            if os.path.exists(self._get_settings_path()):
                with open(self._get_settings_path(), 'r', encoding='utf-8') as f:
                    stored_settings = json.load(f)
                    self._settings.update(stored_settings)
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")

    def save(self) -> bool:
        """Guarda la configuración actual. Devuelve True si tiene éxito."""
        try:
            os.makedirs(os.path.dirname(self._get_settings_path()), exist_ok=True)
            with open(self._get_settings_path(), 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4)
            logger.info("Configuración guardada exitosamente")
            return True
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")
            return False

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Obtiene un valor de configuración, usando el valor por defecto si no existe."""
        if key in self._settings:
            return self._settings[key]
        return self._defaults.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Establece un valor de configuración, validando el tipo si es posible."""
        if key in self._defaults and type(value) != type(self._defaults[key]):
            logger.warning(f"Tipo incorrecto para '{key}': esperado {type(self._defaults[key])}, recibido {type(value)}")
            return
        self._settings[key] = value
        self.save()
