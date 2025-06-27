#include "security.h"
#include <algorithm>
#include <regex>
#include <fstream>
#include <sstream>
#include <cstring>
#include <iomanip>

#ifdef _WIN32
    #include <windows.h>
    #include <wincrypt.h>
#else
    #include <openssl/evp.h>
    #include <openssl/rand.h>
#endif

std::unique_ptr<Security> Security::instance = nullptr;

Security::Security() {
    init_forbidden_lists();
}

Security* Security::getInstance() {
    if (!instance) {
        instance = std::make_unique<Security>();
    }
    return instance.get();
}

void Security::init_forbidden_lists() {
    // Caracteres prohibidos en nombres de archivo
    forbidden_chars = {
        "<", ">", ":", "\"", "|", "?", "*", "/", "\\",
        "\x00", "\x01", "\x02", "\x03", "\x04", "\x05", "\x06", "\x07",
        "\x08", "\x09", "\x0A", "\x0B", "\x0C", "\x0D", "\x0E", "\x0F"
    };
    
    // Rutas prohibidas (Windows)
    forbidden_paths = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    };
}

std::string Security::sanitize_filename(const std::string& filename) {
    if (filename.empty()) {
        return "unnamed_file";
    }
    
    std::string sanitized = filename;
    
    // Remover caracteres prohibidos
    for (const auto& forbidden : forbidden_chars) {
        size_t pos = 0;
        while ((pos = sanitized.find(forbidden, pos)) != std::string::npos) {
            sanitized.replace(pos, forbidden.length(), "_");
            pos += 1;
        }
    }
    
    // Verificar nombres reservados de Windows
    std::string upper_name = sanitized;
    std::transform(upper_name.begin(), upper_name.end(), upper_name.begin(), ::toupper);
    
    for (const auto& forbidden_path : forbidden_paths) {
        if (upper_name == forbidden_path || 
            upper_name.substr(0, forbidden_path.length() + 1) == forbidden_path + ".") {
            sanitized = "_" + sanitized;
            break;
        }
    }
    
    // Remover espacios al inicio y final
    sanitized.erase(0, sanitized.find_first_not_of(" \t\r\n"));
    sanitized.erase(sanitized.find_last_not_of(" \t\r\n") + 1);
    
    // Remover puntos al final (Windows no permite archivos que terminen en punto)
    while (!sanitized.empty() && sanitized.back() == '.') {
        sanitized.pop_back();
    }
    
    // Limitar longitud del nombre
    if (sanitized.length() > 200) {
        sanitized = sanitized.substr(0, 200);
    }
    
    // Si quedó vacío, usar nombre por defecto
    if (sanitized.empty()) {
        sanitized = "unnamed_file";
    }
    
    return sanitized;
}

std::string Security::sanitize_path(const std::string& path) {
    if (path.empty()) {
        return "";
    }
    
    std::string sanitized = path;
    
    // Normalizar separadores de ruta
    std::replace(sanitized.begin(), sanitized.end(), '/', '\\');
    
    // Remover secuencias peligrosas como ../ o ..\
    std::regex dangerous_pattern(R"(\.\.[/\\])");
    sanitized = std::regex_replace(sanitized, dangerous_pattern, "");
    
    // Remover caracteres de control
    sanitized.erase(std::remove_if(sanitized.begin(), sanitized.end(),
        [](char c) { return c >= 0 && c <= 31; }), sanitized.end());
    
    return sanitized;
}

bool Security::validate_url(const std::string& url) {
    if (url.empty() || url.length() > 2048) {
        return false;
    }
    
    // Verificar esquemas permitidos
    std::regex url_pattern(R"(^https?://[^\s<>\"]+$)", std::regex_constants::icase);
    
    if (!std::regex_match(url, url_pattern)) {
        return false;
    }
    
    // Verificar dominios conocidos (YouTube, Twitch, etc.)
    std::regex domain_pattern(
        R"(https?://(?:www\.)?(youtube\.com|youtu\.be|twitch\.tv|tiktok\.com|vm\.tiktok\.com))",
        std::regex_constants::icase
    );
    
    return std::regex_search(url, domain_pattern);
}

