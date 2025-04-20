import os
import time
import browser_cookie3
import hashlib
from config.logger import logger
from selenium.webdriver.chrome.options import Options
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
        cookie_dir = os.path.join(os.path.dirname(__file__), "cookies")
        cookie_path = os.path.join(cookie_dir, "youtube_cookies.txt")
        if os.path.exists(cookie_path) and os.path.getsize(cookie_path) > 0:
            return cookie_path
        return None

    def update_cookies(self):
        logger.info("Iniciando actualización de cookies...")
        
        # Limitar el acceso a directorios seguros
        cookie_dir = os.path.join(os.path.dirname(__file__), "cookies")
        if not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir, mode=0o700)

        # Usar opciones de navegador más seguras
        options = Options()
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-background-networking")
        options.add_argument("--metrics-recording-only")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument(f"--user-agent=YouTube Downloader v1.1.0")
        
        # Limitar permisos del navegador
        options.add_argument("--deny-permission-prompts")
        options.add_argument("--disable-permissions-api")
        
        # Evitar comportamientos sospechosos
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            os.chmod(cookie_dir, 0o700)
        except Exception as e:
            logger.warning(f"No se pudieron establecer permisos restrictivos al directorio de cookies: {e}")

        cookie_path = os.path.join(cookie_dir, "youtube_cookies.txt")
        if not Utils.is_safe_path(cookie_path):
            logger.error("Ruta de cookies no segura, abortando actualización de cookies.")
            raise Exception("Ruta de cookies no segura")

        if os.path.exists(cookie_path):
            try:
                if os.path.getsize(cookie_path) > 0:
                    logger.info("Archivo de cookies ya existe y no está vacío, reutilizando cookies.")
                    return cookie_path
            except Exception as e:
                logger.warning(f"No se pudo verificar el archivo de cookies existente: {e}")

        cookies = self.get_browser_cookies()
        if cookies:
            if self.create_cookie_file(cookies, cookie_path):
                try:
                    os.chmod(cookie_path, 0o600)
                except Exception as e:
                    logger.warning(f"No se pudieron establecer permisos restrictivos al archivo de cookies: {e}")
                logger.info("Cookies actualizadas exitosamente")
                return cookie_path

        try:
            logger.info("Iniciando proceso de autenticación con Selenium...")
            options = Options()
            options.add_argument("--enable-unsafe-swiftshader")
            options.add_argument("--disable-gpu")
            browser_path = self._get_preferred_browser_path()
            if browser_path:
                options.binary_location = browser_path
            
            # Eliminar comportamientos sospechosos
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--window-size=1280,720")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument(f"--user-agent=YouTube Downloader v1.0.8")
            
            self._driver = webdriver.Chrome(options=options)
            self._driver.get("https://accounts.google.com/signin/v2/identifier?service=youtube")
            if self.parent and hasattr(self.parent, "showAuthDialog"):
                self.parent.showAuthDialog.emit()
            timeout = 300
            start_time = time.time()
            while not self._auth_completed and time.time() - start_time < timeout:
                time.sleep(0.1)
                if self.parent and hasattr(self.parent, "cancelled") and self.parent.cancelled:
                    raise Exception("Autenticación cancelada por el usuario")
            if not self._auth_completed:
                raise Exception("Timeout en autenticación")
            if "youtube.com" not in self._driver.current_url:
                self._driver.get("https://www.youtube.com")
                time.sleep(2)
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
            if not Utils.is_safe_path(cookie_path):
                logger.error("Ruta de cookies no segura, abortando guardado de cookies Selenium.")
                raise Exception("Ruta de cookies no segura")
            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write("\n".join(cookie_lines))
            try:
                os.chmod(cookie_path, 0o600)
            except Exception as e:
                logger.warning(f"No se pudieron establecer permisos restrictivos al archivo de cookies: {e}")
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
        browsers = {
            "brave": "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe",
            "chrome": "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "edge": "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
        }
        
        browser_preference = self.settings.get('browser_preference', [])
        for browser in browser_preference:
            if browser in browsers and os.path.exists(browsers[browser]):
                return browsers[browser]
        return None

    def set_auth_completed(self):
        """Marca la autenticación como completada"""
        self._auth_completed = True
        logger.info("Autenticación completada en gestor de cookies")
        
    def get_auth_status(self):
        """Obtiene el estado actual de la autenticación"""
        return self._auth_completed

    def get_browser_cookies(self):
        cookies = []
        browser_preference = self.settings.get('browser_preference', 
            ["chrome", "firefox", "brave", "edge"])
        
        browser_map = {
            "chrome": browser_cookie3.chrome,
            "firefox": browser_cookie3.firefox,
            "brave": browser_cookie3.brave,
            "edge": browser_cookie3.edge
        }
        
        for browser_name in browser_preference:
            if browser_name in browser_map:
                try:
                    browser_cookies = browser_map[browser_name](domain_name="youtube.com")
                    if browser_cookies:
                        cookies.extend(browser_cookies)
                        logger.info(f"Cookies obtenidas de {browser_name}")
                        break  # Usa el primer navegador exitoso
                except Exception as e:
                    logger.debug(f"No se pudieron obtener cookies de {browser_name}: {e}")
        
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
