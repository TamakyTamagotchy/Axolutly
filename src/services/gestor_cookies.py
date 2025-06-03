import os
import time
import browser_cookie3
import hashlib
from config.logger import logger
from selenium import webdriver
from src.services.utils import Utils
from config.settings import Settings
from src.services.security import Security
import tempfile
import ctypes
from src.services.anti_tampering import AntiTampering

class GestorCookies:
    def __init__(self, parent=None):
        # Protección anti-tampering antes de inicializar cualquier lógica sensible
        anti = AntiTampering()
        if not anti.is_safe_environment():
            logger.critical("Entorno inseguro detectado (anti-tampering/cookies). Abortando ejecución.")
            raise RuntimeError("Entorno inseguro detectado. La aplicación se cerrará.")
        
        self._auth_completed = False
        self._driver = None
        self.parent = parent  # Puede ser DownloadThread para señales
        self.settings = Settings()
        self._setup_cookie_cleanup()
        self.security = Security()

        # Cargar la DLL de cifrado
        dll_path = os.path.join(os.path.dirname(__file__), "encryptor.dll")
        self._cookie_encryptor = ctypes.CDLL(dll_path)
        self._cookie_encryptor.encrypt_file.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._cookie_encryptor.encrypt_file.restype = ctypes.c_bool
        self._cookie_encryptor.decrypt_file.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._cookie_encryptor.decrypt_file.restype = ctypes.c_bool

    def _setup_cookie_cleanup(self):
        """Configura la limpieza automática de cookies antiguas"""
        try:
            cookie_dir = os.path.join(os.path.dirname(__file__), "cookies")
            if os.path.exists(cookie_dir):
                current_time = time.time()
                retention_days = self.settings.get('cookie_retention_days', 7)
                max_age = retention_days * 24 * 60 * 60
                
                for file in os.listdir(cookie_dir):
                    file_path = os.path.join(cookie_dir, file)
                    if os.path.isfile(file_path):
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age:
                            try:
                                os.remove(file_path)
                                logger.info(f"Cookie antigua eliminada: {file}")
                            except Exception as e:
                                logger.error(f"Error eliminando cookie antigua: {e}")
        except Exception as e:
            logger.error(f"Error en limpieza de cookies: {e}")

    def get_cookie_path(self):
        """Devuelve la ruta del archivo de cookies cifrado para yt-dlp."""
        cookie_dir = os.path.join(os.path.dirname(__file__), "cookies")
        cookie_path = os.path.join(cookie_dir, "ck.dll")
        return cookie_path if os.path.exists(cookie_path) else None

    def update_cookies(self):
        """Actualiza las cookies usando Selenium solo si es necesario. Intenta con varios navegadores si hay error."""
        logger.info("Iniciando actualización de cookies...")
        cookie_dir = os.path.join(os.path.dirname(__file__), "cookies")
        os.makedirs(cookie_dir, exist_ok=True)
        # El archivo .txt solo será temporal e invisible
        last_error = None
        browser_preference = self.settings.get('browser_preference', ["brave", "chrome", "firefox", "opera", "edge"])
        # Buscar rutas de todos los navegadores instalados
        browser_paths = {}
        browser_registry = {
            'chrome': r'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe',
            'firefox': r'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\firefox.exe',
            'edge': r'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\msedge.exe',
            'brave': r'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\brave.exe',
            'opera': r'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\launcher.exe'
        }
        import winreg
        for browser, reg_path in browser_registry.items():
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                    path = winreg.QueryValue(key, None)
                    if path and os.path.exists(path):
                        browser_paths[browser] = path
            except Exception:
                continue
        for browser_try in browser_preference:
            if browser_try not in browser_paths:
                continue
            # Mostrar mensaje ANTES de intentar con el navegador
            if self.parent and hasattr(self.parent, "show_error_message"):
                self.parent.show_error_message(f"Probando autenticación con: {browser_try.capitalize()}...")
            try:
                logger.info(f"Intentando autenticación con navegador: {browser_try}")
                browser_name = browser_try
                browser_path = browser_paths[browser_try]
                # Prioridad: Chrome/Brave/Firefox/Opera, Edge solo si no hay otro
                if browser_name in ["chrome", "brave"]:
                    from selenium.webdriver.chrome.options import Options
                    from selenium.webdriver.chrome.service import Service as ChromeService
                    from webdriver_manager.chrome import ChromeDriverManager
                    options = Options()
                    options.add_argument("--enable-unsafe-swiftshader")
                    options.add_argument("--window-size=360,720")
                    options.add_argument("--disable-gpu")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-extensions")
                    options.add_argument(f"--user-agent=Axolutly v1.2.0")
                    options.binary_location = browser_path
                    service = ChromeService(executable_path=ChromeDriverManager().install())
                    self._driver = webdriver.Chrome(options=options, service=service)
                elif browser_name == "firefox":
                    from selenium.webdriver.firefox.options import Options as FirefoxOptions
                    from selenium.webdriver.firefox.service import Service as FirefoxService
                    from webdriver_manager.firefox import GeckoDriverManager
                    firefox_options = FirefoxOptions()
                    firefox_options.binary_location = browser_path
                    firefox_options.add_argument("--disable-gpu")
                    firefox_service = FirefoxService(executable_path=GeckoDriverManager().install())
                    self._driver = webdriver.Firefox(options=firefox_options, service=firefox_service)
                elif browser_name == "opera":
                    from selenium.webdriver.chrome.options import Options
                    from selenium.webdriver.chrome.service import Service as ChromeService
                    from webdriver_manager.opera import OperaDriverManager
                    options = Options()
                    options.add_argument("--enable-unsafe-swiftshader")
                    options.add_argument("--disable-gpu")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--window-size=360,720")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-extensions")
                    options.add_argument(f"--user-agent=Axolutly v1.2.0")
                    options.binary_location = browser_path
                    service = ChromeService(executable_path=OperaDriverManager().install())
                    self._driver = webdriver.Chrome(options=options, service=service)
                elif browser_name == "edge":
                    from selenium.webdriver.edge.options import Options as EdgeOptions
                    from selenium.webdriver.edge.service import Service as EdgeService
                    from webdriver_manager.microsoft import EdgeChromiumDriverManager
                    edge_options = EdgeOptions()
                    edge_options.add_argument("--disable-gpu")
                    edge_options.add_argument("--no-sandbox")
                    edge_options.add_argument("--disable-extensions")
                    edge_options.add_argument("--disable-dev-shm-usage")
                    edge_options.add_argument("--window-size=360,720")
                    edge_options.add_argument("--ignore-certificate-errors")
                    edge_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
                    edge_options.add_argument("--disable-blink-features=AutomationControlled")
                    edge_options.add_argument("--disable-popup-blocking")
                    edge_options.add_argument("--disable-infobars")
                    edge_options.add_argument("--disable-notifications")
                    edge_options.add_argument("--disable-web-security")
                    edge_options.add_argument("--allow-running-insecure-content")
                    edge_options.add_argument("--user-agent=Axolutly v1.2.0")
                    edge_options.binary_location = browser_path
                    edge_service = EdgeService(executable_path=EdgeChromiumDriverManager().install())
                    self._driver = webdriver.Edge(options=edge_options, service=edge_service)
                else:
                    raise Exception("Navegador no soportado para autenticación")
                
                self._driver.get("https://accounts.google.com/signin/v2/identifier?service=youtube")
                if self.parent and hasattr(self.parent, "showAuthDialog"):
                    self.parent.showAuthDialog.emit()
                # Al abrir el navegador exitosamente, borra el mensaje de error
                if self.parent and hasattr(self.parent, "clear_error_message"):
                    self.parent.clear_error_message()
                timeout = 300
                start_time = time.time()
                while not self._auth_completed and time.time() - start_time < timeout:
                    time.sleep(0.1)
                    # Verificar explícitamente si la autenticación fue cancelada
                    if self.parent and hasattr(self.parent, "_cancelled") and self.parent._cancelled:
                        logger.warning("Autenticación cancelada por el usuario desde el hilo principal.")
                        raise Exception("Autenticación cancelada por el usuario")

                if not self._auth_completed:
                    raise Exception("Timeout en autenticación")

                if "youtube.com" not in self._driver.current_url:
                    self._driver.get("https://www.youtube.com")
                    time.sleep(2)

                # Guardar cookies en archivo temporal invisible
                with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.txt') as tmp:
                    tmp.write("# Netscape HTTP Cookie File\n")
                    for cookie in self._driver.get_cookies():
                        if cookie.get('domain', '').endswith(('youtube.com', 'google.com')):
                            domain = cookie.get("domain", "")
                            flag = "TRUE" if domain.startswith('.') else "FALSE"
                            path = cookie.get("path", "/")
                            secure = "TRUE" if cookie.get("secure", False) else "FALSE"
                            expiry = cookie.get("expiry", int(time.time() + 3600*24*365))
                            name = cookie.get("name", "")
                            value = cookie.get("value", "")
                            tmp.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
                    tmp_path = tmp.name
                # Cifrar archivo temporal a .dll (invisible para el usuario)
                encrypted_path = os.path.join(cookie_dir, "ck.dll")
                ok = self._cookie_encryptor.encrypt_file(tmp_path.encode('utf-8'), encrypted_path.encode('utf-8'))
                os.remove(tmp_path)
                if not ok:
                    logger.error("Error cifrando archivo de cookies con DLL.")
                    raise Exception("Error cifrando archivo de cookies con DLL.")
                try:
                    os.chmod(encrypted_path, 0o600)
                except Exception as e:
                    logger.warning(f"No se pudieron establecer permisos restrictivos al archivo de cookies: {e}")
                logger.info(f"Archivo de cookies cifrado creado: {encrypted_path}")
                if self._driver:
                    try:
                        self._driver.quit()
                    except:
                        pass
                    self._driver = None
                return encrypted_path
            except Exception as e:
                logger.error(f"Error con navegador {browser_try}: {e}")
                # Mostrar advertencia de error y que se intentará con otro navegador
                if self.parent and hasattr(self.parent, "show_error_message"):
                    self.parent.show_error_message(f"Error con {browser_try.capitalize()}. Intentando con otro navegador...")
                if self._driver:
                    try:
                        self._driver.quit()
                    except:
                        pass
                    self._driver = None
                last_error = e
                continue
        # Si todos los navegadores fallan
        logger.error(f"Todos los navegadores fallaron para la autenticación de cookies: {last_error}")
        if self.parent and hasattr(self.parent, "show_error_message"):
            self.parent.show_error_message(str(last_error) if last_error else "No se pudo autenticar con ningún navegador.")
        if last_error:
            raise last_error
        else:
            raise RuntimeError("No se pudo autenticar con ningún navegador.")

    def _get_preferred_browser_path(self):
        """Obtiene la ruta y nombre del navegador predeterminado del usuario usando el registro de Windows"""
        try:
            import winreg
            user_default = None
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
                    prog_id = winreg.QueryValueEx(key, "ProgId")[0].lower()
                    if "brave" in prog_id:
                        user_default = "brave"
                    elif "chrome" in prog_id:
                        user_default = "chrome"
                    elif "firefox" in prog_id:
                        user_default = "firefox"
                    elif "opera" in prog_id:
                        user_default = "opera"
                    elif "edge" in prog_id:
                        user_default = "edge"
            except Exception as e:
                logger.warning(f"No se pudo determinar el navegador predeterminado del usuario: {e}")

            browser_paths = {}
            browser_registry = {
                'chrome': r'Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe',
                'firefox': r'Software\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe',
                'edge': r'Software\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe',
                'brave': r'Software\Microsoft\Windows\CurrentVersion\App Paths\brave.exe',
                'opera': r'Software\Microsoft\Windows\CurrentVersion\App Paths\launcher.exe'
            }
            for browser, reg_path in browser_registry.items():
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                        path = winreg.QueryValue(key, None)
                        if path and os.path.exists(path):
                            browser_paths[browser] = path
                except WindowsError:
                    continue
            if user_default and user_default in browser_paths:
                logger.info(f"Usando el navegador predeterminado del usuario: {user_default}")
                return user_default, browser_paths[user_default]
            browser_preference = self.settings.get('browser_preference', [])
            for browser in browser_preference:
                if browser in browser_paths:
                    logger.info(f"Usando navegador preferido configurado: {browser}")
                    return browser, browser_paths[browser]
            if browser_paths:
                browser, path = next(iter(browser_paths.items()))
                logger.info(f"Usando navegador disponible: {browser}")
                return browser, path
            logger.warning("No se encontraron navegadores instalados")
            return None
        except Exception as e:
            logger.error(f"Error al buscar navegadores: {e}")
            return None

    def set_auth_completed(self):
        """Marca la autenticación como completada"""
        self._auth_completed = True
        logger.info("Autenticación completada en gestor de cookies")
        
    def get_browser_cookies(self):
        cookies = []
        browser_preference = self.settings.get('browser_preference',
        ["brave","opera","chrome","firefox","edge"])

        # Validar que browser_cookie3 esté disponible de manera segura
        try:
            browser_map = {
                "chrome": (browser_cookie3.chrome, "Chrome"),
                "firefox": (browser_cookie3.firefox, "Firefox"),
                "brave": (browser_cookie3.brave, "Brave"),
                "opera": (browser_cookie3.opera, "Opera"),
                "edge": (browser_cookie3.edge, "Edge")
            }
        except Exception as e:
            logger.error(f"Error al inicializar mapeado de navegadores: {e}")
            return cookies

        for browser_name in browser_preference:
            if browser_name in browser_map:
                try:
                    browser_func, display_name = browser_map[browser_name]
                    # Usar un timeout para prevenir bloqueos
                    import threading
                    cookie_event = threading.Event()
                    cookie_result = []

                    def get_cookies():
                        try:
                            result = browser_func(domain_name="youtube.com")
                            if result:
                                cookie_result.extend(result)
                            cookie_event.set()
                        except Exception as e:
                            logger.debug(f"Error obteniendo cookies de {display_name}: {e}")
                            cookie_event.set()

                    cookie_thread = threading.Thread(target=get_cookies)
                    cookie_thread.daemon = True
                    cookie_thread.start()

                    # Esperar máximo 5 segundos
                    if cookie_event.wait(timeout=5.0):
                        if cookie_result:
                            cookies.extend(cookie_result)
                            logger.info(f"Cookies obtenidas de {display_name}")
                            break
                    else:
                        logger.warning(f"Timeout obteniendo cookies de {display_name}")

                except Exception as e:
                    logger.debug(f"No se pudieron obtener cookies de {display_name}: {e}")
                    continue

        return cookies

    def create_cookie_file(self, cookies, cookie_path):
        try:
            if not Utils.is_safe_path(cookie_path):
                logger.error("Ruta de cookies no segura, abortando creación de archivo de cookies.")
                return False

            # Guardar cookies en archivo temporal fuera de la carpeta visible
            with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.txt') as tmp:
                tmp.write("# Netscape HTTP Cookie File\n")
                for cookie in cookies:
                    if not cookie.is_expired():
                        tmp.write(f"{cookie.domain}\t"
                                  f"{'TRUE' if cookie.domain.startswith('.') else 'FALSE'}\t"
                                  f"{cookie.path}\t"
                                  f"{'TRUE' if cookie.secure else 'FALSE'}\t"
                                  f"{int(cookie.expires if cookie.expires else 0)}\t"
                                  f"{cookie.name}\t"
                                  f"{self.security.encrypt_data(cookie.value)}\n")
                tmp_path = tmp.name

            # Cifrar archivo temporal a .dll (invisible para el usuario)
            encrypted_path = cookie_path.replace('.txt', '.dll')
            ok = self._cookie_encryptor.encrypt_file(tmp_path.encode('utf-8'), encrypted_path.encode('utf-8'))
            os.remove(tmp_path)  # Elimina el archivo temporal inmediatamente
            if not ok:
                logger.error("Error cifrando archivo de cookies con DLL.")
                return False
            try:
                os.chmod(encrypted_path, 0o600)
            except Exception as e:
                logger.warning(f"No se pudieron establecer permisos restrictivos al archivo de cookies: {e}")
            logger.info(f"Archivo de cookies cifrado creado: {encrypted_path}")
            return True
        except Exception as e:
            logger.error(f"Error creando archivo de cookies: {e}")
            return False

    def read_cookies(self, encrypted_path):
        """Descifra el archivo de cookies y devuelve el contenido como texto."""
        try:
            with tempfile.NamedTemporaryFile(delete=False, mode='r', encoding='utf-8', suffix='.txt') as tmp:
                tmp_path = tmp.name
            ok = self._cookie_encryptor.decrypt_file(encrypted_path.encode('utf-8'), tmp_path.encode('utf-8'))
            if not ok:
                logger.error("Error descifrando archivo de cookies con DLL.")
                return None
            with open(tmp_path, 'r', encoding='utf-8') as f:
                data = f.read()
            os.remove(tmp_path)
            return data
        except Exception as e:
            logger.error(f"Error leyendo archivo de cookies cifrado: {e}")
            return None

    def check_file_exists(self, filepath):
        if not Utils.is_safe_path(filepath):
            logger.warning(f"Ruta de archivo no segura: {filepath}")
            return False, None
        if not os.path.exists(filepath):
            return False, None
        try:
            existing_hash = self.get_file_hash(filepath)
            parent_dir = os.path.dirname(filepath)
            base_name = os.path.basename(filepath)
            similar_files = []
            for file in os.listdir(parent_dir):
                if file != base_name:
                    full_path = os.path.join(parent_dir, file)
                    if os.path.isfile(full_path) and Utils.is_safe_path(full_path):
                        file_hash = self.get_file_hash(full_path)
                        if file_hash == existing_hash:
                            similar_files.append(file)
            return True, similar_files
        except Exception as e:
            logger.error(f"Error verificando archivo duplicado: {e}")
            return False, None

    def get_file_hash(self, filepath, block_size=65536):
        if not Utils.is_safe_path(filepath):
            logger.warning(f"Ruta de archivo no segura para hash: {filepath}")
            return ""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for block in iter(lambda: f.read(block_size), b""):
                sha256_hash.update(block)
        return sha256_hash.hexdigest()

    def get_cookie_file_for_yt_dlp(self):
        """Descifra el archivo .dll a un archivo temporal solo para uso de yt-dlp y lo elimina tras su uso."""
        encrypted_path = self.get_cookie_path()
        if not encrypted_path:
            return None
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.txt') as tmp:
            tmp_path = tmp.name
        ok = self._cookie_encryptor.decrypt_file(encrypted_path.encode('utf-8'), tmp_path.encode('utf-8'))
        if not ok:
            logger.error("Error descifrando archivo de cookies con DLL para yt-dlp.")
            os.remove(tmp_path)
            return None
        # Usar el archivo temporal con yt-dlp y eliminarlo después
        return tmp_path  # El llamador debe hacer: ... usar tmp_path ...; os.remove(tmp_path)
