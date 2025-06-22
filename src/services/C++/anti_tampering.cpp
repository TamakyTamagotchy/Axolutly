// anti_tampering.cpp
// DLL para protección anti-tampering y gestión de secretos
// Compilar con:
// set OPENSSL_ROOT=C:\Program Files\OpenSSL-Win64
// cd /d "D:\Escritorio\Carpetas con cosas\Programas\Python\Axolutly\cpp_source"
// cl /EHsc /LD anti_tampering.cpp /I"%OPENSSL_ROOT%\include" /link /OUT:anti_tampering.dll /LIBPATH:"%OPENSSL_ROOT%\lib\VC\x64\MTd" libcrypto.lib advapi32.lib

#include <windows.h>
#include <string>
#include <tlhelp32.h>
#include <psapi.h>
#include <cstring>
#include <fstream>
#include <openssl/sha.h>
#include <vector>

// Salt secreto embebido (ejemplo, cambia por uno generado aleatoriamente)
static const unsigned char SECRET_SALT[16] = {0xA1, 0xB2, 0xC3, 0xD4, 0xE5, 0xF6, 0x17, 0x28, 0x39, 0x4A, 0x5B, 0x6C, 0x7D, 0x8E, 0x9F, 0x10};

extern "C"
{

    // Devuelve el salt secreto solo si el proceso es autorizado y no hay depurador
    __declspec(dllexport) bool get_secret_salt(unsigned char *out, int outlen)
    {
        if (outlen < 16)
            return false;
        // Comprobar proceso autorizado
        char processPath[MAX_PATH] = {0};
        if (!GetModuleFileNameA(NULL, processPath, MAX_PATH))
            return false;
        std::string exe(processPath);
        // Cambia "Axolutly.exe" por el nombre real de tu ejecutable
        if (exe.find("Axolutly") == std::string::npos)
            return false;
        // Comprobar depurador
        if (IsDebuggerPresent())
            return false;
        memcpy(out, SECRET_SALT, 16);
        return true;
    }

    // Verifica la integridad de un archivo (SHA256 simple, solo para ejemplo)
    __declspec(dllexport) bool verify_file_integrity(const char *file_path, const char *expected_hash_hex)
    {
        std::ifstream file(file_path, std::ios::binary);
        if (!file.is_open())
            return false;
        SHA256_CTX ctx;
        SHA256_Init(&ctx);
        char buf[4096];
        while (file.good())
        {
            file.read(buf, sizeof(buf));
            std::streamsize n = file.gcount();
            if (n > 0)
                SHA256_Update(&ctx, buf, n);
        }
        file.close();
        unsigned char hash[SHA256_DIGEST_LENGTH];
        SHA256_Final(hash, &ctx);
        char hash_hex[SHA256_DIGEST_LENGTH * 2 + 1];
        for (int i = 0; i < SHA256_DIGEST_LENGTH; ++i)
            sprintf(hash_hex + i * 2, "%02x", hash[i]);
        hash_hex[SHA256_DIGEST_LENGTH * 2] = 0;
        return strncmp(hash_hex, expected_hash_hex, SHA256_DIGEST_LENGTH * 2) == 0;
    }

    // Detecta si la DLL ha sido modificada (checksum propio)
    __declspec(dllexport) bool self_integrity_check()
    {
        char dll_path[MAX_PATH] = {0};
        HMODULE hModule = NULL;
        if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)&self_integrity_check, &hModule))
            return false;
        GetModuleFileNameA(hModule, dll_path, MAX_PATH);
        std::ifstream file(dll_path, std::ios::binary);
        if (!file.is_open())
            return false;
        std::vector<unsigned char> data((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
        file.close();
        if (data.empty())
            return false;
        unsigned char hash[SHA256_DIGEST_LENGTH];
        SHA256_CTX ctx;
        SHA256_Init(&ctx);
        SHA256_Update(&ctx, data.data(), data.size());
        SHA256_Final(hash, &ctx);
        // Aquí deberías comparar con un hash esperado HARDCODEADO (cámbialo tras cada build)
        const char *expected_hash = "FF6A733E5A0518676CE5ABF82E0F4AC41B8E6D083F51CB1D32B86C959BF53F91";
        char hash_hex[SHA256_DIGEST_LENGTH * 2 + 1];
        for (int i = 0; i < SHA256_DIGEST_LENGTH; ++i)
            sprintf(hash_hex + i * 2, "%02x", hash[i]);
        hash_hex[SHA256_DIGEST_LENGTH * 2] = 0;
        return strncmp(hash_hex, expected_hash, SHA256_DIGEST_LENGTH * 2) == 0;
    }

    // Detecta si hay procesos sospechosos (anti-debug/anti-inject)
    __declspec(dllexport) bool detect_suspicious_processes()
    {
        // Ejemplo: buscar procesos comunes de ingeniería inversa
        const char *suspicious[] = {"ollydbg.exe", "x64dbg.exe", "ida.exe", "ida64.exe", "cheatengine.exe", "scylla.exe", "procexp.exe"};
        DWORD aProcesses[1024], cbNeeded, cProcesses;
        if (!EnumProcesses(aProcesses, sizeof(aProcesses), &cbNeeded))
            return false;
        cProcesses = cbNeeded / sizeof(DWORD);
        for (unsigned int i = 0; i < cProcesses; i++)
        {
            if (aProcesses[i] != 0)
            {
                HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, aProcesses[i]);
                if (hProcess)
                {
                    char szProcessName[MAX_PATH] = "<unknown>";
                    HMODULE hMod;
                    DWORD cbNeeded2;
                    if (EnumProcessModules(hProcess, &hMod, sizeof(hMod), &cbNeeded2))
                    {
                        GetModuleBaseNameA(hProcess, hMod, szProcessName, sizeof(szProcessName) / sizeof(char));
                        for (int j = 0; j < sizeof(suspicious) / sizeof(suspicious[0]); ++j)
                        {
                            if (_stricmp(szProcessName, suspicious[j]) == 0)
                            {
                                CloseHandle(hProcess);
                                return true;
                            }
                        }
                    }
                    CloseHandle(hProcess);
                }
            }
        }
        return false;
    }
}