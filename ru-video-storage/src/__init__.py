"""
RU Video Storage - хранение файлов на российских видеоплатформах
"""

__version__ = "1.0.0"
__author__ = "RU Video Storage Team"

from .encoder import VideoEncoder
from .decoder import VideoDecoder
from .vk_uploader import VKUploader
from .rutube_uploader import RuTubeUploader

__all__ = [
    'VideoEncoder',
    'VideoDecoder',
    'VKUploader',
    'RuTubeUploader',
]
