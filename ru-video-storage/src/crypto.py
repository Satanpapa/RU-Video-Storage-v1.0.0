"""
Crypto - шифрование и дешифрование данных
"""
import os
import hashlib
from typing import Optional

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Получает ключ шифрования из пароля
    
    Args:
        password: пароль пользователя
        salt: соль для PBKDF2
    
    Returns:
        32-байтовый ключ для AES-256
    """
    return PBKDF2(
        password.encode('utf-8'),
        salt,
        dkLen=32,  # 256 бит для AES-256
        count=100000  # Количество итераций
    )


def encrypt_data(data: bytes, password: str) -> bytes:
    """
    Шифрует данные с использованием AES-256-GCM
    
    Args:
        data: данные для шифрования
        password: пароль
    
    Returns:
        зашифрованные данные с заголовком (salt + nonce + tag + ciphertext)
    """
    # Генерируем случайную соль
    salt = get_random_bytes(16)
    
    # Получаем ключ из пароля
    key = derive_key(password, salt)
    
    # Создаем AES cipher в режиме GCM
    cipher = AES.new(key, AES.MODE_GCM)
    
    # Шифруем данные
    ciphertext, tag = cipher.encrypt_and_digest(data)
    
    # Собираем всё вместе: salt (16) + nonce (16) + tag (16) + ciphertext
    encrypted = salt + cipher.nonce + tag + ciphertext
    
    return encrypted


def decrypt_data(encrypted_data: bytes, password: str) -> bytes:
    """
    Дешифрует данные
    
    Args:
        encrypted_data: зашифрованные данные с заголовком
        password: пароль
    
    Returns:
        расшифрованные данные
    
    Raises:
        ValueError: если пароль неверный или данные повреждены
    """
    # Извлекаем компоненты
    salt = encrypted_data[:16]
    nonce = encrypted_data[16:32]
    tag = encrypted_data[32:48]
    ciphertext = encrypted_data[48:]
    
    # Получаем ключ из пароля
    key = derive_key(password, salt)
    
    # Создаем cipher для дешифрования
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    
    try:
        # Дешифруем и проверяем аутентификацию
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        return plaintext
    except ValueError as e:
        raise ValueError("Decryption failed: wrong password or corrupted data") from e


# Тест
if __name__ == '__main__':
    test_data = b"Hello, World! This is a secret message." * 100
    password = "my_secure_password_123"
    
    print("Original data size:", len(test_data))
    
    # Шифрование
    encrypted = encrypt_data(test_data, password)
    print("Encrypted data size:", len(encrypted))
    
    # Дешифрование с правильным паролем
    try:
        decrypted = decrypt_data(encrypted, password)
        print("Decryption successful!")
        print("Data matches:", decrypted == test_data)
    except ValueError as e:
        print(f"Decryption failed: {e}")
    
    # Попытка дешифрования с неправильным паролем
    try:
        decrypted = decrypt_data(encrypted, "wrong_password")
        print("This shouldn't happen!")
    except ValueError as e:
        print(f"Expected error with wrong password: {e}")
