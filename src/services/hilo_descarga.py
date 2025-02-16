from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition, QMutexLocker, pyqtSlot
from PyQt6.QtWidgets import QMessageBox
import os
import sys
from yt_dlp import YoutubeDL
from yt_dlp.utils.networking import std_headers
from config.logger import logger
from selenium.webdriver.chrome.options import Options
from selenium import webdriver

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
            opts = self.get_ydl_options()
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.video_url, download=False)
        except Exception as e:
            if "age" in str(e).lower() or "restricted" in str(e).lower():
                logger.info("Restricción de edad detectada. Solicitando autenticación...")
                self.update_cookies()
                try:
                    with YoutubeDL(self.get_ydl_options()) as ydl:
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
            self.cancelled = True
            self.error.emit("Descarga cancelada por el usuario")
            return
        elif os.path.exists(temp_filename):
            os.remove(temp_filename)
        try:
            with YoutubeDL(self.get_ydl_options()) as ydl:
                ydl.download([self.video_url])
        except Exception as e:
            self.error.emit(f"Error en la descarga: {e}")
            return

        if self.cancelled:
            self.error.emit("Descarga cancelada por el usuario")
            return
        final_path = self.final_filename or temp_filename
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
        
        # Usar sys._MEIPASS cuando se ejecute como exe
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(os.path.dirname(__file__))
        
        for f in os.listdir(base_path):
            if f.lower() == "cookies.txt":
                netscape_path = os.path.join(base_path, f)
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

    def update_cookies(self):
        """Actualiza cookies.txt iniciando sesión en YouTube usando Brave.
            Se guarda la sesión para las posteriores descargas."""
        logger.info("Iniciando proceso de actualización de sesión...")
        base_path = os.path.abspath(os.path.dirname(__file__))
        cookie_filepath = os.path.join(base_path, "cookies.txt")
        if os.path.exists(cookie_filepath):
            logger.info("Sesión detectada. Se usarán las cookies almacenadas.")
        else:
            logger.info("No se detectaron cookies previas. Creando nuevo archivo de cookies.")

        logger.info("Abriendo navegador Brave para autenticación...")
        options = Options()
        BRAVE_PATH = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
        options.binary_location = BRAVE_PATH
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-bluetooth")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Se elimina el uso de ChromeDriverManager
        driver = webdriver.Chrome(options=options)
        driver.get("https://accounts.google.com/signin/v2/identifier?service=youtube")
        
        # Mostrar mensaje directo al usuario utilizando un QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Autenticación requerida")
        msg.setText("Inicie sesión en YouTube en la ventana del navegador y luego haga clic en OK cuando haya finalizado la autenticación.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

        cookies = driver.get_cookies()
        cookie_lines = ["# Netscape HTTP Cookie File"]
        for cookie in cookies:
            domain = cookie.get("domain", "")
            flag = "TRUE" if domain.startswith('.') else "FALSE"
            path = cookie.get("path", "/")
            secure = "TRUE" if cookie.get("secure", False) else "FALSE"
            expiry = cookie.get("expiry", 0)
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            cookie_lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")

        with open(cookie_filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(cookie_lines))
        logger.info(f"Cookies actualizadas: {cookie_filepath}")
        driver.quit()
