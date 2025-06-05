import sys
import ctypes
import os
class AntiTampering:
    # Permite desactivar la protección para desarrollo
    DISABLE_ANTITAMPERING = True  # Cambia a True para desactivar la protección se incluye en lo proximo a borrar
    def __init__(self, dll_path=None):
        """Aqui comienza el sistema de anti-tampering para desactivarlo borrar cuando se exporte."""
        if self.DISABLE_ANTITAMPERING:
            self._disabled = True
            return
        self._disabled = False
        """Aqui termina el sistema de anti-tampering para desactivarlo borrar cuando se exporte."""        
        # Determina la ruta del DLL según el contexto de ejecución
        if dll_path is None:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
                dll_path = os.path.join(base_dir, 'lib', 'src', 'services', 'anti_tampering.dll')
            else:
                dll_path = os.path.join(os.path.dirname(__file__), 'anti_tampering.dll')
            # Ruta alternativa para la carpeta 'service' si es necesario
            if not os.path.exists(dll_path):
                alt_path = dll_path.replace(os.path.join('services', ''), os.path.join('service', ''))
                if os.path.exists(alt_path):
                    dll_path = alt_path
        # Verificar existencia
        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"No se encontró el DLL de AntiTampering en {dll_path}")
        self.dll = ctypes.CDLL(dll_path)
        self.dll.get_secret_salt.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
        self.dll.get_secret_salt.restype = ctypes.c_bool
        self.dll.self_integrity_check.restype = ctypes.c_bool
        self.dll.detect_suspicious_processes.restype = ctypes.c_bool

    def get_secret_salt(self):
        if self._disabled: #eliminar
            return b'\x00'*16 #eliminar
        salt = (ctypes.c_ubyte * 16)()
        ok = self.dll.get_secret_salt(salt, 16)
        if not ok:
            raise RuntimeError("No autorizado o entorno inseguro para obtener el salt secreto.")
        return bytes(salt)

    def check_self_integrity(self):
        if self._disabled: #eliminar
            return True #eliminar
        return self.dll.self_integrity_check()

    def detect_suspicious_processes(self):
        if self._disabled: #eliminar
            return False #eliminar
        return self.dll.detect_suspicious_processes()

    def is_safe_environment(self):
        if not self.check_self_integrity():
            return False
        if self.detect_suspicious_processes():
            return False
        return True