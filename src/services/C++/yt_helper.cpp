// yt_helper.cpp
// DLL para extracción de ID de videos de YouTube
// Compilar con:
// cd /d "D:\Escritorio\Carpetas con cosas\Programas\Python\Axolutly\Capeta C para codigo respaldo"
// cl /EHsc /LD yt_helper.cpp /link /OUT:yt_helper.dll
// renombrar a quest.dll
// Si necesitas soporte para C++17 o superior, agrega: /std:c++17
// Si usas MinGW (g++):
// g++ -shared -o yt_helper.dll -static-libgcc -static-libstdc++ -fPIC yt_helper.cpp
//
// Para usar con Python vía ctypes, asegúrate de exportar las funciones con extern "C"
//
// NOTA: No requiere dependencias externas, solo Windows y el compilador adecuado.

#include <windows.h>
#include <string>
#include <regex>
#include <cstring>

extern "C" {

// Eliminación de funciones de validación de URLs
// Se mantiene solo el código necesario para otras tareas

__declspec(dllexport) bool extract_video_id(const char* url, char* out_id, int out_size) {
    if (!url || !out_id || out_size < 12) return false;
    const char* patterns[] = {"v=", "youtu.be/", "shorts/"};
    for (const char* pattern : patterns) {
        const char* pos = strstr(url, pattern);
        if (pos) {
            pos += strlen(pattern);
            int j = 0;
            while (j < 11 && pos[j] && isalnum(pos[j]) || pos[j] == '-' || pos[j] == '_') {
                out_id[j] = pos[j];
                ++j;
            }
            if (j == 11) {
                out_id[11] = '\0';
                return true;
            }
        }
    }
    return false;
}

}
