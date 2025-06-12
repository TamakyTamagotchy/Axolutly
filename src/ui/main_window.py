from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QCheckBox, QComboBox, QFileDialog, QMessageBox, QMenuBar, QMenu, QGraphicsOpacityEffect, QGraphicsDropShadowEffect)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QSequentialAnimationGroup, QPauseAnimation, QEasingCurve, QTimer
import os
import sys
from Animation.Animation import AnimatedProgressBar
from config.logger import logger
from config.logger import Config
from src.services.hilo_descarga import DownloadThread
from src.services.utils import Utils
import time
from config.settings import Settings
from src.services.updater import Updater

version = "Version "+ Config.VERSION
class YouTubeDownloader(QWidget):
    """ GUI De la aplicación Axolutly """
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.last_download_path = None
        self.download_thread = None
        self.dark_mode = self.settings.get('theme') == 'dark'
        self.init_ui()
        logger.info("Aplicación Axolutly iniciada")

    def init_ui(self):
        self.setWindowTitle('Axolutly')
        self.setGeometry(100, 100, 600, 500)
        # Ajustar ruta de iconos para cx_Freeze
        icon_dir = Config.ICON_DIR
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            icon_dir = os.path.join(getattr(sys, '_MEIPASS', ''), "icons")
        self.setWindowIcon(QIcon(os.path.join(icon_dir, Config.ICON_YOUTUBE)))
        self.icon_dir = icon_dir 

        # Configurar el diseño principal antes de agregar la barra de menú
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Crear barra de menú
        self.menu_bar = QMenuBar(self)
        self.create_menu_bar()

        self.setup_ui_components()
        self.apply_styles()
        self.setup_hover_animations()
        self.enable_smooth_transitions()
        self.center_on_screen()
        if Config.APP_MODE == "development":
            logger.debug("Interfaz de usuario inicializada")

    def create_menu_bar(self):
        """Crea la barra de menú con opciones adicionales."""
        # Menú principal
        file_menu = QMenu("Archivo", self)
        self.menu_bar.addMenu(file_menu)

        # Opción para actualizar yt-dlp
        update_yt_dlp_action = QAction("Actualizar yt-dlp", self)
        update_yt_dlp_action.triggered.connect(lambda: Updater.update_yt_dlp(self))
        file_menu.addAction(update_yt_dlp_action)

        # Opción para salir
        exit_action = QAction("Salir", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Añadir la barra de menú al diseño principal
        layout = self.layout()
        if layout is not None and hasattr(layout, 'setMenuBar'):
            layout.setMenuBar(self.menu_bar)

    def setup_ui_components(self):
        main_layout = self.layout()  # Usa el diseño ya configurado en init_ui
        if main_layout is not None:
            main_layout.setContentsMargins(30, 30, 30, 30)
            main_layout.setSpacing(20)

            self.title_label = self.create_title_label()
            self.url_input = self.create_url_input()
            self.options_layout = self.create_options_layout()
            
            self.download_button = self.create_button("Descargar", Config.ICON_DOWNLOAD, self.start_download, "download_button")
            self.cancel_button = self.create_button("Cancelar", Config.ICON_CANCEL, self.cancel_download, "cancel_button", enabled=False)
            self.open_last_download_button = self.create_button("Abrir última descarga", Config.ICON_FOLDER, self.open_last_download, "open_last_download_button", enabled=False)
            
            # Integrar animaciones de opacidad en los botones principales
            self.setup_button_animations([self.download_button, self.cancel_button, self.open_last_download_button])
            # Agregar sombra a los botones principales
            self.add_shadow_effect(self.download_button)
            self.add_shadow_effect(self.cancel_button)
            self.add_shadow_effect(self.open_last_download_button)

            buttons_layout = QHBoxLayout()
            buttons_layout.addWidget(self.download_button)
            buttons_layout.addWidget(self.cancel_button)
            
            # Añadir layouts secundarios usando widgets contenedores para evitar el error de addLayout
            if main_layout is not None:
                main_layout.addWidget(self.title_label)
                main_layout.addWidget(self.url_input)
                options_widget = QWidget()
                options_widget.setLayout(self.options_layout)
                main_layout.addWidget(options_widget)
                buttons_widget = QWidget()
                buttons_widget.setLayout(buttons_layout)
                main_layout.addWidget(buttons_widget)
                main_layout.addWidget(self.open_last_download_button)
                self.progress_bar = self.create_progress_bar()
                self.status_label = self.create_status_label()
                main_layout.addWidget(self.progress_bar)
                main_layout.addWidget(self.status_label)
                self.version_label = self.create_version_label()
                main_layout.addWidget(self.version_label)
                
                # Botón de actualización
                self.update_button = QPushButton("Buscar actualizaciones")
                self.update_button.setObjectName("update_button")
                self.update_button.clicked.connect(self.check_for_updates)
                if main_layout is not None:
                    main_layout.addWidget(self.update_button)

    def add_shadow_effect(self, button):
        """Agrega un efecto de sombra (box-shadow) a un botón usando QGraphicsDropShadowEffect."""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        shadow.setColor(Qt.GlobalColor.black)
        # Si ya hay un efecto de opacidad, lo anidamos correctamente
        if button.graphicsEffect():
            effect = button.graphicsEffect()
            # Creamos un widget contenedor para ambos efectos si es necesario
            # (PyQt6 no soporta múltiples efectos directos, así que priorizamos la sombra visual)
            button.setGraphicsEffect(shadow)
            button._shadow_effect = shadow
            button._opacity_effect = effect
        else:
            button.setGraphicsEffect(shadow)
            button._shadow_effect = shadow

    def setup_button_animations(self, buttons):
        """Aplica animación de opacidad y escala a una lista de botones (simula hover/click)."""
        for button in buttons:
            # Efecto de opacidad
            opacity_effect = QGraphicsOpacityEffect(button)
            button.setGraphicsEffect(opacity_effect)
            button._opacity_effect = opacity_effect
            # Animación de opacidad para click
            animation = QPropertyAnimation(opacity_effect, b"opacity", button)
            animation.setDuration(120)
            animation.setStartValue(1.0)
            animation.setEndValue(0.7)
            animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            # Animación de opacidad para soltar
            animation_back = QPropertyAnimation(opacity_effect, b"opacity", button)
            animation_back.setDuration(120)
            animation_back.setStartValue(0.7)
            animation_back.setEndValue(1.0)
            animation_back.setEasingCurve(QEasingCurve.Type.InOutQuad)
            # Animación de escala (simula transform: scale)
            # No se puede escalar directamente QPushButton, pero podemos simularlo con geometry
            scale_anim = QPropertyAnimation(button, b"geometry", button)
            scale_anim.setDuration(120)
            scale_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            scale_back_anim = QPropertyAnimation(button, b"geometry", button)
            scale_back_anim.setDuration(120)
            scale_back_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            def enterEvent(event, btn=button, anim=scale_anim):
                rect = btn.geometry()
                anim.stop()
                anim.setStartValue(rect)
                anim.setEndValue(rect.adjusted(-2, -2, 2, 2))
                anim.start()
                event.accept()
            def leaveEvent(event, btn=button, anim=scale_back_anim):
                rect = btn.geometry()
                anim.stop()
                anim.setStartValue(rect)
                anim.setEndValue(rect.adjusted(2, 2, -2, -2))
                anim.start()
                event.accept()
            def mousePressEvent(event, btn=button, anim=animation):
                anim.start()
                QPushButton.mousePressEvent(btn, event)
            def mouseReleaseEvent(event, btn=button, anim=animation_back):
                anim_back = animation_back
                anim_back.start()
                QPushButton.mouseReleaseEvent(btn, event)
            button.enterEvent = enterEvent
            button.leaveEvent = leaveEvent
            button.mousePressEvent = mousePressEvent
            button.mouseReleaseEvent = mouseReleaseEvent

    def create_button(self, text, icon_name, slot, object_name, enabled=True):
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setObjectName(object_name)
        # Usar self.icon_dir para iconos
        button.setIcon(QIcon(os.path.join(self.icon_dir, icon_name)))
        button.setIconSize(QSize(24, 24))
        button.clicked.connect(slot)
        button.setEnabled(enabled)
        return button

    def create_title_label(self):
        title_label = QLabel("Axolutly")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("title")
        return title_label

    def create_url_input(self):
        url_input = QLineEdit()
        url_input.setPlaceholderText("Pega aquí la URL de YouTube, Twitch o TikTok...")
        url_input.setObjectName("url_input")
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
        self.quality_combo.currentTextChanged.connect(self.save_quality_preference)
        media_options.addWidget(self.quality_combo)
        self.audio_only_checkbox = QCheckBox("Solo audio")
        self.audio_only_checkbox.setChecked(self.settings.get('audio_only', False))
        self.audio_only_checkbox.setToolTip("Descargar solo el audio en formato MP3")
        self.audio_only_checkbox.stateChanged.connect(self.toggle_quality_selector)
        media_options.addWidget(self.audio_only_checkbox)
        # Estado inicial del combo de calidad según el checkbox
        self.quality_combo.setEnabled(not self.audio_only_checkbox.isChecked())
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
        version_label = QLabel(f"{version}")
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
        if self.download_thread is None or not hasattr(self.download_thread, 'output_dir'):
            return

        output_dir = self.download_thread.output_dir
        for file in os.listdir(output_dir):
            if file.endswith(".tmp") or file.endswith(".part"):
                full_path = os.path.join(output_dir, file)
                removed = False
                for attempt in range(20):  # Hasta 10 segundos (20*0.5)
                    try:
                        os.remove(full_path)
                        logger.info(f"Archivo temporal eliminado: {full_path}")
                        removed = True
                        break
                    except PermissionError as e:
                        import time
                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Error al eliminar el archivo temporal {full_path}: {str(e)}")
                        break
                if not removed and os.path.exists(full_path):
                    logger.error(f"No se pudo eliminar el archivo temporal tras varios intentos (posiblemente sigue en uso): {full_path}")

    def apply_styles(self):
        # Cargar el archivo CSS externo y aplicar el tema correspondiente
        css_path = os.path.join(os.path.dirname(__file__), "axolutly_styles.css")
        theme = 'dark' if self.dark_mode else 'light'
        css = ""
        if os.path.exists(css_path):
            with open(css_path, encoding="utf-8") as f:
                css = f.read()
            # Reemplazar los selectores para el tema activo
            css = css.replace('[theme="dark"]', '' if self.dark_mode else '[theme="dark"]')
            css = css.replace('[theme="light"]', '' if not self.dark_mode else '[theme="light"]')
        self.setStyleSheet(css)
        logger.debug(f"Estilo {'oscuro' if self.dark_mode else 'claro'} aplicado")

    def setup_hover_animations(self):
        """
        Sistema de animaciones mejorado para botones usando PyQt6
        """
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

        def add_opacity_animation(button):
            effect = QGraphicsOpacityEffect(button)
            button.setGraphicsEffect(effect)
            animation = QPropertyAnimation(effect, b"opacity")
            animation.setDuration(180)
            animation.setStartValue(1.0)
            animation.setEndValue(0.7)
            animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

            # Guardar referencias para evitar que el GC elimine la animación
            button._opacity_effect = effect
            button._opacity_animation = animation

            original_enter = getattr(button, 'enterEvent', None)
            original_leave = getattr(button, 'leaveEvent', None)

            def enterEvent(event):
                if original_enter:
                    original_enter(event)
                animation.setDirection(QPropertyAnimation.Direction.Forward)
                animation.start()

            def leaveEvent(event):
                if original_leave:
                    original_leave(event)
                animation.setDirection(QPropertyAnimation.Direction.Backward)
                animation.start()

            button.enterEvent = enterEvent
            button.leaveEvent = leaveEvent

        # Aplica animación de opacidad a los botones principales
        if hasattr(self, 'download_button'):
            add_opacity_animation(self.download_button)
        if hasattr(self, 'cancel_button'):
            add_opacity_animation(self.cancel_button)
        if hasattr(self, 'open_last_download_button'):
            add_opacity_animation(self.open_last_download_button)
        if hasattr(self, 'theme_button'):
            add_opacity_animation(self.theme_button)

    def enable_smooth_transitions(self):
        """
        Habilita transiciones suaves para cambios de tema en PyQt6
        """
        def fade_transition():
            # Crear efecto de opacidad para la transición
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
            
            # Configurar animación de fade out
            fade_out = QPropertyAnimation(effect, b"opacity")
            fade_out.setDuration(150)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            # Configurar animación de fade in
            fade_in = QPropertyAnimation(effect, b"opacity")
            fade_in.setDuration(150)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            # Crear grupo de animaciones secuencial
            sequence = QSequentialAnimationGroup()
            sequence.addAnimation(fade_out)
            sequence.addAnimation(fade_in)
            
            # Ejecutar el cambio de tema durante la transición
            def on_fade_out_finished():
                self.apply_styles()
                fade_in.start()
            
            fade_out.finished.connect(on_fade_out_finished)
            fade_out.start()

        # Conectar la transición al cambio de tema
        if hasattr(self, 'toggle_theme'):
            original_toggle = self.toggle_theme
            def new_toggle():
                original_toggle()
                fade_transition()
            self.toggle_theme = new_toggle

    def center_on_screen(self):
        """
        Centra la ventana en la pantalla, ajustando tanto X como Y con un offset vertical
        """
        screen = QApplication.primaryScreen()
        if screen is not None:
            # Obtener el área disponible de la pantalla (excluyendo la barra de tareas)
            available_geometry = screen.availableGeometry()
            
            # Obtener el tamaño real de la ventana incluyendo decoraciones
            frame_geometry = self.frameGeometry()
            
            # Calcular las coordenadas centrales con un offset vertical
            x = available_geometry.center().x() - frame_geometry.width() // 2
            y = available_geometry.center().y() - frame_geometry.height() // 2
            
            # Aplicar offset vertical para compensar
            vertical_offset = 60  # Ajustar este valor según sea necesario
            y = max(0, y - vertical_offset)
            
            # Mover la ventana a la posición calculada
            self.move(x, y)

    def validate_youtube_url(self, url):
        # Ahora acepta YouTube y Twitch
        return Utils.validate_supported_url(url)
    
    def open_last_download(self):
        if self.last_download_path:
            sanitized_path = Utils.sanitize_filepath(self.last_download_path)
            if sanitized_path and os.path.exists(sanitized_path):
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
        if not url:
            self.show_error_message("Por favor, ingresa una URL.")
            return
        # Twitch: canal en vivo (no VOD, no clip)
        if Utils.is_twitch_live_channel_url(url):
            self.show_error_message("El usuario está en stream. No se puede descargar el stream en vivo de Twitch.")
            return
        # Validación general
        if not Utils.validate_supported_url(url):
            self.show_error_message("Por favor, ingresa una URL válida de YouTube o Twitch (VOD o clip).")
            return

        last_dir = self.settings.get('download_dir', '')
        output_dir = QFileDialog.getExistingDirectory(self, "Seleccione la carpeta de salida", last_dir)
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
        self.download_thread.cancelled.connect(self.handle_cancelled_download)  # <-- conectar señal cancelada

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
        if not self.download_thread or not hasattr(self.download_thread, 'set_overwrite_answer'):
            return
        self.download_thread.set_overwrite_answer(reply == QMessageBox.StandardButton.Yes)

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.status_label.setText("Cancelando descarga...")
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff5252; }")
            self.cancel_button.setEnabled(False)
            logger.info("Cancelación de descarga solicitada")
            self.download_thread.cancel()  # Solo cancela la descarga

    def handle_cancelled_download(self):
        self.remove_temp_files()
        self.progress_bar.reset()
        self.progress_bar.setValue(0)
        self.status_label.setText("")
        self.progress_bar.setStyleSheet("")
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.open_last_download_button.setEnabled(False)
        QMessageBox.information(self, "Descarga Cancelada", "La descarga ha sido cancelada.")
        logger.info("Descarga cancelada correctamente por el usuario")

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
        # Evitar mostrar error si es cancelación
        if "Descarga cancelada por el usuario" in error_message:
            return
        self.status_label.setText("Error en la descarga")
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
        logger.error(f"Error en la descarga: {error_message}")
        self.show_error_message("Ocurrió un error durante la descarga. Por favor, inténtelo de nuevo.")

    def check_for_updates(self):
        """Verifica si hay actualizaciones disponibles."""
        self.update_button.setEnabled(False)
        self.update_button.setText("Buscando...")
        QApplication.processEvents()
        available, info = Updater.is_new_version_available()
        if available:
            reply = QMessageBox.question(
                self,
                "Actualización disponible",
                f"Hay una nueva versión disponible.\n¿Desea descargar e instalar la actualización?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                Updater.download_and_apply_update(info, parent_widget=self)
        else:
            QMessageBox.information(self, "Actualización", "No hay actualizaciones disponibles.")
        self.update_button.setEnabled(True)
        self.update_button.setText("Buscar actualizaciones")