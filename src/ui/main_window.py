from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QCheckBox, QComboBox, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QSequentialAnimationGroup, QPauseAnimation, QEasingCurve
from PyQt6.QtGui import QIcon
import os
import sys
from Animation.Animation import AnimatedProgressBar
from config.logger import logger
from config.logger import Config
from src.services.hilo_descarga import DownloadThread
from src.services.utils import Utils
import time
from config.settings import Settings

class YouTubeDownloader(QWidget):
    """ GUI De la aplicación YouTube Downloader """
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.last_download_path = None
        self.download_thread = None
        self.dark_mode = self.settings.get('theme') == 'dark'
        self.init_ui()
        logger.info("Aplicación YouTube Downloader iniciada")

    def init_ui(self):
        self.setWindowTitle('YouTube Downloader')
        self.setGeometry(100, 100, 600, 500)
        # Ajustar ruta de iconos para PyInstaller/cx_Freeze
        icon_dir = Config.ICON_DIR
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            icon_dir = os.path.join(sys._MEIPASS, "icons")
        self.setWindowIcon(QIcon(os.path.join(icon_dir, Config.ICON_YOUTUBE)))
        self.icon_dir = icon_dir  # Guardar para uso en create_button
        self.setup_ui_components()
        self.apply_styles()
        self.center_on_screen()
        if Config.APP_MODE == "development":
            logger.debug("Interfaz de usuario inicializada")

    def setup_ui_components(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        self.title_label = self.create_title_label()
        self.url_input = self.create_url_input()
        self.options_layout = self.create_options_layout()
        
        self.download_button = self.create_button("Descargar", Config.ICON_DOWNLOAD, self.start_download, "download_button")
        self.cancel_button = self.create_button("Cancelar", Config.ICON_CANCEL, self.cancel_download, "cancel_button", enabled=False)
        self.open_last_download_button = self.create_button("Abrir última descarga", Config.ICON_FOLDER, self.open_last_download, "open_last_download_button", enabled=False)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.download_button)
        buttons_layout.addWidget(self.cancel_button)
        
        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.url_input)
        main_layout.addLayout(self.options_layout)
        main_layout.addLayout(buttons_layout)
        main_layout.addWidget(self.open_last_download_button)
        self.progress_bar = self.create_progress_bar()
        self.status_label = self.create_status_label()
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)
        self.version_label = self.create_version_label()
        main_layout.addWidget(self.version_label)
        self.setLayout(main_layout)

    def create_button(self, text, icon_name, slot, object_name, enabled=True):
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setObjectName(object_name)
        # Usar self.icon_dir para iconos
        button.setIcon(QIcon(os.path.join(self.icon_dir, icon_name)))
        button.setIconSize(QSize(24, 24))
        button.clicked.connect(slot)
        button.setEnabled(enabled)
        self.add_button_animation(button)
        return button

    def create_title_label(self):
        title_label = QLabel("YouTube Downloader")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("title")
        return title_label

    def create_url_input(self):
        url_input = QLineEdit()
        url_input.setPlaceholderText("Ingrese la URL del video de YouTube")
        return url_input
    
    def save_quality_preference(self, quality_text):
        # Extraer solo la parte numérica (por ejemplo, "1080p" de "1080p (FHD)")
        quality = quality_text.split(' ')[0]  # Obtiene "1080p"
        self.settings.set('default_quality', quality)
        logger.info(f"Preferencia de calidad guardada: {quality}")
        
    def create_options_layout(self):
        options_layout = QHBoxLayout()
        
        # Contenedor para calidad y modo audio
        media_options = QHBoxLayout()
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["2160p (4K)", "1440p (2K)", "1080p (FHD)", "720p (HD)", 
                                    "480p", "360p", "240p", "144p"])
        
        # Corregir la forma de obtener la calidad predeterminada
        default_quality = self.settings.get('default_quality', "1080p")
        default_quality_text = next((q for q in ["2160p (4K)", "1440p (2K)", "1080p (FHD)", "720p (HD)", 
                                                "480p", "360p", "240p", "144p"] 
                                    if q.startswith(default_quality)), "1080p (FHD)")
        
        self.quality_combo.setCurrentText(default_quality_text)
        self.quality_combo.setObjectName("quality_combo")
        self.quality_combo.setToolTip("Seleccione la calidad del video")
        
        # Conectar la señal de cambio del combobox para guardar la preferencia
        self.quality_combo.currentTextChanged.connect(self.save_quality_preference)
        
        media_options.addWidget(self.quality_combo)

        self.audio_only_checkbox = QCheckBox("Solo audio")
        self.audio_only_checkbox.setChecked(self.settings.get('audio_only', False))
        self.audio_only_checkbox.setToolTip("Descargar solo el audio en formato MP3")
        self.audio_only_checkbox.stateChanged.connect(self.toggle_quality_selector)
        media_options.addWidget(self.audio_only_checkbox)
        
        # Botón de cambio de tema mejorado
        self.theme_button = QPushButton()
        self.theme_button.setObjectName("theme_button")
        self.theme_button.setText("☀️" if self.dark_mode else "🌙")
        self.theme_button.setToolTip("Cambiar a tema claro" if self.dark_mode else "Cambiar a tema oscuro")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setFixedSize(40, 40)
        
        options_layout.addLayout(media_options)
        options_layout.addStretch()
        options_layout.addWidget(self.theme_button)
        
        return options_layout

    def toggle_quality_selector(self, state):
        self.quality_combo.setEnabled(not state)
        self.settings.set('audio_only', state)
        logger.info(f"Modo solo audio {'habilitado' if state else 'deshabilitado'}")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.theme_button.setText("☀️" if self.dark_mode else "🌙")
        self.theme_button.setToolTip("Cambiar a tema claro" if self.dark_mode else "Cambiar a tema oscuro")
        self.settings.set('theme', 'dark' if self.dark_mode else 'light')
        self.apply_styles()
        logger.info(f"Tema cambiado a {'oscuro' if self.dark_mode else 'claro'}")

    def add_button_animation(self, button):
        animation_group = QSequentialAnimationGroup()
        move_animation = QPropertyAnimation(button, b"geometry")
        move_animation.setDuration(150)
        move_animation.setStartValue(button.geometry())
        move_animation.setEndValue(button.geometry().adjusted(0, 0, 0, 5))
        move_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        pause = QPauseAnimation(25)
        return_animation = QPropertyAnimation(button, b"geometry")
        return_animation.setDuration(150)
        return_animation.setStartValue(button.geometry().adjusted(0, 0, 0, 5))
        return_animation.setEndValue(button.geometry())
        return_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        animation_group.addAnimation(move_animation)
        animation_group.addAnimation(pause)
        animation_group.addAnimation(return_animation)

        button.clicked.connect(animation_group.start)

    def create_progress_bar(self):
        progress_bar = AnimatedProgressBar()
        return progress_bar

    def create_status_label(self):
        status_label = QLabel("")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return status_label
    
    def create_version_label(self):
        version_label = QLabel("Versión: 1.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        version_label.setStyleSheet("color: #888888; font-size: 10px;")
        return version_label

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
        if self.dark_mode:
            self.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    font-family: "Roboto", "Segoe UI", "Arial", sans-serif;
                }
                QLabel {
                    font-size: 16px;
                    color: #ffffff;
                }
                QLabel#title {
                    font-size: 28px;
                    font-weight: bold;
                    color: #ff4545;
                    margin-bottom: 20px;
                }
                QLineEdit, QComboBox {
                    padding: 10px;
                    border: 2px solid #333333;
                    border-radius: 8px;
                    font-size: 16px;
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QLineEdit:focus, QComboBox:focus {
                    border-color: #505050;
                }
                QPushButton {
                    padding: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton#download_button {
                    background-color: #2962ff;
                    color: white;
                }
                QPushButton#download_button:hover {
                    background-color: #1e4bd8;
                }
                QPushButton#cancel_button {
                    background-color: #ff5252;
                    color: white;
                }
                /* Agregamos estilos para el botón de "Abrir última descarga" */
                QPushButton#open_last_download_button {
                    background-color: #ffab40;
                    color: white;
                }
                QPushButton#open_last_download_button:enabled {
                    background-color: #ffab40;
                    color: white;
                }
                QPushButton#open_last_download_button:hover:enabled {
                    background-color: #ffa000;
                }
                QPushButton#open_last_download_button:pressed:enabled {
                    background-color: #ff8f00;
                }
                QPushButton#theme_button {
                    background-color: #333333;
                    border-radius: 20px;
                    padding: 5px;
                    font-size: 18px;
                    min-width: 40px;
                    min-height: 40px;
                    border: none;
                    outline: none;
                }
                QPushButton#theme_button:hover {
                    background-color: #404040;
                    border-radius: 20px;
                }
                QPushButton#theme_button:pressed {
                    background-color: #505050;
                    border-radius: 20px;
                }
                QPushButton#theme_button:focus {
                    border: none;
                    outline: none;
                    border-radius: 20px;
                }
                QPushButton#theme_button:focus:!pressed {
                    background-color: #333333;
                    border-radius: 20px;
                }
                QProgressBar {
                    border: 2px solid #333333;
                    border-radius: 8px;
                    text-align: center;
                    height: 30px;
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QProgressBar::chunk {
                    background-color: #2962ff;
                    border-radius: 6px;
                }
                QCheckBox {
                    font-size: 16px;
                    color: #ffffff;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    background-color: #2d2d2d;
                    border: 2px solid #404040;
                    border-radius: 4px;
                }
                QCheckBox::indicator:checked {
                    background-color: #2962ff;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {background-color: #f0f2f5;color: #333333;font-family: "Roboto", "Segoe UI", "Arial", sans-serif;}
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
                QPushButton#theme_button {background-color: #e0e0e0; border-radius: 20px; padding: 5px; font-size: 18px; min-width: 40px; min-height: 40px; border: none; outline: none;}
                QPushButton#theme_button:hover {background-color: #d0d0d0; border-radius: 20px;}
                QPushButton#theme_button:pressed {background-color: #c0c0c0; border-radius: 20px;}
                QPushButton#theme_button:focus {border: none; outline: none; border-radius: 20px;}
                QPushButton#theme_button:focus:!pressed {background-color: #e0e0e0; border-radius: 20px;}
                QProgressBar { border: 2px solid #e0e0e0; border-radius: 8px; text-align: center; height: 30px;background-color: #f0f0f0;}
                QProgressBar::chunk {background-color: #007aff; border-radius: 6px;}
                QCheckBox {font-size: 16px;}
                QCheckBox::indicator {width: 20px; height: 20px; }
            """)
        logger.debug(f"Estilo {'oscuro' if self.dark_mode else 'claro'} aplicado")

    def center_on_screen(self):
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def validate_youtube_url(self, url):
        return Utils.validate_youtube_url(url)
    
    def open_last_download(self):
        if self.last_download_path:
            sanitized_path = Utils.sanitize_filepath(self.last_download_path)
            if os.path.exists(sanitized_path):
                import sys, subprocess
                if sys.platform.startswith("win"):
                    subprocess.run(["explorer", "/select,", sanitized_path])
                elif sys.platform == "darwin":
                    subprocess.run(["open", "-R", sanitized_path])
                else:
                    subprocess.run(["xdg-open", os.path.dirname(sanitized_path)])
            else:
                self.show_error_message("El archivo ya no existe en la ubicación original")
                self.open_last_download_button.setEnabled(False)
                logger.warning(f"Archivo no encontrado: {sanitized_path}")

    def get_mp3_path(self, path):
        """Centraliza la lógica para obtener la ruta final, convirtiendo .webm a .mp3 si es necesario."""
        if path.lower().endswith(".webm"):
            return path[:-5] + ".mp3"
        return path

    def start_download(self):
        url = self.url_input.text().strip()
        if not url or not self.validate_youtube_url(url):
            self.show_error_message("Por favor, ingrese una URL de YouTube válida.")
            return

        last_dir = self.settings.get('download_dir', '')
        output_dir = QFileDialog.getExistingDirectory(self, "Seleccione la carpeta de salida",
                                                     last_dir)
        if not output_dir:
            return

        self.settings.set('download_dir', output_dir)
        quality_text = self.quality_combo.currentText().split('p')[0].strip()
        try:
            quality = int(quality_text)
        except ValueError:
            self.show_error_message("Calidad no válida. Usando 1080p por defecto.")
            quality = 1080

        self.download_thread = DownloadThread(url, quality, self.audio_only_checkbox.isChecked(), output_dir)
        self.download_thread.requestOverwritePermission.connect(self.handle_overwrite_permission)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.showAuthDialog.connect(self.show_auth_dialog)
        
        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.open_last_download_button.setEnabled(False)
        self.status_label.setText("Descargando...")
        logger.info(f"Descarga iniciada en modo {'solo audio' if self.audio_only_checkbox.isChecked() else f'{quality}p'}")
        self.download_thread.start()

    def show_auth_dialog(self):
        """Muestra el diálogo de autenticación de forma no bloqueante"""
        try:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Autenticación requerida")
            msg.setText("1. Inicie sesión en YouTube\n2. Haga clic en OK cuando termine")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.buttonClicked.connect(self.handle_auth_completed)
            msg.show()  # Usar show() en lugar de exec()
            logger.info("Diálogo de autenticación mostrado")
        except Exception as e:
            logger.error(f"Error mostrando diálogo de autenticación: {e}")
            self.show_error_message("Error en el proceso de autenticación")

    def handle_auth_completed(self, button=None):
        """Maneja la completación de la autenticación"""
        try:
            if hasattr(self, 'download_thread') and self.download_thread:
                self.download_thread.set_auth_completed()
                self.status_label.setText("Autenticación completada. Continuando descarga...")
                logger.info("Autenticación completada por el usuario")
            else:
                logger.warning("No hay hilo de descarga activo para autenticar")
                self.status_label.setText("Error en la autenticación")
        except Exception as e:
            logger.error(f"Error en handle_auth_completed: {e}")
            self.show_error_message("Error procesando la autenticación")

    def handle_overwrite_permission(self, file_name):
        reply = QMessageBox.question(
                    self,
                    "Confirmar Sobrescritura",
                    f"El archivo '{file_name}' ya existe. ¿Desea sobrescribirlo?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
        self.download_thread.set_overwrite_answer(reply == QMessageBox.StandardButton.Yes)

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.status_label.setText("Cancelando descarga...")
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff5252; }")
            self.cancel_button.setEnabled(False)
            logger.info("Cancelación de descarga solicitada")
            
            self.download_thread.cancel()
            self.download_thread.finished.connect(self.handle_cancelled_download)

    def handle_cancelled_download(self):
        self.remove_temp_files()
        QMessageBox.information(self, "Descarga Cancelada", "La descarga ha sido cancelada.")
        self.progress_bar.setValue(0)
        self.status_label.setText("")
        self.progress_bar.setStyleSheet("")
        self.download_button.setEnabled(True)
            
    def update_progress(self, percentage: float):
        self.progress_bar.setValue(int(percentage))
        self.status_label.setText(f"Descargando: {int(percentage)}%")
        if percentage > 0:
            estimated_time = self.calculate_estimated_time(percentage)
            if estimated_time:
                self.status_label.setText(f"Descargando: {int(percentage)}% - Tiempo estimado: {estimated_time}")
        logger.debug(f"Progreso actualizado: {percentage}%")

    def calculate_estimated_time(self, current_percentage):
        if not hasattr(self, 'start_time'):
            self.start_time = time.time()
            return None
        
        if current_percentage <= 0:
            return None
            
        elapsed_time = time.time() - self.start_time
        estimated_total = (elapsed_time * 100) / current_percentage
        remaining_seconds = estimated_total - elapsed_time
        
        if remaining_seconds < 60:
            return f"{int(remaining_seconds)}s"
        elif remaining_seconds < 3600:
            minutes = int(remaining_seconds / 60)
            return f"{minutes}min"
        else:
            hours = int(remaining_seconds / 3600)
            minutes = int((remaining_seconds % 3600) / 60)
            return f"{hours}h {minutes}min"
        
    def download_finished(self, file_path):
        self.status_label.setText("¡Descarga completada!")
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.open_last_download_button.setEnabled(True)
        self.progress_bar.reset()
        self.progress_bar.setValue(0)
        self.last_download_path = Utils.sanitize_filepath(file_path)
        logger.info(f"Descarga completada: {os.path.basename(file_path)}")
        self.show_success_message(f"Descarga completada con éxito.\nArchivo: {os.path.basename(file_path)}")

    def download_error(self, error_message):
        self.status_label.setText("Error en la descarga")
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
        logger.error(f"Error en la descarga: {error_message}")
        self.show_error_message("Ocurrió un error durante la descarga. Por favor, inténtelo de nuevo.")
