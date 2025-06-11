import requests
import os
import zipfile
import shutil
import sys
import threading
import tempfile
import hashlib
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox, QApplication
from config.logger import logger, Config
from packaging import version as semver


version_axo = Config.VERSION

class YtDlpUpdateThread(threading.Thread):
    def __init__(self, parent_widget=None):
        super().__init__()
        self.parent_widget = parent_widget
        # Determine application root directory
        if getattr(sys, 'frozen', False):
            self.app_root = os.path.dirname(sys.executable)
        else:
            # two levels up from this file to project root
            self.app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

    def run(self):
        try:
            api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
            release = response.json()
            latest_version = release.get("tag_name", "")
            asset = next((a for a in release.get("assets", []) if a["name"] == "yt-dlp.zip"), None)
            if not asset:
                logger.error("No se encontró el archivo yt-dlp.zip en el release oficial.")
                if self.parent_widget:
                    QMessageBox.critical(self.parent_widget, "Error", "No se encontró yt-dlp.zip en el release oficial.")
                return
            download_url = asset["browser_download_url"]

            tmp = tempfile.mkdtemp()
            zip_path = os.path.join(tmp, asset["name"])
            logger.info(f"Descargando yt-dlp {latest_version} desde: {download_url}")
            with requests.get(download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            lib_dir = os.path.join(self.app_root, "lib")
            yt_dir = os.path.join(lib_dir, "yt-dlp")
            if os.path.exists(yt_dir): shutil.rmtree(yt_dir)
            os.makedirs(yt_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(yt_dir)
            logger.info(f"yt-dlp actualizado a {latest_version} en {yt_dir}.")
            if self.parent_widget:
                QMessageBox.information(self.parent_widget, "Actualización", f"yt-dlp {latest_version} actualizado. Reinicie la aplicación.")
        except Exception as e:
            logger.error(f"Error actualizando yt-dlp: {e}")
            if self.parent_widget:
                QMessageBox.critical(self.parent_widget, "Error", f"No se pudo actualizar yt-dlp: {e}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

class Updater:
    REPO_API = "https://api.github.com/repos/TamakyTamagotchy/Axolutly/releases/latest"

    @staticmethod
    def is_new_version_available(current_version=version_axo):
        try:
            response = requests.get(Updater.REPO_API, timeout=10)
            response.raise_for_status()
            release = response.json()
            tag = release.get("tag_name", current_version)
            # Remove leading 'v' if present
            tag_clean = tag.lstrip('v')
            curr_clean = current_version.lstrip('v')
            if semver.parse(tag_clean) > semver.parse(curr_clean):
                return True, release
            return False, release
        except Exception as e:
            logger.error(f"Error verificando actualizaciones: {e}")
            return False, None

    @staticmethod
    def download_and_apply_update(release, parent_widget=None):
        tmp_dir = None
        try:
            tag = release.get("tag_name", "")
            assets = release.get("assets", [])
            # Prefer full ZIP
            zip_asset = next((a for a in assets if a["name"].endswith('.zip')), None)
            if not zip_asset:
                logger.error("No se encontró ZIP de actualización.")
                if parent_widget:
                    QMessageBox.critical(parent_widget, "Error", "No se encontró ZIP de actualización.")
                return
            url = zip_asset["browser_download_url"]
            tmp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(tmp_dir, zip_asset["name"])

            logger.info(f"Descargando actualización {tag} desde {url}")
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(1024): f.write(chunk)

            # Optional SHA verification
            hash_asset = next((a for a in assets if a["name"].endswith('.sha256')), None)
            if hash_asset:
                h_resp = requests.get(hash_asset["browser_download_url"], timeout=10)
                h_resp.raise_for_status()
                expected = h_resp.text.strip().split()[0]
                sha = hashlib.sha256()
                with open(zip_path, 'rb') as f:
                    for c in iter(lambda: f.read(4096), b""): sha.update(c)
                if sha.hexdigest() != expected:
                    logger.error("SHA256 mismatch.")
                    if parent_widget:
                        QMessageBox.critical(parent_widget, "Error de integridad", "Verificación fallida.")
                    return

            # Apply update
            success = Updater._apply_update(zip_path)
            if not success:
                logger.error("Error aplicando la actualización. No se reemplazaron los archivos correctamente.")
                if parent_widget:
                    QMessageBox.critical(parent_widget, "Error", "No se pudo aplicar la actualización. Intente manualmente.")
                return
            if parent_widget:
                QMessageBox.information(parent_widget, "Actualización", "Actualización aplicada. Reiniciando.")
            logger.info("Reinicio de la aplicación.")
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            logger.error(f"Error en actualización: {e}")
            if parent_widget:
                QMessageBox.critical(parent_widget, "Error", f"No se pudo actualizar: {e}")
        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    @staticmethod
    def _apply_update(zip_path):
        try:
            # Determine app root
            if getattr(sys, 'frozen', False):
                app_root = os.path.dirname(sys.executable)
            else:
                app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

            extract_dir = os.path.join(tempfile.gettempdir(), f"axo_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Handle nested root folder
            entries = os.listdir(extract_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
                extract_base = os.path.join(extract_dir, entries[0])
            else:
                extract_base = extract_dir

            # Backup current state
            backup_dir = os.path.join(app_root, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            try:
                shutil.copytree(app_root, backup_dir, dirs_exist_ok=True)
                logger.info(f"Backup creado en {backup_dir}")
            except Exception as e:
                logger.warning(f"Error creando backup: {e}")

            # Override files
            for root, dirs, files in os.walk(extract_base):
                for file in files:
                    src = os.path.join(root, file)
                    rel = os.path.relpath(src, extract_base)
                    dst = os.path.join(app_root, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    try:
                        if os.path.exists(dst):
                            os.remove(dst)
                        shutil.move(src, dst)
                        logger.info(f"Reemplazado: {dst}")
                    except Exception as e:
                        logger.error(f"Error reemplazando {dst}: {e}")
                        return False

            # Cleanup
            shutil.rmtree(extract_dir, ignore_errors=True)
            if os.path.exists(zip_path):
                os.remove(zip_path)
            logger.info("Actualización aplicada con éxito.")
            return True
        except Exception as e:
            logger.error(f"Error aplicando actualización: {e}")
            return False

    @staticmethod
    def update_yt_dlp(parent_widget=None):
        """Actualiza la librería yt-dlp en lib/yt-dlp usando un hilo y la última versión oficial de GitHub."""
        try:
            thread = YtDlpUpdateThread(parent_widget)
            thread.start()
            if parent_widget:
                QMessageBox.information(parent_widget, "Actualización", "La actualización de yt-dlp se está realizando en segundo plano.\nRecibirá un mensaje al finalizar.")
        except Exception as e:
            logger.error(f"Error lanzando hilo de actualización de yt-dlp: {e}")
            if parent_widget:
                QMessageBox.critical(parent_widget, "Error", f"No se pudo iniciar la actualización de yt-dlp: {e}")