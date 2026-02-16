"""
VK Uploader - загрузка видео на VK Видео
"""
import os
import time
from typing import Optional, Dict, Any
from pathlib import Path

import requests
from tqdm import tqdm


class VKUploader:
    """Загрузчик видео на VK Видео через API"""
    
    API_VERSION = "5.131"
    BASE_URL = "https://api.vk.com/method"
    
    def __init__(self, access_token: str, user_id: Optional[int] = None):
        """
        Args:
            access_token: токен доступа VK API
            user_id: ID пользователя (опционально)
        """
        self.access_token = access_token
        self.user_id = user_id
        self.session = requests.Session()
    
    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        is_private: bool = True,
        group_id: Optional[int] = None,
        album_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Загружает видео на VK
        
        Args:
            video_path: путь к видео файлу
            title: название видео
            description: описание
            is_private: приватное видео (по умолчанию True для storage)
            group_id: ID группы (если загружаем в группу)
            album_id: ID альбома
        
        Returns:
            информация о загруженном видео
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        print(f"📤 Uploading to VK: {video_path.name}")
        print(f"📊 Size: {self._format_size(video_path.stat().st_size)}")
        
        # Шаг 1: Получаем URL для загрузки
        print("🔗 Getting upload URL...")
        upload_url_data = self._get_upload_url(
            title=title,
            description=description,
            is_private=is_private,
            group_id=group_id,
            album_id=album_id
        )
        
        upload_url = upload_url_data['upload_url']
        video_id = upload_url_data.get('video_id')
        owner_id = upload_url_data.get('owner_id')
        
        # Шаг 2: Загружаем файл
        print("⬆️  Uploading video file...")
        self._upload_file(video_path, upload_url)
        
        # Шаг 3: Ждем обработки
        print("⏳ Waiting for processing...")
        video_info = self._wait_for_processing(owner_id, video_id)
        
        print(f"✅ Upload complete!")
        print(f"🔗 Video ID: {video_id}")
        print(f"🔗 URL: https://vk.com/video{owner_id}_{video_id}")
        
        return {
            'video_id': video_id,
            'owner_id': owner_id,
            'url': f"https://vk.com/video{owner_id}_{video_id}",
            'info': video_info
        }
    
    def download(
        self,
        owner_id: int,
        video_id: int,
        output_path: str,
        quality: str = "best"
    ) -> str:
        """
        Скачивает видео с VK
        
        Args:
            owner_id: ID владельца видео
            video_id: ID видео
            output_path: путь для сохранения
            quality: качество (best, 720p, 480p, 360p)
        
        Returns:
            путь к скачанному файлу
        """
        print(f"📥 Downloading from VK: {owner_id}_{video_id}")
        
        # Получаем информацию о видео и ссылки
        video_info = self._get_video_info(owner_id, video_id)
        
        if not video_info:
            raise ValueError(f"Video not found: {owner_id}_{video_id}")
        
        # Находим лучшее качество
        files = video_info.get('files', {})
        
        # Приоритет качества
        quality_priority = ['mp4_2160', 'mp4_1440', 'mp4_1080', 'mp4_720', 'mp4_480', 'mp4_360', 'mp4_240']
        
        download_url = None
        for q in quality_priority:
            if q in files:
                download_url = files[q]
                print(f"📺 Quality: {q}")
                break
        
        if not download_url:
            raise ValueError("No download URL found")
        
        # Скачиваем файл
        print("⬇️  Downloading...")
        output_path = Path(output_path)
        
        response = self.session.get(download_url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        print(f"✅ Downloaded: {output_path}")
        return str(output_path)
    
    def _get_upload_url(
        self,
        title: str,
        description: str,
        is_private: bool,
        group_id: Optional[int],
        album_id: Optional[int]
    ) -> Dict[str, Any]:
        """Получает URL для загрузки видео"""
        params = {
            'access_token': self.access_token,
            'v': self.API_VERSION,
            'name': title,
            'description': description,
            'is_private': 1 if is_private else 0,
        }
        
        if group_id:
            params['group_id'] = group_id
        if album_id:
            params['album_id'] = album_id
        
        response = self.session.get(f"{self.BASE_URL}/video.save", params=params)
        data = response.json()
        
        if 'error' in data:
            raise RuntimeError(f"VK API error: {data['error']}")
        
        return data['response']
    
    def _upload_file(self, file_path: Path, upload_url: str) -> None:
        """Загружает файл по полученному URL"""
        with open(file_path, 'rb') as f:
            # Получаем размер файла
            file_size = file_path.stat().st_size
            
            # Создаем progress bar
            with tqdm(total=file_size, unit='B', unit_scale=True) as pbar:
                # Wrapper для отслеживания прогресса
                class ProgressFileWrapper:
                    def __init__(self, file_obj, progress_bar):
                        self.file_obj = file_obj
                        self.progress_bar = progress_bar
                    
                    def read(self, size=-1):
                        data = self.file_obj.read(size)
                        self.progress_bar.update(len(data))
                        return data
                    
                    def __getattr__(self, name):
                        return getattr(self.file_obj, name)
                
                wrapped_file = ProgressFileWrapper(f, pbar)
                
                files = {'video_file': (file_path.name, wrapped_file)}
                response = self.session.post(upload_url, files=files)
                
                if response.status_code != 200:
                    raise RuntimeError(f"Upload failed: {response.status_code}")
    
    def _get_video_info(self, owner_id: int, video_id: int) -> Optional[Dict[str, Any]]:
        """Получает информацию о видео"""
        params = {
            'access_token': self.access_token,
            'v': self.API_VERSION,
            'videos': f"{owner_id}_{video_id}",
        }
        
        response = self.session.get(f"{self.BASE_URL}/video.get", params=params)
        data = response.json()
        
        if 'error' in data:
            raise RuntimeError(f"VK API error: {data['error']}")
        
        items = data['response'].get('items', [])
        return items[0] if items else None
    
    def _wait_for_processing(
        self,
        owner_id: int,
        video_id: int,
        max_wait: int = 600
    ) -> Dict[str, Any]:
        """
        Ждет окончания обработки видео на VK
        
        Args:
            owner_id: ID владельца
            video_id: ID видео
            max_wait: максимальное время ожидания в секундах
        
        Returns:
            информация о видео
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            video_info = self._get_video_info(owner_id, video_id)
            
            if video_info and video_info.get('processing') == 0:
                return video_info
            
            time.sleep(5)
        
        raise TimeoutError("Video processing timeout")
    
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
    TOKEN = "your_vk_access_token_here"
    
    # Загрузка
    uploader = VKUploader(access_token=TOKEN)
    
    try:
        result = uploader.upload(
            video_path="test_video.mkv",
            title="Storage Video",
            description="Encrypted file storage",
            is_private=True
        )
        print(f"Video uploaded: {result['url']}")
    except Exception as e:
        print(f"Upload failed: {e}")
