"""
Примеры использования RU Video Storage
"""
import os
from pathlib import Path

from src import VideoEncoder, VideoDecoder, VKUploader, RuTubeUploader


def example_1_basic_encoding():
    """Пример 1: Базовое кодирование и декодирование"""
    print("=" * 60)
    print("Пример 1: Базовое кодирование без шифрования")
    print("=" * 60)
    
    # Создаем тестовый файл
    test_file = "test_data.txt"
    with open(test_file, 'w') as f:
        f.write("Hello, RU Video Storage!\n" * 100)
    
    # Кодируем
    encoder = VideoEncoder(
        input_file=test_file,
        output_file="output.mkv"
    )
    encoder.encode()
    
    # Декодируем
    decoder = VideoDecoder(
        input_file="output.mkv",
        output_file="decoded.txt"
    )
    decoder.decode()
    
    # Проверяем
    with open(test_file, 'rb') as f1, open("decoded.txt", 'rb') as f2:
        original = f1.read()
        decoded = f2.read()
        print(f"✅ Files match: {original == decoded}")
    
    # Cleanup
    Path(test_file).unlink()
    Path("output.mkv").unlink()
    Path("decoded.txt").unlink()


def example_2_encrypted_encoding():
    """Пример 2: Кодирование с шифрованием"""
    print("\n" + "=" * 60)
    print("Пример 2: Кодирование с шифрованием")
    print("=" * 60)
    
    # Создаем тестовый файл
    test_file = "secret_data.txt"
    with open(test_file, 'w') as f:
        f.write("This is a secret message!\n" * 50)
    
    password = "super_secret_password_123"
    
    # Кодируем с шифрованием
    encoder = VideoEncoder(
        input_file=test_file,
        output_file="encrypted.mkv",
        encryption_password=password
    )
    encoder.encode()
    
    # Декодируем с правильным паролем
    decoder = VideoDecoder(
        input_file="encrypted.mkv",
        output_file="decrypted.txt",
        decryption_password=password
    )
    decoder.decode()
    
    # Проверяем
    with open(test_file, 'rb') as f1, open("decrypted.txt", 'rb') as f2:
        original = f1.read()
        decoded = f2.read()
        print(f"✅ Files match: {original == decoded}")
    
    # Попытка декодирования с неправильным паролем
    try:
        decoder_wrong = VideoDecoder(
            input_file="encrypted.mkv",
            output_file="should_fail.txt",
            decryption_password="wrong_password"
        )
        decoder_wrong.decode()
        print("❌ This shouldn't succeed!")
    except ValueError as e:
        print(f"✅ Correctly failed with wrong password: {e}")
    
    # Cleanup
    Path(test_file).unlink()
    Path("encrypted.mkv").unlink()
    Path("decrypted.txt").unlink()


def example_3_vk_upload():
    """Пример 3: Загрузка на VK Видео"""
    print("\n" + "=" * 60)
    print("Пример 3: Загрузка на VK Видео")
    print("=" * 60)
    
    # ВАЖНО: Замените на ваш токен
    VK_TOKEN = os.getenv('VK_ACCESS_TOKEN', 'your_token_here')
    
    if VK_TOKEN == 'your_token_here':
        print("⚠️  Установите VK_ACCESS_TOKEN в переменные окружения")
        return
    
    # Создаем и кодируем файл
    test_file = "vk_test.txt"
    with open(test_file, 'w') as f:
        f.write("Test file for VK upload\n" * 100)
    
    encoder = VideoEncoder(
        input_file=test_file,
        output_file="vk_video.mkv",
        encryption_password="test123"
    )
    encoder.encode()
    
    # Загружаем на VK
    uploader = VKUploader(access_token=VK_TOKEN)
    
    try:
        result = uploader.upload(
            video_path="vk_video.mkv",
            title="Test Storage Video",
            description="Encrypted file storage test",
            is_private=True
        )
        
        print(f"✅ Uploaded to VK: {result['url']}")
        print(f"Video ID: {result['video_id']}")
        
        # Можно скачать обратно
        # downloaded = uploader.download(
        #     owner_id=result['owner_id'],
        #     video_id=result['video_id'],
        #     output_path="downloaded.mkv"
        # )
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
    
    # Cleanup
    Path(test_file).unlink()
    Path("vk_video.mkv").unlink()


