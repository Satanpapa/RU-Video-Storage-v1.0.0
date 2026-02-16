"""
Metadata - управление метаданными файлов
"""
import json
import struct
from datetime import datetime
from typing import Any


VERSION = "1.0.0"


def create_metadata(
    filename: str,
    file_size: int,
    chunk_size: int,
    encrypted: bool = False,
    **kwargs: Any
) -> dict:
    """
    Создает словарь с метаданными
    
    Args:
        filename: имя оригинального файла
        file_size: размер файла в байтах
        chunk_size: размер чанка
        encrypted: флаг шифрования
        **kwargs: дополнительные параметры
    
    Returns:
        словарь с метаданными
    """
    metadata = {
        'version': VERSION,
        'filename': filename,
        'file_size': file_size,
        'chunk_size': chunk_size,
        'num_chunks': (file_size + chunk_size - 1) // chunk_size,
        'encrypted': encrypted,
        'timestamp': datetime.utcnow().isoformat(),
    }
    
    # Добавляем дополнительные параметры
    metadata.update(kwargs)
    
    return metadata


def serialize_metadata(metadata: dict) -> bytes:
    """
    Сериализует метаданные в байты
    
    Args:
        metadata: словарь с метаданными
    
    Returns:
        сериализованные метаданные
    """
    json_str = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    
    # Добавляем длину в начало для удобства чтения
    length = len(json_bytes)
    return struct.pack('<I', length) + json_bytes


def deserialize_metadata(data: bytes) -> dict:
    """
    Десериализует метаданные из байтов
    
    Args:
        data: сериализованные метаданные
    
    Returns:
        словарь с метаданными
    """
    # Читаем длину
    length = struct.unpack('<I', data[:4])[0]
    
    # Читаем JSON
    json_bytes = data[4:4 + length]
    json_str = json_bytes.decode('utf-8')
    
    metadata = json.loads(json_str)
    
    # Валидация
    required_fields = ['version', 'filename', 'file_size', 'chunk_size', 'encrypted']
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Missing required field in metadata: {field}")
    
    return metadata


def validate_metadata(metadata: dict) -> bool:
    """
    Проверяет валидность метаданных
    
    Args:
        metadata: словарь с метаданными
    
    Returns:
        True если метаданные валидны
    """
    required_fields = {
        'version': str,
        'filename': str,
        'file_size': int,
        'chunk_size': int,
        'encrypted': bool,
    }
    
    for field, expected_type in required_fields.items():
        if field not in metadata:
            return False
        if not isinstance(metadata[field], expected_type):
            return False
    
    # Проверяем разумность значений
    if metadata['file_size'] < 0:
        return False
    if metadata['chunk_size'] <= 0:
        return False
    
    return True


# Тест
if __name__ == '__main__':
    # Создаем тестовые метаданные
    metadata = create_metadata(
        filename="test_document.pdf",
        file_size=1024 * 1024,  # 1 MB
        chunk_size=64 * 1024,   # 64 KB
        encrypted=True,
        custom_field="custom_value"
    )
    
    print("Created metadata:")
    print(json.dumps(metadata, indent=2))
    
    # Сериализация
    serialized = serialize_metadata(metadata)
    print(f"\nSerialized size: {len(serialized)} bytes")
    
    # Десериализация
    deserialized = deserialize_metadata(serialized)
    print("\nDeserialized metadata:")
    print(json.dumps(deserialized, indent=2))
    
    # Проверка
    print(f"\nMetadata matches: {metadata == deserialized}")
    print(f"Metadata is valid: {validate_metadata(deserialized)}")
