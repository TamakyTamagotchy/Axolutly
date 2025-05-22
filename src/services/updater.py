import requests
import os
import zipfile
from config.logger import logger

GITHUB_API_RELEASES = "https://api.github.com/repos/TamakyTamagotchy/Axolutly/releases/latest"
REPO_RELEASES_URL = "https://github.com/TamakyTamagotchy/Axolutly/releases/latest"
CURRENT_VERSION = "1.1.3"  # Debe coincidir con tu versión actual

class Updater:
    @staticmethod
    def get_latest_release_info():
        try:
            response = requests.get(GITHUB_API_RELEASES, timeout=10)
            if response.status_code == 200:
                return response.json()
            logger.error(f"Error consultando releases: {response.status_code}")
        except Exception as e:
            logger.error(f"Error consultando releases: {e}")
        return None

    @staticmethod
    def is_new_version_available():
        info = Updater.get_latest_release_info()
        if not info:
            return False, None
        latest_version = info.get("tag_name", "").lstrip("v")
        if Updater.compare_versions(latest_version, CURRENT_VERSION):
            return True, info
        return False, None

    @staticmethod
    def compare_versions(v1, v2):
        def normalize(v):
            return [int(x) for x in v.split(".") if x.isdigit()]
        return normalize(v1) > normalize(v2)

    @staticmethod
    def download_and_apply_update(info, parent_widget=None):
        assets = info.get("assets", [])
        # Busca un zip o el ejecutable principal
        asset = next((a for a in assets if a["name"].endswith(".zip")), None)
        if not asset:
            logger.error("No se encontró un archivo .zip en el release.")
            return False

        url = asset["browser_download_url"]
        local_zip = os.path.join(os.getcwd(), asset["name"])
        try:
            # Descargar el zip
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(local_zip, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            # Extraer y reemplazar archivos
            with zipfile.ZipFile(local_zip, "r") as zip_ref:
                for member in zip_ref.namelist():
                    # Solo reemplaza archivos existentes o nuevos en la carpeta principal
                    dest_path = os.path.join(os.getcwd(), member)
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    zip_ref.extract(member, os.getcwd())
            os.remove(local_zip)
            logger.info("Actualización aplicada correctamente.")
            if parent_widget:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(parent_widget, "Actualización", "¡Actualización completada! Reinicia la aplicación para aplicar los cambios.")
            return True
        except Exception as e:
            logger.error(f"Error aplicando actualización: {e}")
            if parent_widget:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(parent_widget, "Actualización", f"Error al actualizar: {e}")
            return False
