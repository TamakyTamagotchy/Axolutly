import json
import os
from config.logger import logger, Config

class Settings:
    _instance = None
    _defaults = {
        "theme": "light",
        "default_quality": "1080p",
        "download_dir": "",
        "audio_only": False,
        "browser_preference": ["brave", "chrome", "firefox", "edge"],  # <-- Brave primero
        "cookie_retention_days": 7,
        "download_retries": 3
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._load_settings()
        return cls._instance

    def _get_settings_path(self):
        return os.path.join(Config.BASE_DIR, "config", "user_settings.json")

    def _load_settings(self):
        self._settings = self._defaults.copy()
        try:
            if os.path.exists(self._get_settings_path()):
                with open(self._get_settings_path(), 'r', encoding='utf-8') as f:
                    stored_settings = json.load(f)
                    self._settings.update(stored_settings)
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")

    def save(self):
        try:
            os.makedirs(os.path.dirname(self._get_settings_path()), exist_ok=True)
            with open(self._get_settings_path(), 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4)
            logger.info("Configuración guardada exitosamente")
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value):
        self._settings[key] = value
        self.save()
