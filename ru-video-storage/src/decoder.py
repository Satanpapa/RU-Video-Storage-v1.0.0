"""
Video Decoder - декодирование видео обратно в файлы
"""
import struct
import zlib
from typing import Optional, Callable
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

from .fountain import FountainDecoder
from .crypto import decrypt_data
from .metadata import deserialize_metadata


class VideoDecoder:
    """Декодирует видео обратно в оригинальные файлы"""
    
    def __init__(
        self,
        input_file: str,
        output_file: str,
        decryption_password: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ):
        """
        Args:
            input_file: путь к входному видео (.mkv)
            output_file: путь к выходному файлу
            decryption_password: пароль для дешифрования (если был зашифрован)
            progress_callback: callback для отслеживания прогресса
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.decryption_password = decryption_password
        self.progress_callback = progress_callback
        
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input video not found: {input_file}")
    
    def decode(self) -> None:
        """Декодирует видео в файл"""
        print(f"🎬 Decoding video: {self.input_file.name}")
        
        # Открываем видео
        video_capture = cv2.VideoCapture(str(self.input_file))
        
        if not video_capture.isOpened():
            raise RuntimeError(f"Failed to open video: {self.input_file}")
        
        try:
            # Читаем метаданные
            print("📋 Reading metadata...")
            metadata = self._read_metadata(video_capture)
            
            print(f"📁 Original filename: {metadata['filename']}")
            print(f"📊 Original size: {self._format_size(metadata['file_size'])}")
            print(f"🔐 Encrypted: {metadata['encrypted']}")
            
            if metadata['encrypted'] and not self.decryption_password:
                raise ValueError("Video is encrypted but no password provided")
            
            # Читаем и декодируем пакеты
            print("📦 Reading encoded packets...")
            chunks_data = self._read_packets(video_capture, metadata)
            
            # Применяем fountain decoding
            print("🌊 Applying fountain decoding...")
            decoded_chunks = []
            for chunk_packets in tqdm(chunks_data, desc="Fountain decoding"):
                decoder = FountainDecoder(len(chunk_packets[0]) - 4)  # -4 для chunk_idx header
                for packet in chunk_packets:
                    decoder.add_packet(packet[4:])  # Убираем chunk_idx header
                
                decoded_chunk = decoder.decode()
                if decoded_chunk is None:
                    raise RuntimeError("Failed to decode chunk - insufficient packets")
                
                decoded_chunks.append(decoded_chunk)
            
            # Собираем данные
            print("🔧 Reconstructing file...")
            file_data = self._reconstruct_file(decoded_chunks, metadata)
            
            # Дешифруем если нужно
            if metadata['encrypted']:
                print("🔓 Decrypting data...")
                file_data = decrypt_data(file_data, self.decryption_password)
            
            # Записываем файл
            with open(self.output_file, 'wb') as f:
                f.write(file_data)
            
            print(f"✅ File decoded: {self.output_file}")
            print(f"📊 Output size: {self._format_size(len(file_data))}")
        
        finally:
            video_capture.release()
    
    def _read_metadata(self, video_capture: cv2.VideoCapture) -> dict:
        """Читает метаданные из первых кадров видео"""
        # Читаем первый кадр для получения размера метаданных
        ret, frame = video_capture.read()
        if not ret:
            raise RuntimeError("Failed to read metadata size frame")
        
        # Извлекаем размер метаданных из первых 4 байтов
        size_bytes = bytes([frame[0, i, 0] for i in range(4)])
        metadata_size = struct.unpack('<I', size_bytes)[0]
        
        # Читаем метаданные
        metadata_bytes = bytearray()
        bytes_per_frame = frame.shape[0] * frame.shape[1]
        
        while len(metadata_bytes) < metadata_size:
            ret, frame = video_capture.read()
            if not ret:
                raise RuntimeError("Failed to read metadata frames")
            
            # Извлекаем байты из кадра (используем только R канал для простоты)
            frame_bytes = frame[:, :, 0].flatten()
            metadata_bytes.extend(frame_bytes[:metadata_size - len(metadata_bytes)])
        
        return deserialize_metadata(bytes(metadata_bytes))
    
    def _read_packets(
        self,
        video_capture: cv2.VideoCapture,
        metadata: dict
    ) -> list[list[bytes]]:
        """Читает пакеты из видео кадров"""
        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        current_frame = int(video_capture.get(cv2.CAP_PROP_POS_FRAMES))
        remaining_frames = total_frames - current_frame
        
        # Группируем пакеты по чанкам
        chunks_packets = {}
        
        with tqdm(total=remaining_frames, desc="Reading frames") as pbar:
            while True:
                ret, frame = video_capture.read()
                if not ret:
                    break
                
                packet = self._decode_frame_to_packet(frame)
                
                # Извлекаем индекс чанка из заголовка
                chunk_idx = struct.unpack('<I', packet[:4])[0]
                
                if chunk_idx not in chunks_packets:
                    chunks_packets[chunk_idx] = []
                
                chunks_packets[chunk_idx].append(packet)
                
                pbar.update(1)
                
                if self.progress_callback:
                    progress = pbar.n / remaining_frames
                    self.progress_callback(progress)
        
        # Преобразуем в отсортированный список
        max_chunk_idx = max(chunks_packets.keys())
        result = []
        for i in range(max_chunk_idx + 1):
            if i in chunks_packets:
                result.append(chunks_packets[i])
            else:
                raise RuntimeError(f"Missing chunk {i}")
        
        return result
    
    def _decode_frame_to_packet(self, frame: np.ndarray) -> bytes:
        """Декодирует видео кадр в пакет данных"""
        # Извлекаем данные из всех трех каналов
        packet_data = bytearray()
        
        height, width, _ = frame.shape
        
        for y in range(height):
            for x in range(width):
                for channel in range(3):
                    byte_val = frame[y, x, channel]
                    packet_data.append(byte_val)
        
        # Убираем trailing zeros (padding)
        # Находим последний ненулевой байт
        last_nonzero = len(packet_data) - 1
        while last_nonzero >= 0 and packet_data[last_nonzero] == 0:
            last_nonzero -= 1
        
        return bytes(packet_data[:last_nonzero + 1])
    
    def _reconstruct_file(self, chunks: list[bytes], metadata: dict) -> bytes:
        """Реконструирует файл из чанков с проверкой CRC"""
        file_data = bytearray()
        
        for i, chunk_with_crc in enumerate(chunks):
            # Извлекаем CRC и данные
            crc_stored = struct.unpack('<I', chunk_with_crc[:4])[0]
            chunk_data = chunk_with_crc[4:]
            
            # Проверяем CRC
            crc_computed = zlib.crc32(chunk_data)
            if crc_stored != crc_computed:
                raise RuntimeError(f"CRC mismatch in chunk {i}")
            
            file_data.extend(chunk_data)
        
        # Обрезаем до оригинального размера
        return bytes(file_data[:metadata['file_size']])
    
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
    decoder = VideoDecoder(
        input_file="output.mkv",
        output_file="decoded_file.txt",
        decryption_password="test123"
    )
    decoder.decode()
