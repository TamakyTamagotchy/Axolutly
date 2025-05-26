import requests
import os
import zipfile
import shutil
from config.logger import logger

class Updater:
    REPO_URL = "https://api.github.com/repos/TamakyTamagotchy/Axolutly/releases/latest"
    DOWNLOAD_BASE_URL = "https://github.com/TamakyTamagotchy/Axolutly/releases/download"

    @staticmethod
    def is_new_version_available(current_version="1.1.3"):
        try:
            response = requests.get(Updater.REPO_URL, timeout=10)
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release.get("tag_name", current_version)
            return latest_version > current_version, latest_release
        except Exception as e:
            logger.error(f"Error verificando actualizaciones: {e}")
            return False, None

    @staticmethod
    def download_and_apply_update(latest_release, parent_widget=None):
        try:
            latest_version = latest_release.get("tag_name")
            assets = latest_release.get("assets", [])
            zip_asset = next((asset for asset in assets if asset["name"].endswith(".zip")), None)

            if not zip_asset:
                logger.error("No se encontró un archivo ZIP en los activos de la última versión.")
                return

            download_url = zip_asset["browser_download_url"]
            zip_path = os.path.join(os.getcwd(), f"update_{latest_version}.zip")

            # Descargar el archivo ZIP
            logger.info(f"Descargando actualización desde: {download_url}")
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)

            logger.info("Actualización descargada exitosamente.")
            Updater._apply_update(zip_path)
        except Exception as e:
            logger.error(f"Error descargando actualización: {e}")
            if parent_widget:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(parent_widget, "Error", "No se pudo descargar la actualización.")

    @staticmethod
    def _apply_update(zip_path):
        try:
            extract_dir = os.path.join(os.getcwd(), "update_temp")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)

            # Extraer el contenido del ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Reemplazar archivos existentes con los nuevos
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    src_file = os.path.join(root, file)
                    relative_path = os.path.relpath(src_file, extract_dir)
                    dest_file = os.path.join(os.getcwd(), relative_path)

                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.move(src_file, dest_file)
                    logger.info(f"Archivo reemplazado: {dest_file}")

            # Limpiar archivos temporales
            shutil.rmtree(extract_dir)
            os.remove(zip_path)
            logger.info("Actualización aplicada exitosamente. Reinicie la aplicación.")
        except Exception as e:
            logger.error(f"Error aplicando actualización: {e}")
            if os.path.exists(zip_path):
                os.remove(zip_path)