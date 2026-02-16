# Архитектура RU Video Storage

## Обзор

RU Video Storage — это инструмент для хранения произвольных файлов на российских видеоплатформах (VK Видео и RuTube) путем преобразования файлов в lossless видео.

## Архитектурные компоненты

```
┌─────────────────────────────────────────────────────────┐
│                     CLI / Python API                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │   Encoder    │  │   Decoder    │  │   Uploaders   │ │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘ │
│         │                  │                   │         │
│  ┌──────▼──────────────────▼───────────────────▼──────┐ │
│  │           Core Components Layer                    │ │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │ │
│  │  │ Fountain │  │  Crypto  │  │    Metadata     │  │ │
│  │  │  Codes   │  │          │  │                 │  │ │
│  │  └──────────┘  └──────────┘  └─────────────────┘  │ │
│  └───────────────────────────────────────────────────┘ │
│                                                          │
├─────────────────────────────────────────────────────────┤
│              External Dependencies                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │  FFmpeg  │  │ OpenCV   │  │  VK/RuTube APIs      │ │
│  └──────────┘  └──────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Поток данных

### Кодирование (Encoding Flow)

```
Input File
    │
    ├─► [Read File] → Raw Bytes
    │
    ├─► [Optional: Encrypt] → AES-256-GCM → Encrypted Bytes
    │
    ├─► [Split into Chunks] → Chunk₁, Chunk₂, ..., Chunkₙ
    │
    ├─► [Add CRC32] → Each chunk gets checksum
    │
    ├─► [Fountain Encoding] → Generate redundant packets
    │                          (30% redundancy by default)
    │
    ├─► [Embed Metadata] → First frames contain:
    │                      - Filename
    │                      - File size
    │                      - Encryption flag
    │                      - Version info
    │
    ├─► [Encode to Video Frames] → Each packet → Video frame
    │                                (RGB channels)
    │
    └─► [FFV1/MKV] → Lossless Video File
            │
            └─► Upload to VK/RuTube
```

### Декодирование (Decoding Flow)

```
Video File (from VK/RuTube)
    │
    ├─► [Download] → Local .mkv file
    │
    ├─► [Open Video] → OpenCV VideoCapture
    │
    ├─► [Read Metadata Frames] → Extract:
    │                            - Filename
    │                            - File size
    │                            - Encryption info
    │
    ├─► [Read Data Frames] → Extract packets from RGB channels
    │
    ├─► [Group by Chunk] → Organize packets by chunk index
    │
    ├─► [Fountain Decoding] → Reconstruct original chunks
    │                          using redundancy
    │
    ├─► [Verify CRC32] → Check chunk integrity
    │
    ├─► [Reassemble File] → Combine all chunks
    │
    ├─► [Optional: Decrypt] → AES-256-GCM → Original bytes
    │
    └─► Output File (restored)
```

## Ключевые технологии

### 1. Fountain Codes (Wirehair-подобные)

**Назначение**: Обеспечение устойчивости к потере пакетов при сжатии платформой.

**Принцип работы**:
- Генерируется N пакетов из исходных данных
- Добавляется 30% избыточности (M = N × 1.3 пакетов)
- Для восстановления достаточно получить ≈N пакетов (не обязательно те же самые)
- Используется XOR и random selection для создания пакетов

**Преимущества**:
- Устойчивость к потере до 30% пакетов
- Эффективное O(N) кодирование/декодирование
- Не требует всех оригинальных пакетов

### 2. AES-256-GCM Шифрование

**Компоненты**:
- **Key Derivation**: PBKDF2 (100,000 итераций)
- **Algorithm**: AES-256 в режиме GCM
- **Authentication**: GCM tag для проверки целостности
- **Salt**: 16 байт случайных данных
- **Nonce**: 16 байт для каждого сообщения

**Структура зашифрованных данных**:
```
[Salt:16] [Nonce:16] [Tag:16] [Ciphertext:variable]
```

### 3. FFV1 Codec

**Характеристики**:
- **Lossless**: Без потери данных
- **Intra-frame**: Каждый кадр независим
- **YUV444P**: Полное цветовое пространство
- **4K Resolution**: 3840×2160 для максимальной плотности
- **30 FPS**: Стандартная частота кадров

**Преимущества**:
- Идеальное восстановление данных
- Поддержка в FFmpeg
- Хорошая совместимость

### 4. CRC32 Checksums

**Использование**:
- Каждый chunk имеет CRC32 checksum
- Проверка при декодировании
- Обнаружение повреждений с вероятностью ≈99.9999998%

## Модульная структура

### encoder.py
```python
VideoEncoder
├── __init__(input, output, password, chunk_size)
├── encode()
│   ├── read_file()
│   ├── encrypt_data() [optional]
│   ├── split_into_chunks()
│   ├── apply_fountain_encoding()
│   └── create_video()
└── _encode_packet_to_frame()
```

### decoder.py
```python
VideoDecoder
├── __init__(input, output, password)
├── decode()
│   ├── open_video()
│   ├── read_metadata()
│   ├── read_packets()
│   ├── apply_fountain_decoding()
│   ├── reconstruct_file()
│   └── decrypt_data() [optional]
└── _decode_frame_to_packet()
```

### fountain.py
```python
FountainEncoder
├── __init__(data, redundancy)
├── encode() → List[packets]
└── _xor_blocks()

