import requests
import os
import zipfile
import shutil
import sys
import threading
import tempfile
import hashlib  # <--- Añadido para soporte de SHA256
from PyQt6.QtWidgets import QMessageBox, QApplication
from config.logger import logger

class YtDlpUpdateThread(threading.Thread):
    def __init__(self, parent_widget=None):
        super().__init__()
        self.parent_widget = parent_widget
        # Detectar la ruta absoluta del ejecutable actual (Axolutly)
        self.exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

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
            # Buscar la carpeta 'lib/yt-dlp' relativa al ejecutable actual
            base_dir = self.exe_dir
            lib_dir = os.path.join(base_dir, "lib")
            yt_dlp_dir = os.path.join(lib_dir, "yt-dlp")
            if os.path.exists(yt_dlp_dir):
                shutil.rmtree(yt_dlp_dir)
            os.makedirs(yt_dlp_dir, exist_ok=True)

            # Extraer el ZIP en la carpeta yt-dlp
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(yt_dlp_dir)
            logger.info(f"yt-dlp actualizado correctamente a {latest_version} en {yt_dlp_dir}.")

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
    def is_new_version_available(current_version="1.2.0"):
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
        """Descarga e instala la última versión de la aplicación con verificación de integridad, actualización atómica y descarga incremental avanzada."""
        try:
            latest_version = latest_release.get("tag_name")
            assets = latest_release.get("assets", [])
            manifest_asset = next((asset for asset in assets if asset["name"] == "manifest.json"), None)
            hash_asset = next((asset for asset in assets if asset["name"].endswith(".sha256")), None)

            if not manifest_asset:
                # Si no hay manifest, hacer actualización completa como fallback
                logger.warning("No se encontró manifest.json, usando actualización completa.")
                return Updater._download_and_apply_full_update(latest_release, parent_widget)

            # Descargar el manifest.json (debe contener lista de archivos y hashes SHA256)
            manifest_url = manifest_asset["browser_download_url"]
            manifest_response = requests.get(manifest_url, timeout=10)
            manifest_response.raise_for_status()
            manifest = manifest_response.json()

            # Recopilar archivos locales y sus hashes
            local_files = {}
            for root, dirs, files in os.walk(os.getcwd()):
                for file in files:
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, os.getcwd())
                    try:
                        sha256 = hashlib.sha256()
                        with open(path, "rb") as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                sha256.update(chunk)
                        local_files[rel_path.replace("\\", "/")] = sha256.hexdigest()
                    except Exception:
                        continue

            # Determinar archivos a descargar (nuevos o modificados)
            files_to_update = []
            for entry in manifest.get("files", []):
                rel_path = entry["path"]
                hash_remote = entry["sha256"]
                if rel_path not in local_files or local_files[rel_path] != hash_remote:
                    files_to_update.append(entry)

            if not files_to_update:
                if parent_widget:
                    QMessageBox.information(parent_widget, "Actualización", "Ya tienes la última versión. No hay archivos que actualizar.")
                logger.info("No hay archivos que actualizar.")
                return

            # Descargar y reemplazar solo los archivos necesarios
            temp_dir = tempfile.mkdtemp()
            for entry in files_to_update:
                file_url = entry["download_url"]
                rel_path = entry["path"]
                dest_path = os.path.join(temp_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                logger.info(f"Descargando archivo actualizado: {rel_path}")
                r = requests.get(file_url, stream=True, timeout=30)
                r.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                # Verificar hash
                sha256 = hashlib.sha256()
                with open(dest_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)
                if sha256.hexdigest() != entry["sha256"]:
                    logger.error(f"Hash SHA256 no coincide para {rel_path}. Se cancela la actualización.")
                    if parent_widget:
                        QMessageBox.critical(parent_widget, "Error de integridad", f"El archivo {rel_path} no pasó la verificación de integridad.")
                    shutil.rmtree(temp_dir)
                    return

            # Respaldo antes de reemplazar
            backup_dir = os.path.join(os.getcwd(), f"backup_{int(tempfile.mkstemp()[1][-6:])}")
            try:
                shutil.copytree(os.getcwd(), backup_dir, dirs_exist_ok=True)
            except Exception as e:
                logger.warning(f"No se pudo crear respaldo: {e}")

            # Reemplazar archivos
            for entry in files_to_update:
                rel_path = entry["path"]
                src = os.path.join(temp_dir, rel_path)
                dst = os.path.join(os.getcwd(), rel_path)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
                logger.info(f"Archivo actualizado: {dst}")

            shutil.rmtree(temp_dir)
            if parent_widget:
                QMessageBox.information(parent_widget, "Actualización", "Actualización incremental aplicada correctamente. El programa se reiniciará.")
            logger.info("Actualización incremental aplicada correctamente.")
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            logger.error(f"Error en actualización incremental: {e}")
            if parent_widget:
                QMessageBox.critical(parent_widget, "Error", f"No se pudo aplicar la actualización incremental: {e}")

    @staticmethod
    def _download_and_apply_full_update(latest_release, parent_widget=None):
        """Método auxiliar para actualización completa si no hay manifest.json."""
        try:
            latest_version = latest_release.get("tag_name")
            assets = latest_release.get("assets", [])
            zip_asset = next((asset for asset in assets if asset["name"].endswith(".zip")), None)
            hash_asset = next((asset for asset in assets if asset["name"].endswith(".sha256")), None)

            if not zip_asset:
                logger.error("No se encontró un archivo ZIP en los activos de la última versión.")
                if parent_widget:
                    QMessageBox.critical(parent_widget, "Error", "No se encontró el archivo ZIP de actualización.")
                return

            download_url = zip_asset["browser_download_url"]
            zip_path = os.path.join(os.getcwd(), f"update_{latest_version}.zip")

            # Descargar el archivo ZIP
            logger.info(f"Descargando actualización desde: {download_url}")
            if parent_widget:
                QMessageBox.information(parent_widget, "Actualización", "Descargando la nueva versión...")
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)

            # Verificar integridad SHA256 si hay hash publicado
            if hash_asset:
                hash_url = hash_asset["browser_download_url"]
                hash_response = requests.get(hash_url, timeout=10)
                hash_response.raise_for_status()
                expected_hash = hash_response.text.strip().split()[0]
                sha256 = hashlib.sha256()
                with open(zip_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)
                file_hash = sha256.hexdigest()
                if file_hash != expected_hash:
                    logger.error(f"Hash SHA256 no coincide: esperado {expected_hash}, obtenido {file_hash}")
                    if parent_widget:
                        QMessageBox.critical(parent_widget, "Error de integridad", "La verificación de integridad falló. La actualización fue cancelada.")
                    os.remove(zip_path)
                    return
                logger.info("Verificación de integridad SHA256 exitosa.")
            else:
                logger.warning("No se encontró archivo de hash SHA256 para la actualización. Se recomienda agregarlo en los releases.")

            # Actualización atómica
            Updater._apply_update(zip_path, parent_widget)

            QMessageBox.information(parent_widget, "Actualización", "La actualización se aplicó correctamente. El programa se reiniciará.")
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            logger.error(f"Error descargando actualización: {e}")
            if parent_widget:
                QMessageBox.critical(parent_widget, "Error", f"No se pudo descargar la actualización: {e}")

    @staticmethod
    def _apply_update(zip_path, parent_widget=None):
        try:
            extract_dir = os.path.join(os.getcwd(), "update_temp")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)

            # Extraer el contenido del ZIP en carpeta temporal
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Respaldo rápido antes de reemplazar
            backup_dir = os.path.join(os.getcwd(), f"backup_{int(tempfile.mkstemp()[1][-6:])}")
            try:
                shutil.copytree(os.getcwd(), backup_dir, dirs_exist_ok=True)
            except Exception as e:
                logger.warning(f"No se pudo crear respaldo: {e}")

            # Reemplazar archivos existentes con los nuevos (atómico)
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
            logger.info("Actualización aplicada exitosamente.")
        except Exception as e:
            logger.error(f"Error aplicando actualización: {e}")
            if os.path.exists(zip_path):
                os.remove(zip_path)
            if parent_widget:
                QMessageBox.critical(parent_widget, "Error", f"No se pudo aplicar la actualización: {e}")

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
