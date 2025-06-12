import ctypes
import os
from src.services.utils import Utils
class AntiTampering:
    def __init__(self, dll_path=None):
        # Determina la ruta del DLL según el contexto de ejecución
        if dll_path is None:
            dll_path = Utils.get_dll_path("anti_tampering.dll")
        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"No se encontró el DLL de AntiTampering en {dll_path}")
        self.dll = ctypes.CDLL(dll_path)
        self.dll.get_secret_salt.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
        self.dll.get_secret_salt.restype = ctypes.c_bool
        self.dll.self_integrity_check.restype = ctypes.c_bool
        self.dll.detect_suspicious_processes.restype = ctypes.c_bool

    def get_secret_salt(self):
        salt = (ctypes.c_ubyte * 16)()
        ok = self.dll.get_secret_salt(salt, 16)
        if not ok:
            raise RuntimeError("No autorizado o entorno inseguro para obtener el salt secreto.")
        return bytes(salt)

    def check_self_integrity(self):
        return self.dll.self_integrity_check()

    def detect_suspicious_processes(self):
        return self.dll.detect_suspicious_processes()

    def is_safe_environment(self):
        if not self.check_self_integrity():
            return False
        if self.detect_suspicious_processes():
            return False
        return True