FountainDecoder
├── __init__(block_size)
├── add_packet(packet)
├── decode() → bytes
└── _gaussian_elimination()
```

### crypto.py
```python
├── derive_key(password, salt) → key
├── encrypt_data(data, password) → encrypted
└── decrypt_data(encrypted, password) → data
```

### vk_uploader.py
```python
VKUploader
├── __init__(token)
├── upload(video, title, ...) → result
├── download(owner_id, video_id) → path
└── _wait_for_processing()
```

### rutube_uploader.py
```python
RuTubeUploader
├── __init__(token)
├── upload(video, title, ...) → result
├── download(video_id) → path
└── _wait_for_processing()
```

## Производительность

### Характеристики кодирования

| Размер файла | Время кодирования | Размер видео | Коэффициент |
|--------------|-------------------|--------------|-------------|
| 1 MB         | ~2-5 сек          | ~1.5 MB      | 1.5x        |
| 10 MB        | ~20-50 сек        | ~15 MB       | 1.5x        |
| 100 MB       | ~3-8 мин          | ~150 MB      | 1.5x        |
| 1 GB         | ~30-80 мин        | ~1.5 GB      | 1.5x        |

*Время зависит от CPU и настроек*

### Оптимизации

1. **Chunk Size**: Больше chunks = медленнее, но надежнее
2. **Redundancy**: Меньше избыточности = быстрее, но рискованнее
3. **Resolution**: Можно уменьшить до 1080p для небольших файлов
4. **Parallel Processing**: Можно распараллелить fountain encoding

## Безопасность

### Угрозы и защита

| Угроза | Защита |
|--------|--------|
| Перехват данных | AES-256-GCM шифрование |
| Подбор пароля | PBKDF2 с 100k итераций |
| Модификация данных | CRC32 + GCM authentication |
| Потеря пакетов | Fountain codes (30% redundancy) |
| Повреждение видео | Lossless FFV1 codec |

### Рекомендации

- Используйте пароли ≥16 символов
- Храните пароли в безопасном месте
- Не загружайте конфиденциальные данные без шифрования
- Делайте локальные резервные копии
- Регулярно проверяйте возможность декодирования

## Ограничения и компромиссы

### Технические ограничения

1. **Размер файлов**:
   - VK: до 256 GB или 12 часов видео
   - RuTube: аналогичные ограничения

2. **Скорость**:
   - Медленнее обычного облачного хранилища
   - Требует CPU для кодирования/декодирования

3. **Коэффициент расширения**:
   - Видео ~1.5-2x больше оригинала
   - Из-за избыточности и метаданных

### Юридические риски

⚠️ **ВАЖНО**: Использование видеоплатформ для хранения файлов может нарушать ToS:
- Риск блокировки аккаунта
- Удаление видео
- Потеря данных

**Рекомендация**: Только для образовательных целей и экспериментов.

## Будущие улучшения

### Версия 2.0 (планируется)

- [ ] Поддержка Yandex.Дзен Видео
- [ ] GUI приложение (Qt/Tkinter)
- [ ] Batch processing с очередями
- [ ] Настоящая библиотека Wirehair
- [ ] Оптимизация производительности (C++ расширения)
- [ ] Восстановление поврежденных видео
- [ ] Деление больших файлов на несколько видео
- [ ] Интеграция с облачными сервисами

## Сравнение с аналогами

| Проект | Платформа | Язык | Fountain Codes | Шифрование |
|--------|-----------|------|----------------|------------|
| yt-media-storage | YouTube | C++ | ✅ Wirehair | ✅ XChaCha20 |
| **ru-video-storage** | VK/RuTube | Python | ✅ Custom | ✅ AES-256 |
| youtube-drive | YouTube | Python | ❌ | ❌ |
| qStore | YouTube | Python | ❌ | ✅ |

## Заключение

RU Video Storage предоставляет полноценное решение для хранения файлов на российских видеоплатформах с акцентом на:
- **Надежность**: Fountain codes + CRC32
- **Безопасность**: AES-256-GCM шифрование
- **Удобство**: CLI + Python API
- **Качество**: Lossless FFV1 codec

Проект является proof-of-concept и демонстрацией технологий, не рекомендуется для критически важных данных.
