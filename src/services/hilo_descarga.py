#formato base de la clase de hilo de descarga
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
        self.final_filename = None  # Almacenará el nombre real del archivo
        self.temp_file = None  # Almacenará el archivo temporal antes de conversión
        
    def run(self):
        try:
            ydl_opts = self.get_ydl_options()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.video_url, download=False)
                temp_filename = ydl.prepare_filename(info)
                
                if os.path.exists(temp_filename):
                    if not self.ask_overwrite_permission(temp_filename):
                        self.cancelled = True
                        raise Exception("Descarga cancelada por el usuario")
                
                ydl.download([self.video_url])
                
                if self.cancelled:
                    raise Exception("Descarga cancelada por el usuario")
                
                # Procesar conversión si es necesario
                final_path = self.process_conversion(temp_filename)
                
                self.finished.emit(final_path)
                logger.info(f"Descarga completada: {'solo audio' if self.audio_only else f'{self.quality}p'}")
                
        except yt_dlp.utils.DownloadError as e:
            if not self.cancelled:
                self.error.emit(f"Error de descarga: {str(e)}")
                logger.error(f"Error durante la descarga: {str(e)}")
        except ffmpeg.Error as e:
            self.error.emit(f"Error en la conversión: {str(e)}")
            logger.error(f"Error en la conversión: {str(e)}")
        except Exception as e:
            if not self.cancelled:
                self.error.emit(f"Error inesperado: {str(e)}")
                logger.error(f"Error inesperado durante la descarga: {str(e)}")
        finally:
            # Limpiar archivo temporal si existe
            if self.temp_file and os.path.exists(self.temp_file):
                os.remove(self.temp_file)
                
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
            
    def process_conversion(self, input_path):
        """Convierte el archivo a MP4 si no está en ese formato"""
        if self.audio_only:
            return input_path  # No necesita conversión para audio
        
        base, ext = os.path.splitext(input_path)
        if ext.lower() == '.mp4':
            return input_path  # Ya es MP4
            
        output_path = f"{base}.mp4"
        try:
            # Convertir usando FFmpeg
            (
                ffmpeg
                .input(input_path)
                .output(output_path, vcodec='copy', acodec='copy')
                .global_args('-loglevel', 'error')
                .run()
            )
            
            # Verificar si el archivo de salida fue creado correctamente
            if not os.path.exists(output_path):
                logger.error("Archivo de salida no creado durante la conversión")
                return input_path  # Devolver el archivo original si la conversión falló
                
            self.temp_file = input_path  # Marcar para eliminación
            logger.info(f"Conversión exitosa a MP4: {output_path}")
            return output_path
            
        except ffmpeg.Error as e:
            logger.error(f"Error en conversión: {str(e)}")
            return input_path  # Devolver original si falla
        
    def get_ydl_options(self):
        """Configuración modificada para priorizar calidad sobre formato"""
        opts = {
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
            'retries': 5,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
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
                # Priorizar la máxima calidad disponible
                'format': f'bestvideo[height<={self.quality}]+bestaudio/best',
                # Forzar la descarga del formato nativo
                'merge_output_format': None,
                'format_sort': [f'res:{self.quality}', 'res', '+codec']
            })
        return opts

    def progress_hook(self, d):
        if self.cancelled:
            raise Exception("Descarga cancelada por el usuario")
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0%').strip().replace('%', '')
            try:
                percent = float(percent_str)
                self.progress.emit(int(percent))  # Emitir como entero
            except ValueError:
                pass  # Ignorar valores inválidos
        elif d['status'] == 'finished':
            self.progress.emit(100)
            self.final_filename = d['info_dict']['_filename']
            logger.info(f"Archivo final: {self.final_filename}")

    def convert_to_mp3(self, input_file, output_file):
        try:
            ffmpeg.input(input_file).output(output_file, format='mp3', audio_bitrate='192k').run()
            os.remove(input_file)
            logger.info(f"Conversión a MP3 completada: {output_file}")
        except ffmpeg.Error as e:
            logger.error(f"Error en la conversión a MP3: {str(e)}")
            raise Exception("Error en la conversión a MP3")
