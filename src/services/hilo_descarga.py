import os
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition, QMutexLocker, pyqtSlot
from PyQt6.QtWidgets import QMessageBox
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled
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
    cancelled = pyqtSignal()

    def __init__(self, video_url, quality, audio_only, output_dir):
        super().__init__()
        self.video_url = video_url
        self.quality = quality
        self.audio_only = audio_only
        self.output_dir = output_dir
        self._cancelled = False
        self._auth_cancelled = False
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
        self.current_video_index = 0
        self.total_videos = 0

    def set_auth_completed(self):
        """Maneja la completación de la autenticación"""
        self._auth_completed = True
        if self.cookie_manager:
            self.cookie_manager.set_auth_completed()
        logger.info("Autenticación completada en hilo de descarga")

    def is_twitch_url(self, url):
        """Detecta si la URL es de Twitch (stream o VOD)."""
        return any(domain in url for domain in ["twitch.tv", "www.twitch.tv"])

    def is_tiktok_url(self, url):
        """Detecta si la URL es de TikTok."""
        return any(domain in url for domain in ["tiktok.com", "www.tiktok.com", "vm.tiktok.com"])

    def get_ydl_options(self):
        # Soporte para Twitch
        if self.is_twitch_url(self.video_url):
            # Para streams en vivo y VODs de Twitch
            opts = {
                'outtmpl': os.path.join(
                    self.output_dir,
                    '%(title)s.%(ext)s'
                ),
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'extract_flat': False,
                'playlist': False
            }
            # Selección de calidad para Twitch
            # Si la calidad es "audio_only", descargar solo audio
            if self.audio_only:
                opts['format'] = 'bestaudio/best'
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                # Para Twitch, la calidad puede ser "best", "worst", "720p", "480p", etc.
                # Si la calidad es un número, usar ese valor, si no, usar "best"
                fmt = str(self.quality) if self.quality else 'best'
                opts['format'] = f'bestvideo[height<={fmt}]+bestaudio/best[height<={fmt}]/best[height<={fmt}]/best'
            # FFMPEG
            ffmpeg_base = os.environ.get("FFMPEG_LOCATION")
            if ffmpeg_base and os.path.isdir(ffmpeg_base):
                opts['ffmpeg_location'] = ffmpeg_base
            return opts

        # Soporte para TikTok
        if self.is_tiktok_url(self.video_url):
            opts = {
                'outtmpl': os.path.join(
                    self.output_dir,
                    '%(title)s.%(ext)s'
                ),
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'extract_flat': False,
                'playlist': False,
                'format': 'mp4/bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
            }
            # FFMPEG
            ffmpeg_base = os.environ.get("FFMPEG_LOCATION")
            if ffmpeg_base and os.path.isdir(ffmpeg_base):
                opts['ffmpeg_location'] = ffmpeg_base
            # Nombre personalizado: quitar # del título o usar video_axolutly
            opts['postprocessors'] = [{
                'key': 'FFmpegMetadata',
            }]
            opts['final_ext'] = 'mp4'
            opts['outtmpl'] = os.path.join(
                self.output_dir,
                '%(description)s.%(ext)s'
            )
            opts['postprocessor_hooks'] = [self.tiktok_filename_hook]
            return opts

        opts = {
            'outtmpl': os.path.join(
                self.output_dir,
                '%(title)s.%(ext)s'
            ),
            'progress_hooks': [self.progress_hook],
            'http_headers': {
                'User-Agent': 'yt-dlp',
                'Accept': '*/*',
                'Accept-Language': 'es-ES,es;q=0.9',
            },
            'format': f'bestvideo[height<={self.quality}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,  # Importante: esto evita que descargue la playlist completa
            'extract_flat': False,
            'playlist': False
        }

        if self.audio_only:
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            })

        # Configuración de FFMPEG_LOCATION si está disponible
        ffmpeg_base = os.environ.get("FFMPEG_LOCATION")
        if ffmpeg_base and os.path.isdir(ffmpeg_base):
            opts['ffmpeg_location'] = ffmpeg_base

        return opts

    def run(self):
        temp_cookie_path = None
        try:
            # Permitir cancelación ANTES de iniciar cualquier proceso
            if self._cancelled:
                self.cleanup_temp_files()
                self.cancelled.emit()
                return
            with YoutubeDL(self.get_ydl_options()) as ydl:
                # Extraer información del video antes de descargar
                info = ydl.extract_info(self.video_url, download=False)
                if self._cancelled:
                    self.cleanup_temp_files()
                    self.cancelled.emit()
                    return
        except Exception as e:
            if self._cancelled:
                self.cleanup_temp_files()
                self.cancelled.emit()
                return
            if "age" in str(e).lower() or "restricted" in str(e).lower():
                logger.info("Restricción de edad detectada. Solicitando autenticación...")
                cookie_path = self.cookie_manager.get_cookie_path()
                if not cookie_path:
                    cookie_path = self.cookie_manager.update_cookies()
                opts = self.get_ydl_options()
                if cookie_path:
                    import tempfile
                    temp_cookie = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.txt')
                    temp_cookie_path = temp_cookie.name
                    temp_cookie.close()
                    ok = self.cookie_manager._cookie_encryptor.decrypt_file(cookie_path.encode('utf-8'), temp_cookie_path.encode('utf-8'))
                    if not ok:
                        logger.error("Error descifrando archivo de cookies con DLL para yt-dlp.")
                        self.error.emit("Error descifrando archivo de cookies para autenticación.")
                        return
                    opts['cookiefile'] = temp_cookie_path
                    logger.info(f"Usando archivo de cookies temporal descifrado: {temp_cookie_path}")
                try:
                    with YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(self.video_url, download=False)
                        if self._cancelled:
                            self.cleanup_temp_files()
                            self.cancelled.emit()
                            return
                except Exception as e2:
                    logger.error(f"Error tras actualizar cookies: {e2}")
                    self.error.emit(f"Error tras actualizar cookies: {e2}")
                    if temp_cookie_path and os.path.exists(temp_cookie_path):
                        os.remove(temp_cookie_path)
                    return
                finally:
                    if temp_cookie_path and os.path.exists(temp_cookie_path):
                        os.remove(temp_cookie_path)
            else:
                logger.error(f"Error extrayendo información: {e}")
                self.error.emit(f"Error extrayendo información: {e}")
                return

        if self._cancelled:
            self.cleanup_temp_files()
            self.cancelled.emit()
            return

        temp_filename = ydl.prepare_filename(info)
        # Preguntar al usuario si desea sobrescribir el archivo si ya existe
        if os.path.exists(temp_filename):
            self.requestOverwritePermission.emit(os.path.basename(temp_filename))
            with QMutexLocker(self.mutex):
                waited = self.waitCondition.wait(self.mutex, 60000)
                if not waited or self.overwrite_answer is None:
                    logger.warning("Timeout en confirmación de sobrescritura")
                    self.error.emit("No se recibió respuesta para sobrescribir el archivo.")
                    return
                if not self.overwrite_answer:
                    logger.info("El usuario decidió no sobrescribir el archivo existente.")
                    self.error.emit("Descarga cancelada por el usuario")
                    return
            try:
                os.remove(temp_filename)
                logger.info(f"Archivo existente eliminado para sobrescribir: {temp_filename}")
            except Exception as e:
                logger.error(f"No se pudo eliminar el archivo existente: {e}")
                self.error.emit(f"No se pudo eliminar el archivo existente: {e}")
                return

        try:
            opts = self.get_ydl_options()
            cookie_path = self.cookie_manager.get_cookie_path()
            temp_cookie_path = None
            if cookie_path:
                import tempfile
                temp_cookie = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.txt')
                temp_cookie_path = temp_cookie.name
                temp_cookie.close()
                ok = self.cookie_manager._cookie_encryptor.decrypt_file(cookie_path.encode('utf-8'), temp_cookie_path.encode('utf-8'))
                if not ok:
                    logger.error("Error descifrando archivo de cookies con DLL para descarga.")
                    self.error.emit("Error descifrando archivo de cookies para descarga.")
                    return
                opts['cookiefile'] = temp_cookie_path
            with YoutubeDL(opts) as ydl:
                if self._cancelled:
                    self.cleanup_temp_files()
                    self.cancelled.emit()
                    return
                ydl.download([self.video_url])
        except DownloadCancelled:
            self.cleanup_temp_files()
            self.cancelled.emit()
            return
        except Exception as e:
            if self._cancelled and "Descarga cancelada por el usuario" in str(e):
                self.cancelled.emit()
                return
            self.error.emit(f"Error en la descarga: {e}")
            return
        finally:
            if temp_cookie_path and os.path.exists(temp_cookie_path):
                os.remove(temp_cookie_path)

        if self._cancelled:
            self.cleanup_temp_files()
            self.cancelled.emit()
            return

        final_path = self.final_filename or temp_filename
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

    def progress_hook(self, d):
        if self._cancelled:
            raise DownloadCancelled("Descarga cancelada por el usuario")
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                downloaded = d.get('downloaded_bytes', 0)
                percent = int(downloaded / total * 100)
                self.progress.emit(percent)
        elif d['status'] == 'finished':
            self.progress.emit(100)
            self.final_filename = d['info_dict']['_filename']
            logger.info(f"Archivo final: {self.final_filename}")

    @pyqtSlot(bool)
    def set_overwrite_answer(self, answer):
        with QMutexLocker(self.mutex):
            self.overwrite_answer = answer
            self.waitCondition.wakeAll()

    def cancel(self):
        """Marca el hilo como cancelado y detiene la descarga si es posible."""
        self._cancelled = True
        # Intentar detener procesos de yt-dlp si están activos
        try:
            if hasattr(self, '_ydl') and self._ydl:
                self._ydl._force_terminate = True
                if hasattr(self._ydl, 'proc') and self._ydl.proc:
                    self._ydl.proc.terminate()
        except Exception:
            pass
        # Forzar la interrupción del hilo si está bloqueado
        try:
            self.terminate()
        except Exception:
            pass

    def cancel_auth(self):
        """Cancela solo la autenticación (no la descarga)."""
        self._auth_cancelled = True
        if hasattr(self, "cookie_manager") and hasattr(self.cookie_manager, "_driver") and self.cookie_manager._driver:
            try:
                self.cookie_manager._driver.quit()
            except Exception:
                pass
            self.cookie_manager._driver = None

    def tiktok_filename_hook(self, info):
        """Hook para ajustar el nombre del archivo descargado de TikTok."""
        if info.get('status') == 'finished':
            desc = info['info_dict'].get('description', '')
            # Quitar # y limpiar nombre
            clean = desc.replace('#', '').strip()
            if not clean:
                clean = 'video_axolutly'
            # Usar '_filename' para compatibilidad con yt-dlp
            old_path = info['info_dict'].get('_filename') or info.get('filename')
            if not old_path:
                logger.error("No se pudo obtener el nombre del archivo final de TikTok (ni _filename ni filename)")
                return None
            ext = os.path.splitext(old_path)[1]
            new_path = os.path.join(os.path.dirname(old_path), f"{clean}{ext}")
            try:
                if old_path != new_path:
                    os.rename(old_path, new_path)
                    info['info_dict']['_filename'] = new_path
                    self.final_filename = new_path
            except Exception as e:
                logger.warning(f"No se pudo renombrar el archivo TikTok: {e}")
        return None

    def show_auth_dialog(self):
        """Muestra el diálogo de autenticación de forma no bloqueante e informativa"""
        try:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Autenticación requerida")
            msg.setText("Iniciando navegador para autenticación en YouTube...\n\nPor favor, inicie sesión en su cuenta.\nLa ventana se cerrará automáticamente al detectar el inicio de sesión.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.buttonClicked.connect(self.handle_auth_completed)
            msg.show()  # Usar show() en lugar de exec()
            logger.info("Diálogo de autenticación mostrado")
        except Exception as e:
            logger.error(f"Error mostrando diálogo de autenticación: {e}")
            self.show_error_message("Error en el proceso de autenticación")