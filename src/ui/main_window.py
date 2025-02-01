from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QCheckBox, QComboBox, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation
from PyQt6.QtGui import QIcon
import os
from Animation.Animation import AnimatedProgressBar
from config.logger import logger
from config.logger import Config
from src.services.hilo_descarga import DownloadThread
from src.services.utils import Utils

# Clase principal de la aplicación
class YouTubeDownloader(QWidget):
    """ GUI De la aplicación YouTube Downloader """
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.last_download_path = None
        self.download_thread = None
        logger.info("Aplicación YouTube Downloader iniciada")

    def init_ui(self):
        self.setWindowTitle('YouTube Downloader')
        self.setGeometry(100, 100, 600, 500)
        self.setWindowIcon(QIcon(os.path.join(Config.ICON_DIR, Config.ICON_YOUTUBE)))
        self.setup_ui_components()
        self.apply_styles()
        self.center_on_screen()
        logger.debug("Interfaz de usuario inicializada")

    def setup_ui_components(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.addWidget(self.create_title_label())
        layout.addWidget(self.create_url_input())
        layout.addLayout(self.create_options_layout())
        layout.addLayout(self.create_buttons_layout())
        layout.addWidget(self.create_open_last_download_button())
        layout.addWidget(self.create_progress_bar())
        layout.addWidget(self.create_status_label())

        self.setLayout(layout)

    def create_title_label(self):
        self.title_label = QLabel("YouTube Downloader")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setObjectName("title")
        return self.title_label

    def create_url_input(self):
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Ingrese la URL del video de YouTube")
        return self.url_input

    def create_options_layout(self):
        layout = QHBoxLayout()
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["2160p (4K)", "1440p (2K)", "1080p (FHD)", "720p (HD)", 
                                    "480p", "360p", "240p", "144p"])        
        self.quality_combo.setCurrentText("1080p (FHD)")
        self.quality_combo.setObjectName("quality_combo")
        layout.addWidget(self.quality_combo)

        self.audio_only_checkbox = QCheckBox("Solo audio")
        self.audio_only_checkbox.stateChanged.connect(self.toggle_quality_selector)
        layout.addWidget(self.audio_only_checkbox)
        return layout

    def create_buttons_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.create_download_button())
        layout.addWidget(self.create_cancel_button())
        return layout

    def toggle_quality_selector(self, state):
        self.quality_combo.setEnabled(not state)
        logger.info(f"Modo solo audio {'habilitado' if state else 'deshabilitado'}")

    def create_download_button(self):
        self.download_button = QPushButton("Descargar")
        self.download_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_button.setObjectName("download_button")
        self.download_button.setIcon(QIcon(os.path.join(Config.ICON_DIR, Config.ICON_DOWNLOAD)))
        self.download_button.setIconSize(QSize(24, 24))
        self.download_button.clicked.connect(self.start_download)
        self.add_button_animation(self.download_button)
        return self.download_button

    def create_cancel_button(self):
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.setIcon(QIcon(os.path.join(Config.ICON_DIR, Config.ICON_CANCEL)))
        self.cancel_button.setIconSize(QSize(24, 24))
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)
        self.add_button_animation(self.cancel_button)
        return self.cancel_button

    def create_open_last_download_button(self):
        self.open_last_download_button = QPushButton("Abrir última descarga")
        self.open_last_download_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_last_download_button.setObjectName("open_last_download_button")
        self.open_last_download_button.setIcon(QIcon(os.path.join(Config.ICON_DIR, Config.ICON_FOLDER)))
        self.open_last_download_button.setIconSize(QSize(24, 24))
        self.open_last_download_button.clicked.connect(self.open_last_download)
        self.open_last_download_button.setEnabled(False)
        self.add_button_animation(self.open_last_download_button)
        return self.open_last_download_button

    def add_button_animation(self, button):
        animation = QPropertyAnimation(button, b"geometry")
        animation.setDuration(200)
        animation.setStartValue(button.geometry())
        animation.setEndValue(button.geometry().adjusted(0, 0, 0, 10))
        button.clicked.connect(animation.start)

    def create_progress_bar(self):
        self.progress_bar = AnimatedProgressBar()
        return self.progress_bar

    def create_status_label(self):
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return self.status_label
    
    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)
        logger.error(f"Mensaje de error mostrado al usuario: {message}")

    def show_success_message(self, message):
        QMessageBox.information(self, "Éxito", message)
        logger.info(f"Mensaje de éxito mostrado al usuario: {message}")

    def closeEvent(self, event):
        if self.download_thread and self.download_thread.isRunning():
            response = QMessageBox.warning(
                self, 
                "Descarga en progreso",
                "Una descarga está en progreso. ¿Está seguro de que desea salir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if response == QMessageBox.StandardButton.Yes:
                self.download_thread.cancel()
                self.download_thread.wait()
                event.accept()
            else:
                event.ignore()

    def remove_temp_files(self):
        if not hasattr(self.download_thread, 'output_dir'):
            return

        output_dir = self.download_thread.output_dir
        for file in os.listdir(output_dir):
            if file.endswith(".tmp") or file.endswith(".part"):
                full_path = os.path.join(output_dir, file)
                try:
                    os.remove(full_path)
                    logger.info(f"Archivo temporal eliminado: {full_path}")
                except Exception as e:
                    logger.error(f"Error al eliminar el archivo temporal {full_path}: {str(e)}")

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {background-color: #f0f2f5;color: #333333;font-family: 'Segoe UI', Arial, sans-serif;}
            QLabel {font-size: 16px;color: #444444;}
            QLabel#title {font-size: 28px;font-weight: bold;color: #ff2d00;margin-bottom: 20px;}
            QLineEdit, QComboBox { padding: 10px;border: 2px solid #e0e0e0;border-radius: 8px;font-size: 16px;background-color: #ffffff;}
            QLineEdit:focus, QComboBox:focus {border-color: #e0e0e0;}
            QPushButton { padding: 12px;font-size: 16px;font-weight: bold;border: none;border-radius: 8px;}
            QPushButton#download_button { background-color: #007aff; color: white;}
            QPushButton#download_button:hover {background-color: #005bb5;}
            QPushButton#download_button:pressed {background-color: #003f7f;}
            QPushButton#cancel_button { background-color: #ff5252;color: white;}
            QPushButton#cancel_button:hover {background-color: #e04848;}
            QPushButton#cancel_button:pressed {background-color: #b03a3a;}
            QPushButton#cancel_button:disabled { background-color: #ffcccb; color: #808080;}
            QPushButton#open_last_download_button { background-color: #e0e0e0; color: #333333;}
            QPushButton#open_last_download_button:enabled { background-color: #ff9500; color: white;}
            QPushButton#open_last_download_button:hover:enabled { background-color: #cc7a00; }
            QPushButton#open_last_download_button:pressed:enabled { background-color: #995c00; }
            QProgressBar { border: 2px solid #e0e0e0; border-radius: 8px; text-align: center; height: 30px;background-color: #f0f0f0;}
            QProgressBar::chunk {background-color: #007aff; border-radius: 6px;}
            QCheckBox {font-size: 16px;}
            QCheckBox::indicator {width: 20px; height: 20px; }
        """)
        logger.debug("Estilo moderno aplicado a la interfaz")

    def center_on_screen(self):
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def validate_youtube_url(self, url):
        return Utils.validate_youtube_url(url)
    
    def open_last_download(self):
        if self.last_download_path:
            if os.path.exists(self.last_download_path):  # Verificar existencia real
                Utils.safe_open_file(self.last_download_path)
            else:
                self.show_error_message("El archivo ya no existe en la ubicación original")
                self.open_last_download_button.setEnabled(False)
                logger.warning(f"Archivo no encontrado: {self.last_download_path}")
                
    def start_download(self):
        url = self.url_input.text().strip()
        if not url or not self.validate_youtube_url(url):
            self.show_error_message("Por favor, ingrese una URL de YouTube válida.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Seleccione la carpeta de salida")
        if not output_dir:
            return

        quality_text = self.quality_combo.currentText().split('p')[0].strip()  # Extraer solo el número
        try:
            quality = int(quality_text)
        except ValueError:
            self.show_error_message("Calidad no válida. Usando 1080p por defecto.")
            quality = 1080  # Valor por defecto

        self.download_thread = DownloadThread(url, quality, self.audio_only_checkbox.isChecked(), output_dir)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)

        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.open_last_download_button.setEnabled(False)
        self.status_label.setText("Descargando...")
        logger.info(f"Descarga iniciada en modo {'solo audio' if self.audio_only_checkbox.isChecked() else f'{quality}p'}")
        self.download_thread.start()

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.status_label.setText("Cancelando descarga...")
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff5252; }")
            self.cancel_button.setEnabled(False)
            logger.info("Cancelación de descarga solicitada")
            
            self.download_thread.cancel()
            self.download_thread.wait()
            self.remove_temp_files()

            QMessageBox.information(self, "Descarga Cancelada", "La descarga ha sido cancelada.")
            self.progress_bar.setValue(0)
            self.status_label.setText("")
            self.progress_bar.setStyleSheet("")
            self.download_button.setEnabled(True)
            
    def update_progress(self, percentage: float):
        self.progress_bar.setValue(percentage)  # Acepta float pero se convierte a int internamente
        logger.debug(f"Progreso actualizado: {percentage}%")
        
    def download_finished(self, file_path):
        self.status_label.setText("¡Descarga completada!")
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.open_last_download_button.setEnabled(True)
        self.progress_bar.reset()
        self.progress_bar.setValue(0)
        self.last_download_path = file_path
        logger.info(f"Descarga completada: {os.path.basename(file_path)}")
        self.show_success_message(f"Descarga completada con éxito.\nArchivo: {os.path.basename(file_path)}")

    def download_error(self, error_message):
        self.status_label.setText("Error en la descarga")
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
        logger.error(f"Error en la descarga: {error_message}")
        self.show_error_message("Ocurrió un error durante la descarga. Por favor, inténtelo de nuevo.")
