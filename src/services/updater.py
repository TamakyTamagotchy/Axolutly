import requests
import os
import zipfile
import shutil
import sys
import threading
import tempfile
from PyQt6.QtWidgets import QMessageBox, QApplication
from config.logger import logger

class YtDlpUpdateThread(threading.Thread):
    def __init__(self, base_dir, parent_widget=None):
        super().__init__()
        self.base_dir = base_dir
        self.parent_widget = parent_widget

    def run(self):
        try:
            # Descargar la última versión de yt-dlp desde el repositorio oficial
            api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
            release = response.json()
            latest_version = release.get("tag_name", "")
            # Buscar el asset ZIP universal (yt-dlp.zip)
            asset = next((a for a in release.get("assets", []) if a["name"] == "yt-dlp.zip"), None)
            if not asset:
                logger.error("No se encontró el archivo yt-dlp.zip en el release oficial.")
                if self.parent_widget:
                    QMessageBox.critical(self.parent_widget, "Error", "No se encontró el archivo yt-dlp.zip en el release oficial.")
                return
            download_url = asset["browser_download_url"]

            # Descargar el ZIP temporalmente
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, asset["name"])
            logger.info(f"Descargando yt-dlp {latest_version} desde: {download_url}")
            with requests.get(download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # Eliminar la versión anterior
            yt_dlp_dir = os.path.join(self.base_dir, "lib", "yt-dlp")
            if os.path.exists(yt_dlp_dir):
                shutil.rmtree(yt_dlp_dir)
            os.makedirs(yt_dlp_dir, exist_ok=True)

            # Extraer el ZIP en la carpeta yt-dlp
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(yt_dlp_dir)
            logger.info(f"yt-dlp actualizado correctamente a {latest_version} en lib/yt-dlp.")

            if self.parent_widget:
                QMessageBox.information(self.parent_widget, "Actualización", f"yt-dlp {latest_version} se actualizó correctamente en segundo plano.\nReinicie la aplicación para usar la nueva versión.")
        except Exception as e:
            logger.error(f"Error actualizando yt-dlp en hilo: {e}")
            if self.parent_widget:
                QMessageBox.critical(self.parent_widget, "Error", f"No se pudo actualizar yt-dlp: {e}")

class Updater:
    REPO_URL = "https://api.github.com/repos/TamakyTamagotchy/Axolutly/releases/latest"
    DOWNLOAD_BASE_URL = "https://github.com/TamakyTamagotchy/Axolutly/releases/download"

    @staticmethod
    def is_new_version_available(current_version="1.1.5"):
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
        """Descarga e instala la última versión de la aplicación."""
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

            QMessageBox.information(parent_widget, "Actualización", "La actualización se aplicó correctamente.\nEl programa se reiniciará.")
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            logger.error(f"Error descargando actualización: {e}")
            if parent_widget:
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

    @staticmethod
    def update_yt_dlp(parent_widget=None):
        """Actualiza la librería yt-dlp en lib/yt-dlp usando un hilo y la última versión oficial de GitHub."""
        try:
            from config.logger import Config
            base_dir = Config.BASE_DIR
            thread = YtDlpUpdateThread(base_dir, parent_widget)
            thread.start()
            if parent_widget:
                QMessageBox.information(parent_widget, "Actualización", "La actualización de yt-dlp se está realizando en segundo plano.\nRecibirá un mensaje al finalizar.")
        except Exception as e:
            logger.error(f"Error lanzando hilo de actualización de yt-dlp: {e}")
            if parent_widget:
                QMessageBox.critical(parent_widget, "Error", f"No se pudo iniciar la actualización de yt-dlp: {e}")
