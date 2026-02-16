"""
RuTube Uploader - загрузка видео на RuTube
"""
import os
import time
import json
from typing import Optional, Dict, Any
from pathlib import Path

import requests
from tqdm import tqdm


class RuTubeUploader:
    """Загрузчик видео на RuTube через API"""
    
    BASE_URL = "https://rutube.ru/api"
    UPLOAD_URL = "https://rutube.ru/api/video"
    
    def __init__(self, access_token: str):
        """
        Args:
            access_token: токен доступа RuTube API
        """
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        })
    
    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        category_id: int = 24,  # Разное
        is_hidden: bool = True,
        tags: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Загружает видео на RuTube
        
        Args:
            video_path: путь к видео файлу
            title: название видео
            description: описание
            category_id: ID категории
            is_hidden: скрытое видео (по умолчанию True для storage)
            tags: теги видео
        
        Returns:
            информация о загруженном видео
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        print(f"📤 Uploading to RuTube: {video_path.name}")
        print(f"📊 Size: {self._format_size(video_path.stat().st_size)}")
        
        # Шаг 1: Создаем видео запись
        print("🔗 Creating video entry...")
        video_data = self._create_video_entry(
            title=title,
            description=description,
            category_id=category_id,
            is_hidden=is_hidden,
            tags=tags or []
        )
        
        video_id = video_data['id']
        upload_url = video_data['video_upload_url']
        
        # Шаг 2: Загружаем файл
        print("⬆️  Uploading video file...")
        self._upload_file(video_path, upload_url)
        
        # Шаг 3: Ждем обработки
        print("⏳ Waiting for processing...")
        video_info = self._wait_for_processing(video_id)
        
        print(f"✅ Upload complete!")
        print(f"🔗 Video ID: {video_id}")
        print(f"🔗 URL: https://rutube.ru/video/{video_id}")
        
        return {
            'video_id': video_id,
            'url': f"https://rutube.ru/video/{video_id}",
            'info': video_info
        }
    
    def download(
        self,
        video_id: str,
        output_path: str,
        quality: str = "best"
    ) -> str:
        """
        Скачивает видео с RuTube
        
        Args:
            video_id: ID видео
            output_path: путь для сохранения
            quality: качество (best, 1080p, 720p, 480p, 360p)
        
        Returns:
            путь к скачанному файлу
        """
        print(f"📥 Downloading from RuTube: {video_id}")
        
        # Получаем информацию о видео
        video_info = self._get_video_info(video_id)
        
        if not video_info:
            raise ValueError(f"Video not found: {video_id}")
        
        # Получаем ссылку на видео
        video_url = video_info.get('video_url') or video_info.get('m3u8_url')
        
        if not video_url:
            # Пытаемся получить через опции
            options = video_info.get('video_balancer', {}).get('m3u8')
            if options:
                video_url = options
        
        if not video_url:
            raise ValueError("No download URL found")
        
        print(f"🔗 Download URL: {video_url}")
        
        # Для m3u8 нужен специальный обработчик, но для простоты используем прямую ссылку
        # В реальном приложении лучше использовать yt-dlp или подобные инструменты
        
        output_path = Path(output_path)
        
        # Скачиваем файл
        print("⬇️  Downloading...")
        response = self.session.get(video_url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        print(f"✅ Downloaded: {output_path}")
        return str(output_path)
    
    def _create_video_entry(
        self,
        title: str,
        description: str,
        category_id: int,
        is_hidden: bool,
        tags: list[str]
    ) -> Dict[str, Any]:
        """Создает запись о видео на RuTube"""
        data = {
            'title': title,
            'description': description,
            'category_id': category_id,
            'is_hidden': is_hidden,
            'tags': tags
        }
        
        response = self.session.post(f"{self.UPLOAD_URL}/", json=data)
        
        if response.status_code not in [200, 201]:
            raise RuntimeError(f"Failed to create video entry: {response.status_code} - {response.text}")
        
        return response.json()
    
    def _upload_file(self, file_path: Path, upload_url: str) -> None:
        """Загружает файл по полученному URL"""
        # RuTube использует chunked upload для больших файлов
        chunk_size = 10 * 1024 * 1024  # 10 MB chunks
        file_size = file_path.stat().st_size
        
        with open(file_path, 'rb') as f:
            with tqdm(total=file_size, unit='B', unit_scale=True) as pbar:
                uploaded = 0
                chunk_num = 0
                
                while uploaded < file_size:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Формируем headers для chunked upload
                    headers = {
                        'Content-Type': 'application/octet-stream',
                        'Content-Range': f'bytes {uploaded}-{uploaded + len(chunk) - 1}/{file_size}'
                    }
                    
                    response = requests.put(
                        upload_url,
                        data=chunk,
                        headers=headers
                    )
                    
                    if response.status_code not in [200, 201, 206]:
                        raise RuntimeError(f"Chunk upload failed: {response.status_code}")
                    
                    uploaded += len(chunk)
                    pbar.update(len(chunk))
                    chunk_num += 1
    
    def _get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о видео"""
        response = self.session.get(f"{self.UPLOAD_URL}/{video_id}/")
        
        if response.status_code != 200:
            return None
        
        return response.json()
    
    def _wait_for_processing(
        self,
        video_id: str,
        max_wait: int = 600
    ) -> Dict[str, Any]:
        """
        Ждет окончания обработки видео на RuTube
        
        Args:
            video_id: ID видео
            max_wait: максимальное время ожидания в секундах
        
        Returns:
            информация о видео
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            video_info = self._get_video_info(video_id)
            
            if not video_info:
                time.sleep(5)
                continue
            
            # Проверяем статус обработки
            publication_state = video_info.get('publication_state')
            
            if publication_state in ['ready', 'published']:
                return video_info
            
            if publication_state == 'failed':
                raise RuntimeError("Video processing failed")
            
            time.sleep(5)
        
        raise TimeoutError("Video processing timeout")
    
    def get_categories(self) -> list[Dict[str, Any]]:
        """Получает список доступных категорий"""
        response = self.session.get(f"{self.BASE_URL}/video/category/")
        
        if response.status_code != 200:
            raise RuntimeError(f"Failed to get categories: {response.status_code}")
        
        return response.json()
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Форматирует размер в человеко-читаемый вид"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


# Пример использования
if __name__ == '__main__':
    # ВАЖНО: Замените на ваш токен
    TOKEN = "your_rutube_access_token_here"
    
    # Загрузка
    uploader = RuTubeUploader(access_token=TOKEN)
    
    try:
        # Получаем категории
        categories = uploader.get_categories()
        print("Available categories:")
        for cat in categories[:5]:  # Первые 5
            print(f"  {cat['id']}: {cat['name']}")
        
        # Загружаем видео
        result = uploader.upload(
            video_path="test_video.mkv",
            title="Storage Video",
            description="Encrypted file storage",
            is_hidden=True,
            tags=["storage", "encrypted"]
        )
        print(f"Video uploaded: {result['url']}")
    except Exception as e:
        print(f"Upload failed: {e}")
