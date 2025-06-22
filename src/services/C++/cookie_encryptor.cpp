// cookie_encryptor.cpp
// cookie_encryptor.cpp
// DLL para cifrado y descifrado de archivos de cookies usando OpenSSL
// Compilar con:
// set OPENSSL_ROOT=C:\Program Files\OpenSSL-Win64
// cd /d "D:\Escritorio\Carpetas con cosas\Programas\Python\Axolutly\Capeta C para codigo respaldo"
// cl /EHsc /LD cookie_encryptor.cpp /I"%OPENSSL_ROOT%\\include" /link /OUT:cookie_encryptor.dll /LIBPATH:"%OPENSSL_ROOT%\\lib\\VC\\x64\\MTd" libcrypto.lib
// renombrar a encriptor.dll
// Si usas MinGW (g++):
// g++ -shared -o cookie_encryptor.dll -I"%OPENSSL_ROOT%/include" -L"%OPENSSL_ROOT%/lib" -lcrypto -static-libgcc -static-libstdc++ -fPIC cookie_encryptor.cpp
//
// NOTA: Requiere OpenSSL instalado y las rutas configuradas correctamente.
#include <windows.h>
#include <fstream>
#include <vector>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <cstring>

extern "C" {

// Genera una clave y IV aleatorios y los guarda al inicio del archivo cifrado
__declspec(dllexport) bool encrypt_file(const char* input_path, const char* output_path) {
    std::ifstream infile(input_path, std::ios::binary);
    if (!infile) return false;
    std::vector<unsigned char> plaintext((std::istreambuf_iterator<char>(infile)), std::istreambuf_iterator<char>());
    infile.close();
    if (plaintext.empty()) return false;

    unsigned char key[32];
    unsigned char iv[16];
    if (RAND_bytes(key, sizeof(key)) != 1 || RAND_bytes(iv, sizeof(iv)) != 1) return false;

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return false;
    int outlen1 = 0, outlen2 = 0;
    std::vector<unsigned char> ciphertext(plaintext.size() + EVP_MAX_BLOCK_LENGTH);

    bool ok = false;
    do {
        if (1 != EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key, iv)) break;
        if (1 != EVP_EncryptUpdate(ctx, ciphertext.data(), &outlen1, plaintext.data(), (int)plaintext.size())) break;
        if (1 != EVP_EncryptFinal_ex(ctx, ciphertext.data() + outlen1, &outlen2)) break;
        std::ofstream outfile(output_path, std::ios::binary);
        if (!outfile) break;
        outfile.write((char*)key, sizeof(key));
        outfile.write((char*)iv, sizeof(iv));
        outfile.write((char*)ciphertext.data(), outlen1 + outlen2);
        outfile.close();
        ok = true;
    } while (0);
    EVP_CIPHER_CTX_free(ctx);
    return ok;
}

// Lee la clave y IV del inicio del archivo cifrado
__declspec(dllexport) bool decrypt_file(const char* input_path, const char* output_path) {
    std::ifstream infile(input_path, std::ios::binary);
    if (!infile) return false;
    unsigned char key[32];
    unsigned char iv[16];
    infile.read((char*)key, sizeof(key));
    infile.read((char*)iv, sizeof(iv));
    std::vector<unsigned char> ciphertext((std::istreambuf_iterator<char>(infile)), std::istreambuf_iterator<char>());
    infile.close();
    if (ciphertext.empty()) return false;

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return false;
    int outlen1 = 0, outlen2 = 0;
    std::vector<unsigned char> plaintext(ciphertext.size() + EVP_MAX_BLOCK_LENGTH);
    bool ok = false;
    do {
        if (1 != EVP_DecryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key, iv)) break;
        if (1 != EVP_DecryptUpdate(ctx, plaintext.data(), &outlen1, ciphertext.data(), (int)ciphertext.size())) break;
        if (1 != EVP_DecryptFinal_ex(ctx, plaintext.data() + outlen1, &outlen2)) break;
        std::ofstream outfile(output_path, std::ios::binary);
        if (!outfile) break;
        outfile.write((char*)plaintext.data(), outlen1 + outlen2);
        outfile.close();
        ok = true;
    } while (0);
    EVP_CIPHER_CTX_free(ctx);
    return ok;
}
}