def example_4_rutube_upload():
    """Пример 4: Загрузка на RuTube"""
    print("\n" + "=" * 60)
    print("Пример 4: Загрузка на RuTube")
    print("=" * 60)
    
    # ВАЖНО: Замените на ваш токен
    RUTUBE_TOKEN = os.getenv('RUTUBE_ACCESS_TOKEN', 'your_token_here')
    
    if RUTUBE_TOKEN == 'your_token_here':
        print("⚠️  Установите RUTUBE_ACCESS_TOKEN в переменные окружения")
        return
    
    # Создаем и кодируем файл
    test_file = "rutube_test.txt"
    with open(test_file, 'w') as f:
        f.write("Test file for RuTube upload\n" * 100)
    
    encoder = VideoEncoder(
        input_file=test_file,
        output_file="rutube_video.mkv",
        encryption_password="test456"
    )
    encoder.encode()
    
    # Загружаем на RuTube
    uploader = RuTubeUploader(access_token=RUTUBE_TOKEN)
    
    try:
        result = uploader.upload(
            video_path="rutube_video.mkv",
            title="Test Storage Video",
            description="Encrypted file storage test",
            is_hidden=True,
            tags=["storage", "test"]
        )
        
        print(f"✅ Uploaded to RuTube: {result['url']}")
        print(f"Video ID: {result['video_id']}")
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
    
    # Cleanup
    Path(test_file).unlink()
    Path("rutube_video.mkv").unlink()


def example_5_large_file():
    """Пример 5: Кодирование большого файла"""
    print("\n" + "=" * 60)
    print("Пример 5: Кодирование большого файла (10MB)")
    print("=" * 60)
    
    # Создаем файл 10MB
    test_file = "large_file.bin"
    size_mb = 10
    
    print(f"Creating {size_mb}MB file...")
    with open(test_file, 'wb') as f:
        # Записываем случайные данные
        import random
        chunk = bytes([random.randint(0, 255) for _ in range(1024 * 1024)])
        for _ in range(size_mb):
            f.write(chunk)
    
    # Кодируем
    encoder = VideoEncoder(
        input_file=test_file,
        output_file="large_video.mkv",
        encryption_password="large123",
        chunk_size=128 * 1024  # Увеличенный chunk size для больших файлов
    )
    encoder.encode()
    
    # Декодируем
    decoder = VideoDecoder(
        input_file="large_video.mkv",
        output_file="large_decoded.bin",
        decryption_password="large123"
    )
    decoder.decode()
    
    # Проверяем
    import hashlib
    
    with open(test_file, 'rb') as f:
        original_hash = hashlib.sha256(f.read()).hexdigest()
    
    with open("large_decoded.bin", 'rb') as f:
        decoded_hash = hashlib.sha256(f.read()).hexdigest()
    
    print(f"Original hash:  {original_hash}")
    print(f"Decoded hash:   {decoded_hash}")
    print(f"✅ Hashes match: {original_hash == decoded_hash}")
    
    # Cleanup
    Path(test_file).unlink()
    Path("large_video.mkv").unlink()
    Path("large_decoded.bin").unlink()


def main():
    """Запуск всех примеров"""
    print("\n" + "=" * 60)
    print("RU Video Storage - Примеры использования")
    print("=" * 60 + "\n")
    
    # Базовые примеры
    example_1_basic_encoding()
    example_2_encrypted_encoding()
    
    # Примеры с загрузкой (требуют токены)
    # example_3_vk_upload()
    # example_4_rutube_upload()
    
    # Продвинутые примеры
    example_5_large_file()
    
    print("\n" + "=" * 60)
    print("✅ Все примеры выполнены успешно!")
    print("=" * 60)


if __name__ == '__main__':
    main()
