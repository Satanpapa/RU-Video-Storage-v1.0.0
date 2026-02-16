"""
Fountain Codes - реализация fountain кодов для избыточности данных

Это упрощенная реализация, имитирующая функциональность Wirehair.
Для продакшн использования рекомендуется настоящая библиотека Wirehair.
"""
import random
import struct
from typing import Optional


class FountainEncoder:
    """
    Fountain encoder - генерирует избыточные пакеты из исходных данных
    """
    
    def __init__(self, data: bytes, redundancy: float = 1.3):
        """
        Args:
            data: исходные данные для кодирования
            redundancy: коэффициент избыточности (1.3 = 30% дополнительных пакетов)
        """
        self.data = data
        self.redundancy = redundancy
        self.packet_size = 1024  # 1KB пакеты
        
        # Разбиваем данные на блоки
        self.blocks = self._split_into_blocks()
        self.num_blocks = len(self.blocks)
    
    def _split_into_blocks(self) -> list[bytes]:
        """Разбивает данные на блоки фиксированного размера"""
        blocks = []
        for i in range(0, len(self.data), self.packet_size):
            block = self.data[i:i + self.packet_size]
            # Padding если блок меньше packet_size
            if len(block) < self.packet_size:
                block += b'\x00' * (self.packet_size - len(block))
            blocks.append(block)
        return blocks
    
    def encode(self) -> list[bytes]:
        """
        Генерирует закодированные пакеты с избыточностью
        
        Returns:
            список закодированных пакетов
        """
        num_packets = int(self.num_blocks * self.redundancy)
        packets = []
        
        for packet_id in range(num_packets):
            # Генерируем seed для этого пакета
            seed = packet_id
            
            # Выбираем случайные блоки для XOR на основе seed
            selected_blocks = self._select_blocks(seed)
            
            # XOR выбранных блоков
            packet_data = self._xor_blocks(selected_blocks)
            
            # Добавляем заголовок с packet_id и информацией о выбранных блоках
            header = struct.pack('<I', packet_id) + struct.pack('<H', len(selected_blocks))
            header += b''.join(struct.pack('<H', idx) for idx in selected_blocks)
            
            packets.append(header + packet_data)
        
        return packets
    
    def _select_blocks(self, seed: int) -> list[int]:
        """
        Выбирает случайные блоки на основе seed
        Использует детерминированный генератор для воспроизводимости
        """
        rng = random.Random(seed)
        
        # Выбираем от 1 до min(3, num_blocks) блоков
        num_selected = rng.randint(1, min(3, self.num_blocks))
        
        # Выбираем случайные индексы без повторений
        selected = rng.sample(range(self.num_blocks), num_selected)
        return sorted(selected)
    
    def _xor_blocks(self, block_indices: list[int]) -> bytes:
        """XOR выбранных блоков"""
        if not block_indices:
            return b'\x00' * self.packet_size
        
        result = bytearray(self.blocks[block_indices[0]])
        
        for idx in block_indices[1:]:
            block = self.blocks[idx]
            for i in range(len(result)):
                result[i] ^= block[i]
        
        return bytes(result)


class FountainDecoder:
    """
    Fountain decoder - восстанавливает исходные данные из пакетов
    """
    
    def __init__(self, block_size: int):
        """
        Args:
            block_size: размер блока данных
        """
        self.block_size = block_size
        self.packets = []  # Полученные пакеты
        self.decoded_blocks = {}  # Декодированные блоки
    
    def add_packet(self, packet: bytes) -> None:
        """Добавляет полученный пакет"""
        self.packets.append(packet)
    
    def decode(self) -> Optional[bytes]:
        """
        Декодирует данные из накопленных пакетов
        
        Returns:
            декодированные данные или None если недостаточно пакетов
        """
        # Парсим все пакеты
        parsed_packets = []
        max_block_idx = 0
        
        for packet in self.packets:
            header_size = 6  # packet_id (4) + num_selected (2)
            packet_id = struct.unpack('<I', packet[:4])[0]
            num_selected = struct.unpack('<H', packet[4:6])[0]
            
            # Читаем индексы выбранных блоков
            indices_start = 6
            indices_end = 6 + (num_selected * 2)
            selected_blocks = []
            
            for i in range(num_selected):
                idx_offset = indices_start + (i * 2)
                block_idx = struct.unpack('<H', packet[idx_offset:idx_offset + 2])[0]
                selected_blocks.append(block_idx)
                max_block_idx = max(max_block_idx, block_idx)
            
            packet_data = packet[indices_end:]
            
            parsed_packets.append({
                'id': packet_id,
                'blocks': selected_blocks,
                'data': packet_data
            })
        
        num_blocks = max_block_idx + 1
        
        # Gaussian elimination для декодирования
        decoded = self._gaussian_elimination(parsed_packets, num_blocks)
        
        if decoded is None:
            return None
        
        # Собираем данные обратно
        result = bytearray()
        for i in range(num_blocks):
            if i in decoded:
                result.extend(decoded[i])
            else:
                # Недостаточно пакетов для декодирования
                return None
        
        return bytes(result)
    
    def _gaussian_elimination(
        self,
        packets: list[dict],
        num_blocks: int
    ) -> Optional[dict[int, bytes]]:
        """
        Декодирование через Gaussian elimination
        Упрощенная версия для демонстрации
        """
        decoded = {}
        
        # Сначала декодируем пакеты с одним блоком
        for packet in packets:
            if len(packet['blocks']) == 1:
                block_idx = packet['blocks'][0]
                decoded[block_idx] = packet['data']
        
        # Итеративно декодируем остальные
        changed = True
        max_iterations = 100
        iteration = 0
        
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            
            for packet in packets:
                # Пропускаем уже обработанные
                unknown_blocks = [idx for idx in packet['blocks'] if idx not in decoded]
                
                if len(unknown_blocks) == 0:
                    continue
                
                if len(unknown_blocks) == 1:
                    # Можем декодировать этот блок
                    unknown_idx = unknown_blocks[0]
                    
                    # XOR packet_data со всеми известными блоками
                    result = bytearray(packet['data'])
                    
                    for known_idx in packet['blocks']:
                        if known_idx in decoded:
                            known_block = decoded[known_idx]
                            for i in range(len(result)):
                                result[i] ^= known_block[i]
                    
                    decoded[unknown_idx] = bytes(result)
                    changed = True
        
        # Проверяем, все ли блоки декодированы
        if len(decoded) == num_blocks:
            return decoded
        
        return None


# Простой тест
if __name__ == '__main__':
    # Тестовые данные
    test_data = b"Hello, World! " * 100
    
    print("Original data size:", len(test_data))
    
    # Кодирование
    encoder = FountainEncoder(test_data, redundancy=1.5)
    packets = encoder.encode()
    
    print(f"Generated {len(packets)} packets")
    
    # Декодирование (используем только 80% пакетов для теста)
    num_packets_to_use = int(len(packets) * 0.8)
    decoder = FountainDecoder(encoder.packet_size)
    
    for packet in packets[:num_packets_to_use]:
        decoder.add_packet(packet)
    
    decoded_data = decoder.decode()
    
    if decoded_data:
        # Убираем padding
        decoded_data = decoded_data[:len(test_data)]
        print("Decoded successfully!")
        print("Data matches:", decoded_data == test_data)
    else:
        print("Failed to decode - need more packets")
