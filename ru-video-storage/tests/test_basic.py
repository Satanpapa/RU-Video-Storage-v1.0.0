"""
Простые тесты для RU Video Storage
"""
import pytest
from pathlib import Path
import tempfile
import os

from src.encoder import VideoEncoder
from src.decoder import VideoDecoder
from src.metadata import create_metadata, serialize_metadata, deserialize_metadata
from src.crypto import encrypt_data, decrypt_data


class TestMetadata:
    """Тесты для метаданных"""
    
    def test_create_metadata(self):
        metadata = create_metadata(
            filename="test.txt",
            file_size=1024,
            chunk_size=64,
            encrypted=True
        )
        
        assert metadata['filename'] == "test.txt"
        assert metadata['file_size'] == 1024
        assert metadata['chunk_size'] == 64
        assert metadata['encrypted'] is True
        assert 'version' in metadata
    
    def test_serialize_deserialize(self):
        original = create_metadata(
            filename="test.pdf",
            file_size=2048,
            chunk_size=128,
            encrypted=False
        )
        
        serialized = serialize_metadata(original)
        deserialized = deserialize_metadata(serialized)
        
        assert original == deserialized


class TestCrypto:
    """Тесты для шифрования"""
    
    def test_encrypt_decrypt(self):
        data = b"Hello, World!" * 100
        password = "test_password_123"
        
        encrypted = encrypt_data(data, password)
        decrypted = decrypt_data(encrypted, password)
        
        assert decrypted == data
    
    def test_wrong_password(self):
        data = b"Secret message"
        password = "correct_password"
        wrong_password = "wrong_password"
        
        encrypted = encrypt_data(data, password)
        
        with pytest.raises(ValueError):
            decrypt_data(encrypted, wrong_password)


class TestEncoderDecoder:
    """Тесты для кодирования и декодирования"""
    
    def test_encode_decode_simple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Создаем тестовый файл
            input_file = tmpdir / "input.txt"
            input_file.write_text("Test data " * 100)
            
            video_file = tmpdir / "video.mkv"
            output_file = tmpdir / "output.txt"
            
            # Кодируем
            encoder = VideoEncoder(
                input_file=str(input_file),
                output_file=str(video_file)
            )
            encoder.encode()
            
            assert video_file.exists()
            
            # Декодируем
            decoder = VideoDecoder(
                input_file=str(video_file),
                output_file=str(output_file)
            )
            decoder.decode()
            
            assert output_file.exists()
            
            # Проверяем
            original = input_file.read_bytes()
            decoded = output_file.read_bytes()
            
            assert original == decoded
    
    def test_encode_decode_encrypted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Создаем тестовый файл
            input_file = tmpdir / "secret.txt"
            input_file.write_text("Secret data " * 50)
            
            video_file = tmpdir / "encrypted.mkv"
            output_file = tmpdir / "decrypted.txt"
            
            password = "super_secret_123"
            
            # Кодируем с шифрованием
            encoder = VideoEncoder(
                input_file=str(input_file),
                output_file=str(video_file),
                encryption_password=password
            )
            encoder.encode()
            
            # Декодируем
            decoder = VideoDecoder(
                input_file=str(video_file),
                output_file=str(output_file),
                decryption_password=password
            )
            decoder.decode()
            
            # Проверяем
            original = input_file.read_bytes()
            decoded = output_file.read_bytes()
            
            assert original == decoded


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
