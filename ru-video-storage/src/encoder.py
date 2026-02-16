"""
Video Encoder - кодирование файлов в видео с использованием FFV1 codec
"""
import os
import struct
import json
import zlib
from typing import Optional, Callable
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

from .fountain import FountainEncoder
from .crypto import encrypt_data
from .metadata import create_metadata, serialize_metadata


class VideoEncoder:
    """Кодирует файлы в lossless видео (FFV1/MKV)"""
    
    # Константы
    CHUNK_SIZE = 64 * 1024  # 64 KB chunks
    VIDEO_WIDTH = 3840  # 4K
    VIDEO_HEIGHT = 2160
    VIDEO_FPS = 30
    REDUNDANCY_FACTOR = 1.3  # 30% избыточности для fountain codes
    
    def __init__(
        self,
        input_file: str,
        output_file: str,
        encryption_password: Optional[str] = None,
        chunk_size: int = CHUNK_SIZE,
        progress_callback: Optional[Callable[[float], None]] = None
    ):
        """
        Args:
            input_file: путь к входному файлу
            output_file: путь к выходному видео (.mkv)
            encryption_password: пароль для шифрования (опционально)
            chunk_size: размер чанка в байтах
            progress_callback: callback для отслеживания прогресса
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.encryption_password = encryption_password
        self.chunk_size = chunk_size
        self.progress_callback = progress_callback
        
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Убедимся, что выходной файл имеет расширение .mkv
        if self.output_file.suffix.lower() != '.mkv':
            self.output_file = self.output_file.with_suffix('.mkv')
    
    def encode(self) -> None:
        """Кодирует файл в видео"""
        print(f"📁 Encoding file: {self.input_file.name}")
        print(f"📊 File size: {self._format_size(self.input_file.stat().st_size)}")
        
        # Читаем файл
        with open(self.input_file, 'rb') as f:
            file_data = f.read()
        
        # Шифруем если нужно
        if self.encryption_password:
            print("🔐 Encrypting data...")
            file_data = encrypt_data(file_data, self.encryption_password)
        
        # Создаем метаданные
        metadata = create_metadata(
            filename=self.input_file.name,
            file_size=len(file_data),
            chunk_size=self.chunk_size,
            encrypted=bool(self.encryption_password)
        )
        metadata_bytes = serialize_metadata(metadata)
        
        # Разбиваем на чанки
        chunks = self._split_into_chunks(file_data)
        print(f"📦 Split into {len(chunks)} chunks")
        
        # Применяем fountain encoding для каждого чанка
        print("🌊 Applying fountain codes...")
        encoded_chunks = []
        for chunk in tqdm(chunks, desc="Fountain encoding"):
            fountain_encoder = FountainEncoder(chunk, redundancy=self.REDUNDANCY_FACTOR)
            encoded_packets = fountain_encoder.encode()
            encoded_chunks.append(encoded_packets)
        
        # Создаем видео
        print("🎬 Creating video...")
        self._create_video(metadata_bytes, encoded_chunks)
        
        print(f"✅ Video created: {self.output_file}")
        print(f"📊 Video size: {self._format_size(self.output_file.stat().st_size)}")
    
    def _split_into_chunks(self, data: bytes) -> list[bytes]:
        """Разбивает данные на чанки"""
        chunks = []
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i:i + self.chunk_size]
            # Добавляем CRC32 для проверки целостности
            crc = zlib.crc32(chunk)
            chunk_with_crc = struct.pack('<I', crc) + chunk
            chunks.append(chunk_with_crc)
        return chunks
    
    def _create_video(self, metadata: bytes, encoded_chunks: list) -> None:
        """Создает видео файл с встроенными данными"""
        # Настройка FFmpeg для FFV1 codec
        fourcc = cv2.VideoWriter_fourcc(*'FFV1')
        video_writer = cv2.VideoWriter(
            str(self.output_file),
            fourcc,
            self.VIDEO_FPS,
            (self.VIDEO_WIDTH, self.VIDEO_HEIGHT),
            isColor=True
        )
        
        if not video_writer.isOpened():
            raise RuntimeError("Failed to open video writer. Make sure FFmpeg is installed.")
        
        try:
            # Кодируем метаданные в первые кадры
            metadata_frames = self._encode_metadata_to_frames(metadata)
            for frame in metadata_frames:
                video_writer.write(frame)
            
            # Кодируем данные
            total_packets = sum(len(packets) for packets in encoded_chunks)
            with tqdm(total=total_packets, desc="Encoding frames") as pbar:
                for chunk_idx, packets in enumerate(encoded_chunks):
                    for packet in packets:
                        frame = self._encode_packet_to_frame(packet, chunk_idx)
                        video_writer.write(frame)
                        pbar.update(1)
                        
                        if self.progress_callback:
                            progress = pbar.n / total_packets
                            self.progress_callback(progress)
        
        finally:
            video_writer.release()
    
    def _encode_metadata_to_frames(self, metadata: bytes) -> list[np.ndarray]:
        """Кодирует метаданные в видео кадры"""
        frames = []
        
        # Первый кадр: размер метаданных
        frame = np.zeros((self.VIDEO_HEIGHT, self.VIDEO_WIDTH, 3), dtype=np.uint8)
        metadata_size = len(metadata)
        
        # Записываем размер в первые пиксели (4 байта = 32 бита)
        size_bytes = struct.pack('<I', metadata_size)
        for i, byte_val in enumerate(size_bytes):
            x = i % self.VIDEO_WIDTH
            y = i // self.VIDEO_WIDTH
            frame[y, x] = [byte_val, byte_val, byte_val]
        
        frames.append(frame)
        
        # Следующие кадры: сами метаданные
        bytes_per_frame = self.VIDEO_WIDTH * self.VIDEO_HEIGHT
        for i in range(0, len(metadata), bytes_per_frame):
            frame = np.zeros((self.VIDEO_HEIGHT, self.VIDEO_WIDTH, 3), dtype=np.uint8)
            chunk = metadata[i:i + bytes_per_frame]
            
            for j, byte_val in enumerate(chunk):
                x = j % self.VIDEO_WIDTH
                y = j // self.VIDEO_WIDTH
                frame[y, x] = [byte_val, byte_val, byte_val]
            
            frames.append(frame)
        
        return frames
    
    def _encode_packet_to_frame(self, packet: bytes, chunk_idx: int) -> np.ndarray:
        """
        Кодирует пакет данных в видео кадр
        Использует все три канала (RGB) для максимальной плотности
        """
        frame = np.zeros((self.VIDEO_HEIGHT, self.VIDEO_WIDTH, 3), dtype=np.uint8)
        
        # Добавляем заголовок с индексом чанка (4 байта)
        header = struct.pack('<I', chunk_idx)
        packet_with_header = header + packet
        
        # Заполняем кадр данными
        pixel_idx = 0
        for byte_val in packet_with_header:
            if pixel_idx >= self.VIDEO_WIDTH * self.VIDEO_HEIGHT * 3:
                break
            
            y = pixel_idx // (self.VIDEO_WIDTH * 3)
            x = (pixel_idx % (self.VIDEO_WIDTH * 3)) // 3
            channel = pixel_idx % 3
            
            frame[y, x, channel] = byte_val
            pixel_idx += 1
        
        return frame
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Форматирует размер в человеко-читаемый вид"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


if __name__ == '__main__':
    # Пример использования
    encoder = VideoEncoder(
        input_file="test_file.txt",
        output_file="output.mkv",
        encryption_password="test123"
    )
    encoder.encode()
