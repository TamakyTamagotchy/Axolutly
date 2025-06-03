import ctypes
import os

class AntiTampering:

    def __init__(self, dll_path=None):
        if dll_path is None:
            dll_path = os.path.join(os.path.dirname(__file__), 'anti_tampering.dll')
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
