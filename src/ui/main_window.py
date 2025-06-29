from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QCheckBox, QComboBox, QFileDialog, QMessageBox, QMenuBar, QMenu, QGraphicsOpacityEffect)
from PyQt6.QtGui import QIcon, QAction, QColor
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QSequentialAnimationGroup, QPauseAnimation, QEasingCurve, QTimer
import os
import sys
from Animation.Animation import AnimatedProgressBar, AnimatedWidget
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
        
        # Verificar DLLs críticas al inicio
        self.check_critical_dlls()
        
        self.init_ui()
        logger.info("Aplicación Axolutly iniciada")
        # Verificar actualización de la app al iniciar
        QTimer.singleShot(100, self.check_app_update_on_startup)

    def check_app_update_on_startup(self):
        """Verifica si hay una nueva versión de la app al iniciar y pregunta al usuario si desea actualizar"""
        updater = Updater()
        try:
            is_new, release = updater.is_update_available()
            if is_new and release:
                latest_version = release.get('tag_name', 'desconocida')
                changelog = release.get('body', '')
                msg = f"¡Hay una nueva versión disponible!\n\nVersión actual: {updater.get_current_version()}\nNueva versión: {latest_version}\n\n¿Deseas actualizar ahora?\n\nCambios:\n{changelog[:300]}{'...' if len(changelog)>300 else ''}"
                reply = QMessageBox.question(
                    self,
                    "Actualización disponible",
                    msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.check_for_updates()
        except Exception as e:
            logger.warning(f"No se pudo verificar actualización al inicio: {e}")
    
    def check_critical_dlls(self):
        """Verifica que las DLLs críticas estén presentes y muestra advertencias si faltan"""
        try:
            # Se eliminó quest.dll de la lista
            dlls_to_check = ["security.dll", "encryptor.dll", "anti_tampering.dll"]
            missing_dlls = []
            
            # Comprobar en múltiples rutas posibles
            for dll in dlls_to_check:
                # Comprobar primero en la ruta raíz
                if getattr(sys, 'frozen', False):
                    app_root = os.path.dirname(sys.executable)
                    root_path = os.path.join(app_root, dll)
                    lib_path = os.path.join(app_root, "lib", "src", "services", dll)
                    svc_path = os.path.join(app_root, "src", "services", dll)
                    
                    if not (os.path.exists(root_path) or os.path.exists(lib_path) or os.path.exists(svc_path)):
                        missing_dlls.append(dll)
                        logger.error(f"No se encontró {dll} en ninguna ruta esperada")
                else:
                    # En modo desarrollo, buscar en src/services
                    svc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", dll)
                    if not os.path.exists(svc_path):
                        missing_dlls.append(dll)
                        logger.error(f"No se encontró {dll} en {svc_path}")
        
            if missing_dlls:
                logger.warning(f"DLLs faltantes: {', '.join(missing_dlls)}")
                # Solo mostrar advertencia, no bloquear inicio
                print(f"Advertencia: Algunas DLLs críticas no se encontraron: {', '.join(missing_dlls)}")
        except Exception as e:
            logger.error(f"Error verificando DLLs críticas: {e}")
    
    def init_ui(self):
        self.setWindowTitle('Axolutly')
        self.setGeometry(100, 100, 600, 500)
        # Ajustar ruta de iconos para cx_Freeze
        icon_dir = Config.ICON_DIR
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            icon_dir = os.path.join(getattr(sys, '_MEIPASS', ''), "icons")
        self.setWindowIcon(QIcon(os.path.join(icon_dir, Config.ICON_YOUTUBE)))
        self.icon_dir = icon_dir 

        # Spinner de carga (GIF)
        from PyQt6.QtGui import QMovie
        self.spinner_label = QLabel(self)
        self.spinner_label.setObjectName("spinner_label")
        self.spinner_label.setFixedSize(20, 20)  # Tamaño fijo
        self.spinner_label.setStyleSheet("background: transparent;")
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner_label.setScaledContents(True)  # Escalar el GIF al tamaño del label
        spinner_gif_path = os.path.join(self.icon_dir, Config.ICON_GIF)
        self.spinner_movie = QMovie(spinner_gif_path)
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_label.hide()

        # Configurar el diseño principal antes de agregar la barra de menú
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Crear barra de menú
        self.menu_bar = QMenuBar(self)
        self.menu_bar.setObjectName("menu_bar")
        main_layout.setMenuBar(self.menu_bar)
        # Crear la barra de menú con opciones adicionales
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
        update_yt_dlp_action.setObjectName("update_yt_dlp_action")
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

            self.download_button = self.create_button("Descargar", Config.ICON_DOWNLOAD, self.start_download, "download_button", enabled=True)
            self.cancel_button = self.create_button("Cancelar", Config.ICON_CANCEL, self.cancel_download, "cancel_button", enabled=False)
            self.open_last_download_button = self.create_button("Abrir última descarga", Config.ICON_FOLDER, self.open_last_download, "open_last_download_button", enabled=False)
            # Integrar animaciones de opacidad en los botones principales usando AnimatedWidget
            buttons = [self.download_button, self.cancel_button, self.open_last_download_button]
            for button in buttons:
                AnimatedWidget.fade_in(button) # Aplicar efecto de entrada inicial
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
                # Conectar señal de umbral para efectos visuales
                self.progress_bar.value_threshold_reached.connect(self.on_progress_threshold)
                self.status_label = self.create_status_label()
                self.file_size_label = self.create_file_size_label()
                main_layout.addWidget(self.progress_bar)
                main_layout.addWidget(self.file_size_label)
                main_layout.addWidget(self.status_label)
                
                # Botón de actualización con texto superpuesto - movido más arriba para reducir espacio                
                update_layout = QHBoxLayout()  # Layout horizontal para centrar
                update_layout.addStretch()     # Espaciador izquierdo
                
                # Widget contenedor para superponer botón y texto
                update_container = QWidget()
                update_container.setFixedSize(200, 50)  # Tamaño fijo para el contenedor
                
                # Crear botón base
                self.update_button = QPushButton("", update_container)
                self.update_button.setObjectName("update_button")
                self.update_button.setCursor(Qt.CursorShape.PointingHandCursor)
                self.update_button.setToolTip("Buscar actualizaciones de Axolutly")
                self.update_button.clicked.connect(self.check_for_updates)
                self.update_button.setGeometry(0, 0, 200, 50)  # Ocupar todo el contenedor
                
                # Crear label de texto superpuesto
                self.update_label = QLabel("Buscar actualizaciones", update_container)
                self.update_label.setObjectName("update_label")
                self.update_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.update_label.setGeometry(0, 0, 200, 50)  # Misma posición que el botón
                self.update_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # Permitir clics pasen al botón
                
                update_layout.addWidget(update_container)
                update_layout.addStretch()     # Espaciador derecho
                
                update_widget = QWidget()
                update_widget.setLayout(update_layout)
                main_layout.addWidget(update_widget)
                
                self.version_label = self.create_version_label()
                main_layout.addWidget(self.version_label)

    def on_progress_threshold(self, threshold):
        """Aplica efectos visuales según el umbral alcanzado en la barra de progreso"""
        if threshold == 25:
            self.progress_bar.pulse_animation(duration=400)
        elif threshold == 50:
            self.progress_bar.pulse_animation(duration=400)
        elif threshold == 75:
            self.progress_bar.pulse_animation(duration=400)
        elif threshold == 100:
            self.progress_bar.glow_effect(QColor(0, 255, 0, 120), intensity=25)

    def add_shadow_effect(self, button):
        """Agrega un efecto de sombra (box-shadow) a un botón usando QGraphicsDropShadowEffect."""
        # Usar el color predeterminado basado en el tema
        color = QColor(0, 0, 0, 80) if not self.dark_mode else QColor(0, 0, 0, 120)
        # No crear efectos directamente, utilizar AnimatedWidget
        shadow = AnimatedWidget.add_drop_shadow(button, color=color, blur_radius=16, offset=(0, 4))
        button._shadow_effect = shadow

    def setup_button_animations(self, buttons):
        """Aplica animación de opacidad y escala a una lista de botones (simula hover/click)."""
        for button in buttons:
            # Utilizar la clase AnimatedWidget para efectos uniformes
            AnimatedWidget.add_click_effect(button)
            AnimatedWidget.add_hover_effect(button)

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
        self.quality_combo.setCursor(Qt.CursorShape.PointingHandCursor)
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
        # --- Cambios aquí: separar checkbox y label ---
        audio_only_layout = QHBoxLayout()
        self.audio_only_checkbox = QCheckBox("")  # Sin texto
        self.audio_only_checkbox.setObjectName("audio_only_checkbox")
        self.audio_only_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.audio_only_checkbox.setChecked(self.settings.get('audio_only', False))
        self.audio_only_checkbox.setToolTip("Descargar solo el audio en formato MP3")
        self.audio_only_checkbox.stateChanged.connect(self.toggle_quality_selector)
        self.audio_only_label = QLabel("Solo audio")
        self.audio_only_label.setObjectName("audio_only_label")
        audio_only_layout.addWidget(self.audio_only_checkbox)
        audio_only_layout.addWidget(self.audio_only_label)
        media_options.addLayout(audio_only_layout)
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
        # Cambiar icono según el tema
        # Actualizar icono del botón de tema con el nombre
        #self.theme_button.setIcon(QIcon(os.path.join(self.icon_dir, Config.ICON_THEME_DARK if self.dark_mode else Config.ICON_THEME_LIGHT)))
        #self.theme_button.setIconSize(QSize(24, 24))
        self.theme_button.setToolTip("Cambiar a tema claro" if self.dark_mode else "Cambiar a tema oscuro")
        self.settings.set('theme', 'dark' if self.dark_mode else 'light')
        self.apply_styles()
        logger.info(f"Tema cambiado a {'oscuro' if self.dark_mode else 'claro'}")

    def add_button_animation(self, button):
        animation_group = QSequentialAnimationGroup()
        move_animation = QPropertyAnimation(button, b"geometry")
        move_animation.setDuration(150)
        # Ajustar la geometría del botón para la animación
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
        progress_bar.setObjectName("progress_bar")
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

    def create_file_size_label(self):
        """Crea el label que muestra el tamaño del archivo debajo de la barra de progreso"""
        label = QLabel("")
        label.setObjectName("file_size_label")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.hide()  # Oculto por defecto, se muestra cuando hay información
        return label

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
                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Error al eliminar el archivo temporal {full_path}: {str(e)}")
                        break
                if not removed and os.path.exists(full_path):
                    logger.error(f"No se pudo eliminar el archivo temporal tras varios intentos (posiblemente sigue en uso): {full_path}")

    def apply_styles(self):
        # Cargar el archivo CSS limpio para el botón de actualización
        css_path = os.path.join(os.path.dirname(__file__), "axolutly_styles.css")
        theme = 'dark' if self.dark_mode else 'light'
        css = ""
        if os.path.exists(css_path):
            with open(css_path, encoding="utf-8") as f:
                css = f.read()
            # Reemplazar los selectores para el tema activo
            css = css.replace('[theme="dark"]', '' if self.dark_mode else '[theme="dark"]')
            css = css.replace('[theme="light"]', '' if not self.dark_mode else '[theme="light"]')
        
        # Establecer el atributo theme en el widget principal
        self.setProperty('theme', theme)
        self.setStyleSheet(css)
        logger.debug(f"Estilo {'oscuro' if self.dark_mode else 'claro'} aplicado")

    def setup_hover_animations(self):
        """
        Sistema de animaciones mejorado para botones usando PyQt6
        """
        # Aplica animación de opacidad, hover/click, glow y rebote a los botones principales usando AnimatedWidget
        for btn_attr in ['download_button', 'cancel_button', 'open_last_download_button', 'theme_button']:
            btn = getattr(self, btn_attr, None)
            if btn:
                AnimatedWidget.add_click_effect(btn)
                AnimatedWidget.add_hover_effect(btn)
                AnimatedWidget.add_glow_on_hover(btn)
                AnimatedWidget.add_bounce_on_click(btn)

    def enable_smooth_transitions(self):
        """
        Habilita transiciones suaves para cambios de tema en PyQt6
        """
        def fade_transition():
            AnimatedWidget.fade_out(self, duration=150)
            QTimer.singleShot(150, lambda: [self.apply_styles(), AnimatedWidget.fade_in(self, duration=150)])
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
                import subprocess
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
            self.show_error_message("Por favor, ingresa una URL válida de YouTube, Twitch o Tiktok.")
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
        self.download_thread.video_info.connect(self.update_video_info)
        self.download_thread.showAuthDialog.connect(self.show_auth_dialog)
        self.download_thread.cancelled.connect(self.handle_cancelled_download)  # <-- conectar señal cancelada

        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.open_last_download_button.setEnabled(False)
        self.status_label.setText("Descargando...")
        self.file_size_label.hide()  # Ocultar el tamaño del archivo anterior
        logger.info(f"Descarga iniciada en modo {'solo audio' if self.audio_only_checkbox.isChecked() else f'{quality}p'}")
        self.show_spinner()  # Mostrar spinner al iniciar descarga
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
                    f"El archivo '{file_name}' ya existe. ¿Desea Reemplazarlo?",
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
        self.file_size_label.hide()  # Ocultar tamaño al cancelar
        self.progress_bar.setStyleSheet("")
        self.progress_bar.shake_animation(duration=600, intensity=3)
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
        self.update_spinner_position(percentage)  # Mover el spinner según el progreso
        logger.debug(f"Progreso actualizado: {percentage}%")
        self.update_spinner_position(percentage)  # Actualizar posición del spinner

    def update_spinner_position(self, progress_percent: float):
        """Mueve el spinner sobre la barra de progreso según el porcentaje, adelantado un poco."""
        # Asegúrate de que la barra de progreso y el spinner existen
        if not hasattr(self, 'progress_bar') or not hasattr(self, 'spinner_label'):
            return
        bar = self.progress_bar
        spinner = self.spinner_label
        # Obtener geometría de la barra
        bar_geom = bar.geometry()
        # Calcular el rango útil (dejar margen para el GIF)
        min_x = bar_geom.x()
        max_x = bar_geom.x() + bar_geom.width() - spinner.width()
        # Porcentaje adelantado (por ejemplo, +1%)
        adelantado = min(progress_percent + 1, 100)
        pos_x = min_x + int((max_x - min_x) * (adelantado / 100))
        # Colocar el GIF justo encima de la barra
        pos_y = bar_geom.y() - spinner.height() - 4  # 4px de margen
        spinner.move(pos_x, pos_y)
        spinner.raise_()

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
        self.progress_bar.setValue(100)
        # Añadir animación de celebración al completar
        self.progress_bar.glow_effect(QColor(0, 255, 0, 100), intensity=25)
        QTimer.singleShot(1000, lambda: self.progress_bar.setValue(0))
        self.hide_spinner()  # Ocultar spinner al terminar
        self.last_download_path = Utils.sanitize_filepath(file_path)
        logger.info(f"Descarga completada: {os.path.basename(file_path)}")
        self.show_success_message(f"Descarga completada con éxito.\nArchivo: {os.path.basename(file_path)}")
        

    def download_error(self, error_message):
        # Evitar mostrar error si es cancelación
        if "Descarga cancelada por el usuario" in error_message:
            self.hide_spinner()
            return
        self.status_label.setText("Error en la descarga")
        self.file_size_label.hide()  # Ocultar tamaño en caso de error
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.shake_animation(duration=700, intensity=4)
        self.hide_spinner()  # Ocultar spinner si hay error
        logger.error(f"Error en la descarga: {error_message}")
        self.show_error_message("Ocurrió un error durante la descarga. Por favor, inténtelo de nuevo.\n\nSugerencia: Intenta actualizar yt-dlp desde el menú Archivo > Actualizar yt-dlp si el problema persiste.")

    def check_for_updates(self):
        """Verifica si hay actualizaciones disponibles utilizando el nuevo sistema."""
        self.update_button.setEnabled(False)
        self.update_label.setText("Buscando...")  # Cambiar el texto del label
        QApplication.processEvents()
        
        # Crear instancia del actualizador
        updater = Updater()
        
        # Obtener la versión actual
        current_version = updater.get_current_version()
        if not current_version:
            self.show_error_message("No se pudo obtener la versión actual.")
            self.update_button.setEnabled(True)
            self.update_label.setText("Buscar actualizaciones")  # Restaurar texto del label
            return
        
        # Iniciar proceso de actualización
        updater.download_and_apply_update(parent_widget=self)
        
        # Restaurar estado del botón y label
        self.update_button.setEnabled(True)
        self.update_label.setText("Buscar actualizaciones")  # Restaurar texto del label

    def show_spinner(self):
        """Muestra el spinner de carga animado, ya posicionado sobre la barra de progreso."""
        # Obtener el valor actual de la barra de progreso (o 0 si no existe)
        percent = 0
        if hasattr(self, 'progress_bar'):
            percent = self.progress_bar.value()
        self.update_spinner_position(percent)
        self.spinner_label.show()
        self.spinner_movie.start()

    def hide_spinner(self):
        """Oculta el spinner de carga animado."""
        self.spinner_movie.stop()
        self.spinner_label.hide()

    def _get_file_size(self, size_bytes: int) -> str:
        """Obtiene el tamaño del archivo en formato legible"""
        try:
            if size_bytes < 1000:
                return f"{size_bytes} B"
            elif size_bytes < 1_000_000:
                return f"{size_bytes/1_000:.2f} KB"
            elif size_bytes < 1_000_000_000:
                return f"{size_bytes/1_000_000:.2f} MB"
            else:
                return f"{size_bytes/(1_000_000_000):.2f} GB"
        except:
            return "Tamaño desconocido"
    
    def update_video_info(self, info: dict):
        """Actualiza la información del video, incluyendo el tamaño del archivo"""
        if 'total_size' in info:
            size_text = self._get_file_size(info['total_size'])
            self.file_size_label.setText(f"Tamaño del archivo: {size_text}")
            self.file_size_label.show()
            logger.info(f"Tamaño del archivo: {size_text}")