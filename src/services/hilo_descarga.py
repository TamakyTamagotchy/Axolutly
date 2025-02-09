from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition, QMutexLocker, pyqtSlot
import os
from yt_dlp import YoutubeDL
from yt_dlp.utils.networking import std_headers
from config.logger import logger

class DownloadThread(QThread):
    
    """ Hilo de descarga el cual se encarga de descargar un video de YouTube 
        ya sea en video o audio."""
        
    progress = pyqtSignal(float)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    video_info = pyqtSignal(dict)
    requestOverwritePermission = pyqtSignal(str)

    def __init__(self, video_url, quality, audio_only, output_dir):
        super().__init__()
        self.video_url = video_url
        self.quality = quality
        self.audio_only = audio_only
        self.output_dir = output_dir
        self.cancelled = False
        self.final_filename = None  # Almacenará el nombre real del archivo
        self.temp_file = None  # Almacenará el archivo temporal antes de conversión
        self.overwrite_answer = None
        self.mutex = QMutex()
        self.waitCondition = QWaitCondition()
        
    def run(self):
        try:
            ydl_opts = self.get_ydl_options()
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.video_url, download=False)
        except Exception as e:
            logger.error(f"Error extrayendo información: {e}")
            self.error.emit(f"Error extrayendo información: {e}")
            return

        temp_filename = ydl.prepare_filename(info)
        if os.path.exists(temp_filename):
            if not self.ask_overwrite_permission(temp_filename):
                self.cancelled = True
                self.error.emit("Descarga cancelada por el usuario")
                return
            else:
                os.remove(temp_filename)
        # Descarga integrada en yt‑dlp
        try:
            ydl.download([self.video_url])
        except Exception as e:
            self.error.emit(f"Error en la descarga: {e}")
            return

        if self.cancelled:
            self.error.emit("Descarga cancelada por el usuario")
            return
        final_path = self.final_filename if self.final_filename else temp_filename
        self.finished.emit(final_path)
        logger.info(f"Descarga completada: {'solo audio' if self.audio_only else f'{self.quality}p'}")

    def ask_overwrite_permission(self, file_name):
        self.overwrite_answer = None
        self.requestOverwritePermission.emit(file_name)
        with QMutexLocker(self.mutex):
            waited = self.waitCondition.wait(self.mutex, 10000)
            if not waited or self.overwrite_answer is None:
                logger.error("Timeout esperando confirmación de sobrescritura; se asume 'No'.")
                self.overwrite_answer = False
        return self.overwrite_answer

    @pyqtSlot(bool)
    def set_overwrite_answer(self, answer):
        with QMutexLocker(self.mutex):
            self.overwrite_answer = answer
            self.waitCondition.wakeAll()

    def cancel(self):
        self.cancelled = True
        self.quit()
            
    def get_ydl_options(self):
        opts = {
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
            'retries': 5,
            'http_headers': std_headers,
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
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                }],
                'merge_output_format': 'mp4',
                'format_sort': ['height', 'vcodec:h264', 'filesize', 'ext'],
            })
        
        # Iterar sobre los archivos del directorio para detectar "cookies_netscape.txt"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for f in os.listdir(current_dir):
            if f.lower() == "cookies.txt":
                netscape_path = os.path.join(current_dir, f)
                opts['cookiefile'] = netscape_path
                logger.info(f"Cookie file detectado: {netscape_path}")
                break

        return opts

    def progress_hook(self, d):
        if self.cancelled:
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
