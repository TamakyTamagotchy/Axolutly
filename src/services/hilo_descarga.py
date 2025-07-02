"""
Ejemplo de uso del hilo de descarga (DownloadThread) de Axolutly
Este archivo es solo demostrativo y no contiene la lógica interna del programa.
"""

from src.services.hilo_descarga import DownloadThread

# Parámetros de ejemplo
url = "https://www.youtube.com/watch?v=XXXXXXXXXXX"
calidad = 1080
solo_audio = False
carpeta_salida = "./descargas"

def on_progreso(porcentaje):
    print(f"Progreso simulado: {porcentaje}%")

def on_finalizado(ruta):
    print(f"Descarga simulada finalizada: {ruta}")

def on_error(msg):
    print(f"Error simulado: {msg}")

if __name__ == "__main__":
    hilo = DownloadThread(url, calidad, solo_audio, carpeta_salida)
    hilo.progress.connect(on_progreso)
    hilo.finished.connect(on_finalizado)
    hilo.error.connect(on_error)
    print("Hilo de descarga creado (solo ejemplo, no descarga real)")
    # hilo.start()  # No se ejecuta realmente en el ejemplo