bool Security::check_file_integrity(const std::string& filepath) {
    std::ifstream file(filepath, std::ios::binary);
    if (!file.is_open()) {
        return false;
    }
    
    // Verificar que el archivo no esté vacío
    file.seekg(0, std::ios::end);
    std::streampos size = file.tellg();
    
    if (size == 0) {
        return false;
    }
    
    // Verificar tamaño razonable (menos de 10GB)
    if (size > 10737418240LL) {
        return false;
    }
    
    return true;
}

std::string Security::encrypt_data(const std::string& data, const std::string& key) {
    // Implementación básica de cifrado (en producción usar librerías robustas)
    std::string encrypted = data;
    
    for (size_t i = 0; i < encrypted.length(); ++i) {
        encrypted[i] ^= key[i % key.length()];
    }
    
    // Convertir a hexadecimal para safe storage
    std::stringstream ss;
    for (unsigned char c : encrypted) {
        ss << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(c);
    }
    
    return ss.str();
}

std::string Security::decrypt_data(const std::string& encrypted_data, const std::string& key) {
    // Convertir de hexadecimal
    std::string hex_data = encrypted_data;
    std::string binary_data;
    
    for (size_t i = 0; i < hex_data.length(); i += 2) {
        std::string byte_string = hex_data.substr(i, 2);
        char byte = static_cast<char>(std::stoi(byte_string, nullptr, 16));
        binary_data.push_back(byte);
    }
    
    // Descifrar
    std::string decrypted = binary_data;
    for (size_t i = 0; i < decrypted.length(); ++i) {
        decrypted[i] ^= key[i % key.length()];
    }
    
    return decrypted;
}

// Funciones C para exportar a Python
extern "C" {
    EXPORT void sanitize_filename(const char* input, char* output, int max_len) {
        if (!input || !output || max_len <= 0) return;
        
        Security* sec = Security::getInstance();
        std::string result = sec->sanitize_filename(std::string(input));
        
        strncpy(output, result.c_str(), max_len - 1);
        output[max_len - 1] = '\0';
    }
    
    EXPORT void sanitize_path_c(const char* input, char* output, int max_len) {
        if (!input || !output || max_len <= 0) return;
        
        Security* sec = Security::getInstance();
        std::string result = sec->sanitize_path(std::string(input));
        
        strncpy(output, result.c_str(), max_len - 1);
        output[max_len - 1] = '\0';
    }
    
    EXPORT int validate_url_c(const char* url) {
        if (!url) return 0;
        
        Security* sec = Security::getInstance();
        return sec->validate_url(std::string(url)) ? 1 : 0;
    }
    
    EXPORT int check_file_integrity_c(const char* filepath) {
        if (!filepath) return 0;
        
        Security* sec = Security::getInstance();
        return sec->check_file_integrity(std::string(filepath)) ? 1 : 0;
    }
    
    EXPORT void encrypt_data_c(const char* data, const char* key, char* output, int max_len) {
        if (!data || !key || !output || max_len <= 0) return;
        
        Security* sec = Security::getInstance();
        std::string result = sec->encrypt_data(std::string(data), std::string(key));
        
        strncpy(output, result.c_str(), max_len - 1);
        output[max_len - 1] = '\0';
    }
    
    EXPORT void decrypt_data_c(const char* encrypted_data, const char* key, char* output, int max_len) {
        if (!encrypted_data || !key || !output || max_len <= 0) return;
        
        Security* sec = Security::getInstance();
        std::string result = sec->decrypt_data(std::string(encrypted_data), std::string(key));
        
        strncpy(output, result.c_str(), max_len - 1);
        output[max_len - 1] = '\0';
    }
}
