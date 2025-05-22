import os
import time
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition, QMutexLocker, pyqtSlot
from yt_dlp import YoutubeDL
from config.logger import logger
from src.services.gestor_cookies import GestorCookies
from src.services.security import Security

class DownloadThread(QThread):
    progress = pyqtSignal(float)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    video_info = pyqtSignal(dict)
    requestOverwritePermission = pyqtSignal(str)
    showAuthDialog = pyqtSignal()
    cancelled = pyqtSignal()  # señal

    def __init__(self, video_url, quality, audio_only, output_dir):
        super().__init__()
        self.video_url = video_url
        self.quality = quality
        self.audio_only = audio_only
        self.output_dir = output_dir
        self._cancelled = False  # <--- Cambiado de self.cancelled a self._cancelled
        self.final_filename = None
        self.temp_file = None
        self.overwrite_answer = None
        self.mutex = QMutex()
        self.waitCondition = QWaitCondition()
        self.last_progress_time = 0
        self._auth_completed = False
        self._driver = None
        self.cookie_manager = GestorCookies(self)
        self.security = Security()

    def set_auth_completed(self):
        """Maneja la completación de la autenticación"""
        self._auth_completed = True
        if self.cookie_manager:
            self.cookie_manager.set_auth_completed()
        logger.info("Autenticación completada en hilo de descarga")

    def run(self):
        try:
            # Validar URL antes de procesar
            if not self.security.validate_url(self.video_url):
                self.error.emit("URL no válida o potencialmente peligrosa")
                return

            opts = self.get_ydl_options()
            cookie_path = self.cookie_manager.get_cookie_path()
            if cookie_path:
                opts['cookiefile'] = cookie_path
                logger.info(f"Usando archivo de cookies: {cookie_path}")
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.video_url, download=False)
        except Exception as e:
            if "age" in str(e).lower() or "restricted" in str(e).lower():
                logger.info("Restricción de edad detectada. Solicitando autenticación...")
                # Solo aquí se llama a update_cookies (que puede usar Selenium)
                cookie_path = self.cookie_manager.update_cookies()
                opts = self.get_ydl_options()
                if cookie_path:
                    opts['cookiefile'] = cookie_path
                    logger.info(f"Usando archivo de cookies tras autenticación: {cookie_path}")
                try:
                    with YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(self.video_url, download=False)
                except Exception as e2:
                    logger.error(f"Error tras actualizar cookies: {e2}")
                    self.error.emit(f"Error tras actualizar cookies: {e2}")
                    return
            else:
                logger.error(f"Error extrayendo información: {e}")
                self.error.emit(f"Error extrayendo información: {e}")
                return

        temp_filename = ydl.prepare_filename(info)
        if os.path.exists(temp_filename) and not self.ask_overwrite_permission(temp_filename):
            self._cancelled = True  # <--- Cambiado
            self.cancelled.emit()
            return
        elif os.path.exists(temp_filename):
            os.remove(temp_filename)
        try:
            opts = self.get_ydl_options()
            cookie_path = self.cookie_manager.get_cookie_path()
            if cookie_path:
                opts['cookiefile'] = cookie_path
            with YoutubeDL(opts) as ydl:
                ydl.download([self.video_url])
        except Exception as e:
            if self._cancelled and "Descarga cancelada por el usuario" in str(e):  # <--- Cambiado
                self.cancelled.emit()
                return
            self.error.emit(f"Error en la descarga: {e}")
            return

        if self._cancelled:  # <--- Cambiado
            self.cleanup_temp_files()
            self.cancelled.emit()
            return

        final_path = self.final_filename or temp_filename
        if os.path.exists(temp_filename) and final_path != temp_filename:
            try:
                os.replace(temp_filename, final_path)
            except Exception as rename_error:
                logger.error(f"Error al renombrar el archivo: {rename_error}")
                self.error.emit("Error interno al procesar la descarga")
                return

        if self.audio_only and final_path.lower().endswith(".webm"):
            final_path = final_path[:-5] + ".mp3"

        self.finished.emit(final_path)
        logger.info(f"Descarga completada: {'solo audio' if self.audio_only else f'{self.quality}p'}")

    def cleanup_temp_files(self):
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
                logger.info(f"Archivo temporal eliminado: {self.temp_file}")
            except Exception as e:
                logger.error(f"Error al eliminar el archivo temporal {self.temp_file}: {str(e)}")

    def ask_overwrite_permission(self, file_path):
        exists, similar_files = self.cookie_manager.check_file_exists(file_path)
        if not exists:
            return True

        message = f"El archivo '{os.path.basename(file_path)}' ya existe."
        if similar_files:
            message += "\nAdemás, se encontraron archivos con contenido idéntico:\n"
            message += "\n".join(f"- {f}" for f in similar_files)
        
        self.requestOverwritePermission.emit(message)
        
        with QMutexLocker(self.mutex):
            waited = self.waitCondition.wait(self.mutex, 10000)
            if not waited or self.overwrite_answer is None:
                logger.warning("Timeout en confirmación de sobrescritura")
                return False
        return self.overwrite_answer

    @pyqtSlot(bool)
    def set_overwrite_answer(self, answer):
        with QMutexLocker(self.mutex):
            self.overwrite_answer = answer
            self.waitCondition.wakeAll()

    def cancel(self):
        self._cancelled = True  # <--- Cambiado
        if self._driver:
            try:
                self._driver.quit()
            except:
                pass
            self._driver = None
        self.quit()
            
    def get_ydl_options(self):
        opts = {
            'outtmpl': os.path.join(
                self.output_dir, 
                self.security.sanitize_filename('%(title)s.%(ext)s')
            ),
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
            'retries': 3,
            'http_headers': {
                'User-Agent': 'Axolutly v1.1.3',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            },
            'nocheckcertificate': False,
            'socket_timeout': 30,
            'restrict_filenames': True,
            'no_color': True,
            'geo_bypass': False,
            'no_warnings': True,
            'quiet': True,
            'extract_flat': "in_playlist",
            'source_address': '0.0.0.0'
        }
        if self.audio_only:
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }]
            })
        else:
            opts.update({
                'format': f'bestvideo[height<={self.quality}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
                'format_sort': ['height', 'vcodec:h264', 'filesize', 'ext'],
            })
        # Usar la variable de entorno FFMPEG_LOCATION si está disponible
        ffmpeg_base = os.environ.get("FFMPEG_LOCATION")
        if ffmpeg_base and os.path.isdir(ffmpeg_base):
            if os.name == "nt":
                ffmpeg_exe = os.path.join(ffmpeg_base, "ffmpeg.exe")
                ffprobe_exe = os.path.join(ffmpeg_base, "ffprobe.exe")
            else:
                ffmpeg_exe = os.path.join(ffmpeg_base, "ffmpeg")
                ffprobe_exe = os.path.join(ffmpeg_base, "ffprobe")
            if os.path.isfile(ffmpeg_exe) and os.path.isfile(ffprobe_exe):
                opts['ffmpeg_location'] = ffmpeg_base
            else:
                opts['ffmpeg_location'] = ffmpeg_exe
        else:
            opts['ffmpeg_location'] = ""

        return opts

    def progress_hook(self, d):
        now = time.time()
        if now - self.last_progress_time < 0.5:
            return
        self.last_progress_time = now
        if self._cancelled:  # <--- Cambiado
            raise Exception("Descarga cancelada por el usuario")
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                downloaded = d.get('downloaded_bytes', 0)
                percent = int(downloaded / total * 100)
                self.progress.emit(percent)
            else:
                try:
                    percent = float(d.get('_percent_str', '0%').strip().replace('%', ''))
                    self.progress.emit(int(percent))
                except ValueError:
                    pass
        elif d['status'] == 'finished':
            self.progress.emit(100)
            self.final_filename = d['info_dict']['_filename']
            logger.info(f"Archivo final: {self.final_filename}")
