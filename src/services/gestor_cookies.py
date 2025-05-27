import os
import time
import browser_cookie3
import hashlib
from config.logger import logger
from selenium import webdriver
from src.services.utils import Utils
from config.settings import Settings
from src.services.security import Security

class GestorCookies:
    def __init__(self, parent=None):
        self._auth_completed = False
        self._driver = None
        self.parent = parent  # Puede ser DownloadThread para señales
        self.settings = Settings()
        self._setup_cookie_cleanup()
        self.security = Security()

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
        """Devuelve la ruta del archivo de cookies para yt-dlp."""
        cookie_dir = os.path.join(os.path.dirname(__file__), "cookies")
        cookie_path = os.path.join(cookie_dir, "youtube_cookies.txt")
        return cookie_path if os.path.exists(cookie_path) else None

    def update_cookies(self):
        """Actualiza las cookies usando Selenium solo si es necesario."""
        logger.info("Iniciando actualización de cookies...")
        
        # Obtener la ruta de cookies y asegurar que el directorio exista
        cookie_dir = os.path.join(os.path.dirname(__file__), "cookies")
        os.makedirs(cookie_dir, exist_ok=True)
        cookie_path = os.path.join(cookie_dir, "youtube_cookies.txt")

        # Validar la ruta de cookies
        if not Utils.is_safe_path(cookie_path):
            logger.error("Ruta de cookies no segura, abortando actualización de cookies.")
            raise Exception("Ruta de cookies no segura")

        # Reutilizar cookies existentes si son válidas
        if os.path.exists(cookie_path) and os.path.getsize(cookie_path) > 0:
            logger.info("Archivo de cookies existente encontrado. Reutilizando.")
            return cookie_path

        # Si no hay cookies válidas, usar Selenium como último recurso
        logger.info("No se encontraron cookies válidas. Iniciando autenticación con Selenium...")
        try:
            logger.info("Iniciando proceso de autenticación con Selenium...")
            browser_info = self._get_preferred_browser_path()
            if not browser_info:
                raise Exception("No se encontró un navegador compatible para la autenticación")
            browser_name, browser_path = browser_info

            # Prioridad: Chrome/Brave/Firefox/Opera, Edge solo si no hay otro
            if browser_name in ["chrome", "brave"]:
                from selenium.webdriver.chrome.options import Options
                options = Options()
                options.add_argument("--enable-unsafe-swiftshader")
                options.add_argument("--window-size=360,720")
                options.add_argument("--disable-gpu")  # <-- Mantener solo si es necesario
                options.add_argument("--no-sandbox")  # <-- Puede ser visto como sospechoso
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-extensions")
                options.add_argument(f"--user-agent=Axolutly v1.1.3")
                options.binary_location = browser_path
                self._driver = webdriver.Chrome(options=options)
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
                options.add_argument(f"--user-agent=Axolutly v1.1.3")
                options.binary_location = browser_path
                # OperaDriverManager instala el driver de Opera (chromium-based)
                service = ChromeService(executable_path=OperaDriverManager().install())
                self._driver = webdriver.Chrome(options=options, service=service)
            elif browser_name == "edge":
                from selenium.webdriver.edge.options import Options as EdgeOptions
                from selenium.webdriver.edge.service import Service as EdgeService
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                edge_options = EdgeOptions()
                # Opciones para minimizar advertencias de seguridad y permitir login
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
                edge_options.add_argument("--user-agent=Axolutly v1.1.3")
                edge_options.binary_location = browser_path
                edge_service = EdgeService(executable_path=EdgeChromiumDriverManager().install())
                self._driver = webdriver.Edge(options=edge_options, service=edge_service)
            else:
                raise Exception("Navegador no soportado para autenticación")
            self._driver.get("https://accounts.google.com/signin/v2/identifier?service=youtube")
            if self.parent and hasattr(self.parent, "showAuthDialog"):
                self.parent.showAuthDialog.emit()

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

            # Guardar cookies
            cookies = self._driver.get_cookies()
            cookie_lines = ["# Netscape HTTP Cookie File"]
            for cookie in cookies:
                if cookie.get('domain', '').endswith(('youtube.com', 'google.com')):
                    domain = cookie.get("domain", "")
                    flag = "TRUE" if domain.startswith('.') else "FALSE"
                    path = cookie.get("path", "/")
                    secure = "TRUE" if cookie.get("secure", False) else "FALSE"
                    expiry = cookie.get("expiry", int(time.time() + 3600*24*365))
                    name = cookie.get("name", "")
                    value = cookie.get("value", "")
                    cookie_lines.append(
                        f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}"
                    )

            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write("\n".join(cookie_lines))
            os.chmod(cookie_path, 0o600)
            logger.info(f"Cookies actualizadas: {cookie_path}")
        except Exception as e:
            logger.error(f"Error en autenticación Selenium: {e}")
            raise e
        finally:
            if self._driver:
                try:
                    self._driver.quit()
                except:
                    pass
                self._driver = None
        return cookie_path

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

            # Cifrar cookies antes de guardar
            encrypted_cookies = []
            for cookie in cookies:
                if not cookie.is_expired():
                    cookie_data = {
                        'domain': cookie.domain,
                        'flag': 'TRUE' if cookie.domain.startswith('.') else 'FALSE',
                        'path': cookie.path,
                        'secure': 'TRUE' if cookie.secure else 'FALSE',
                        'expiry': str(int(cookie.expires if cookie.expires else 0)),
                        'name': cookie.name,
                        'value': self.security.encrypt_data(cookie.value)
                    }
                    encrypted_cookies.append(cookie_data)

            with open(cookie_path, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                for cookie in encrypted_cookies:
                    f.write(f"{cookie['domain']}\t"
                        f"{cookie['flag']}\t"
                        f"{cookie['path']}\t"
                        f"{cookie['secure']}\t"
                        f"{cookie['expiry']}\t"
                        f"{cookie['name']}\t"
                        f"{cookie['value']}\n")

            try:
                os.chmod(cookie_path, 0o600)
            except Exception as e:
                logger.warning(f"No se pudieron establecer permisos restrictivos al archivo de cookies: {e}")

            logger.info(f"Archivo de cookies creado y cifrado: {cookie_path}")
            return True
        except Exception as e:
            logger.error(f"Error creando archivo de cookies: {e}")
            return False

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
