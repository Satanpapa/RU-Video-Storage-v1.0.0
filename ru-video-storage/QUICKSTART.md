# 🚀 Быстрый старт

## Установка

```bash
# Клонируем репозиторий
git clone https://github.com/yourusername/ru-video-storage.git
cd ru-video-storage

# Создаем виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Устанавливаем зависимости
pip install -r requirements.txt

# Устанавливаем пакет
pip install -e .
```

## Базовое использование

### 1. Кодирование файла

```bash
python -m src.cli encode \
    --input my_document.pdf \
    --output storage.mkv \
    --encrypt \
    --password mypassword123
```

### 2. Декодирование файла

```bash
python -m src.cli decode \
    --input storage.mkv \
    --output restored.pdf \
    --password mypassword123
```

### 3. Загрузка на VK Видео

```bash
# Получите токен на https://vk.com/apps?act=manage
export VK_ACCESS_TOKEN="your_token_here"

python -m src.cli upload \
    --platform vk \
    --input storage.mkv \
    --token $VK_ACCESS_TOKEN \
    --title "My Storage Video" \
    --private
```

### 4. Загрузка на RuTube

```bash
# Получите токен через RuTube API
export RUTUBE_ACCESS_TOKEN="your_token_here"

python -m src.cli upload \
    --platform rutube \
    --input storage.mkv \
    --token $RUTUBE_ACCESS_TOKEN \
    --title "My Storage Video" \
    --private
```

### 5. Все в одной команде

```bash
# Кодирует и загружает файл одной командой
python -m src.cli store \
    --input document.pdf \
    --output temp.mkv \
    --platform vk \
    --token $VK_ACCESS_TOKEN \
    --title "Document Storage" \
    --encrypt \
    --password secret123
```

## Python API

```python
from src import VideoEncoder, VideoDecoder, VKUploader

# Кодирование
encoder = VideoEncoder(
    input_file="file.txt",
    output_file="video.mkv",
    encryption_password="pass123"
)
encoder.encode()

# Декодирование
decoder = VideoDecoder(
    input_file="video.mkv",
    output_file="file_restored.txt",
    decryption_password="pass123"
)
decoder.decode()

# Загрузка на VK
uploader = VKUploader(access_token="your_token")
result = uploader.upload(
    video_path="video.mkv",
    title="Storage",
    is_private=True
)
print(f"Uploaded: {result['url']}")
```

## Получение токенов

### VK Видео

1. Перейдите на https://vk.com/apps?act=manage
2. Создайте новое приложение (Standalone)
3. В настройках получите `access_token`
4. Необходимые права: `video`

### RuTube

1. Зарегистрируйтесь на https://rutube.ru/
2. Перейдите в настройки разработчика
3. Создайте приложение
4. Получите API credentials через OAuth

## Советы

- Используйте сильные пароли (16+ символов)
- Храните токены в переменных окружения
- Для больших файлов увеличьте `chunk_size`
- Всегда делайте резервные копии важных данных

## Решение проблем

### FFmpeg не найден

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Скачайте с https://ffmpeg.org/download.html
```

### Ошибка при кодировании

Убедитесь, что FFmpeg версии 5.0 или выше:
```bash
ffmpeg -version
```

### Неверный пароль

При декодировании убедитесь, что используете тот же пароль, что и при кодировании.

## Примеры

Запустите файл с примерами:
```bash
python examples.py
```

## Дальнейшие шаги

- Прочитайте полную документацию в README.md
- Изучите примеры в examples.py
- Посмотрите API документацию платформ
