from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
import os
import ffmpeg
import yt_dlp
from config.logger import logger

# Clase de hilo de descarga
class DownloadThread(QThread):
    
    """ Hilo de descarga el cual se encarga de descargar un video de YouTube 
        ya sea en video o audio."""
        
    progress = pyqtSignal(float)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    video_info = pyqtSignal(dict)

    def __init__(self, video_url, quality, audio_only, output_dir):
        super().__init__()
        self.video_url = video_url
        self.quality = quality
        self.audio_only = audio_only
        self.output_dir = output_dir
        self.cancelled = False

    def run(self):
        try:
            ydl_opts = self.get_ydl_options()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.video_url, download=False)
                file_name = ydl.prepare_filename(info)
                
                if os.path.exists(file_name):
                    if not self.ask_overwrite_permission(file_name):
                        self.cancelled = True
                        raise Exception("Descarga cancelada por el usuario")
                
                ydl.download([self.video_url])
                
                if self.cancelled:
                    raise Exception("Descarga cancelada por el usuario")
                
                ext = 'mp3' if self.audio_only else 'mp4'
                final_path = os.path.splitext(file_name)[0] + f'.{ext}'
                
                if self.audio_only:
                    self.convert_to_mp3(file_name, final_path)
                
                self.finished.emit(final_path)
                logger.info(f"Descarga completada: {'solo audio' if self.audio_only else f'{self.quality}p'}")
        except yt_dlp.utils.DownloadError as e:
            if not self.cancelled:
                self.error.emit(f"Error de descarga: {str(e)}")
                logger.error(f"Error durante la descarga: {str(e)}")
        except ffmpeg.Error as e:
            self.error.emit(f"Error en la conversión a MP3: {str(e)}")
            logger.error(f"Error en la conversión a MP3: {str(e)}")
        except Exception as e:
            if not self.cancelled:
                self.error.emit(f"Error inesperado: {str(e)}")
                logger.error(f"Error inesperado durante la descarga: {str(e)}")

    def ask_overwrite_permission(self, file_name):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText(f"El archivo '{file_name}' ya existe. ¿Desea sobrescribirlo?")
        msg_box.setWindowTitle("Confirmar Sobrescritura")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msg_box.exec() == QMessageBox.StandardButton.Yes

    def cancel(self):
        self.cancelled = True
        self.quit()
        self.wait()
            
    def get_ydl_options(self):
        return {
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
            'no_color': True,
            'nooverwrites': True,  # Prevent overwriting existing files
            'continue_dl': True,   # Continue partial downloads
            'retries': 5,          # Incrementar el número de reintentos
            'fragment_retries': 5, # Incrementar el número de reintentos de fragmentos
            'timeout': 30,         # Timeout después de 30 segundos
            'force_generic_extractor': False,  # Cambiado a False para usar el extractor específico
            'concurrent_fragment_downloads': 3, # Descargar fragmentos en paralelo
            'nocheckcertificate': True,  # Ignorar errores de certificado SSL
            'extractor_retries': 5,      # Reintentos del extractor
            'http_headers': {            # Headers personalizados
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
            },
            **(
                {'format': 'bestaudio/best'} if self.audio_only else 
                {'format': f'bestvideo[height<={self.quality}]+bestaudio[ext=m4a]/best[height<={self.quality}]',
                'merge_output_format': 'mp4'}
            )
        }
            
    def progress_hook(self, d):
        if self.cancelled:
            raise Exception("Descarga cancelada por el usuario")
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip().replace('%', '')
            speed = d.get('_speed_str', '0B/s')
            eta = d.get('_eta_str', '00:00')
            try:
                self.progress.emit(float(percent))
                logger.info(f"Progreso: {percent}%, Velocidad: {speed}, ETA: {eta}")
            except ValueError:
                self.progress.emit(0)
        elif d['status'] == 'finished':
            self.progress.emit(100)
            logger.info("Descarga finalizada")

    def convert_to_mp3(self, input_file, output_file):
        try:
            ffmpeg.input(input_file).output(output_file, format='mp3', audio_bitrate='192k').run()
            os.remove(input_file)
            logger.info(f"Conversión a MP3 completada: {output_file}")
        except ffmpeg.Error as e:
            logger.error(f"Error en la conversión a MP3: {str(e)}")
            raise Exception("Error en la conversión a MP3")
