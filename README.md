# YouTube Downloader

## Descripción
Aplicación de escritorio para descargar videos y audio de YouTube. Incluye conversión a MP3 y permite la descarga de videos con restricciones (por ejemplo, verificación de edad) mediante el uso de cookies.

## Características
- Descarga de videos en diferentes calidades (2160p, 1440p, 1080p, etc.)
- Opción para extraer solo audio (MP3)
- Soporte para videos con restricciones mediante autenticación con cookies
- Interfaz intuitiva y registro de descargas

## Requisitos y Configuración
- Python 3.7 o superior.
- Dependencias listadas en `requirements.txt`.
- Para descargar videos restringidos, exporta las cookies de YouTube en formato Netscape usando una extensión de terceros (por ejemplo, [EditThisCookie](https://www.editthiscookie.com/)) y guarda el archivo (por defecto, `cookies.txt`) en el directorio `Config`.

## Instalación

1. Clonar el repositorio:

git clone https://github.com/tu-usuario/youtube-downloader.git cd youtube-downloader

2. Crear entorno virtual

python -m venv venv source venv/bin/activate 

# En Windows: 

venv\Scripts\activate

3. Instalar dependencias

pip install -r requirements.txt

4. Ejecutar la aplicación:

python -m src.main

Contribuciones
Las contribuciones son bienvenidas. Por favor, lee las guías de contribución.

Licencia
Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para obtener más información
