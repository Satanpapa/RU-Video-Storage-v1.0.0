"""
CLI - интерфейс командной строки для RU Video Storage
"""
import sys
from pathlib import Path

import click
from colorama import init as colorama_init, Fore, Style

from .encoder import VideoEncoder
from .decoder import VideoDecoder
from .vk_uploader import VKUploader
from .rutube_uploader import RuTubeUploader

# Инициализация colorama для Windows
colorama_init()


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    RU Video Storage - инструмент для хранения файлов на видеоплатформах
    
    Поддерживаемые платформы: VK Видео, RuTube
    """
    pass


@cli.command()
@click.option('--input', '-i', 'input_file', required=True, type=click.Path(exists=True),
              help='Входной файл для кодирования')
@click.option('--output', '-o', 'output_file', required=True, type=click.Path(),
              help='Выходное видео (.mkv)')
@click.option('--encrypt', is_flag=True, help='Шифровать файл')
@click.option('--password', '-p', help='Пароль для шифрования')
@click.option('--chunk-size', type=int, default=64*1024,
              help='Размер чанка в байтах (по умолчанию 64KB)')
def encode(input_file, output_file, encrypt, password, chunk_size):
    """Кодирует файл в видео"""
    try:
        if encrypt and not password:
            password = click.prompt('Enter encryption password', hide_input=True,
                                   confirmation_prompt=True)
        
        click.echo(f"{Fore.CYAN}🎬 Starting encoding...{Style.RESET_ALL}")
        
        encoder = VideoEncoder(
            input_file=input_file,
            output_file=output_file,
            encryption_password=password if encrypt else None,
            chunk_size=chunk_size
        )
        
        encoder.encode()
        
        click.echo(f"{Fore.GREEN}✅ Encoding complete!{Style.RESET_ALL}")
        
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--input', '-i', 'input_file', required=True, type=click.Path(exists=True),
              help='Входное видео (.mkv)')
@click.option('--output', '-o', 'output_file', required=True, type=click.Path(),
              help='Выходной файл')
@click.option('--password', '-p', help='Пароль для дешифрования')
def decode(input_file, output_file, password):
    """Декодирует видео обратно в файл"""
    try:
        click.echo(f"{Fore.CYAN}🎬 Starting decoding...{Style.RESET_ALL}")
        
        decoder = VideoDecoder(
            input_file=input_file,
            output_file=output_file,
            decryption_password=password
        )
        
        decoder.decode()
        
        click.echo(f"{Fore.GREEN}✅ Decoding complete!{Style.RESET_ALL}")
        
    except ValueError as e:
        if "password" in str(e).lower():
            if not password:
                password = click.prompt('Enter decryption password', hide_input=True)
                # Retry with password
                decoder = VideoDecoder(
                    input_file=input_file,
                    output_file=output_file,
                    decryption_password=password
                )
                decoder.decode()
                click.echo(f"{Fore.GREEN}✅ Decoding complete!{Style.RESET_ALL}")
            else:
                click.echo(f"{Fore.RED}❌ Wrong password or corrupted data{Style.RESET_ALL}", err=True)
                sys.exit(1)
        else:
            raise
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--platform', '-p', required=True, type=click.Choice(['vk', 'rutube']),
              help='Платформа для загрузки')
@click.option('--input', '-i', 'input_file', required=True, type=click.Path(exists=True),
              help='Видео файл для загрузки')
@click.option('--token', '-t', required=True, help='API токен платформы')
@click.option('--title', required=True, help='Название видео')
@click.option('--description', '-d', default='', help='Описание видео')
@click.option('--private/--public', default=True, help='Приватное видео (по умолчанию)')
def upload(platform, input_file, token, title, description, private):
    """Загружает видео на платформу"""
    try:
        click.echo(f"{Fore.CYAN}📤 Uploading to {platform.upper()}...{Style.RESET_ALL}")
        
        if platform == 'vk':
            uploader = VKUploader(access_token=token)
            result = uploader.upload(
                video_path=input_file,
                title=title,
                description=description,
                is_private=private
            )
        else:  # rutube
            uploader = RuTubeUploader(access_token=token)
            result = uploader.upload(
                video_path=input_file,
                title=title,
                description=description,
                is_hidden=private
            )
        
        click.echo(f"{Fore.GREEN}✅ Upload complete!{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}🔗 URL: {result['url']}{Style.RESET_ALL}")
        
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--platform', '-p', required=True, type=click.Choice(['vk', 'rutube']),
              help='Платформа для скачивания')
@click.option('--video-id', '-v', required=True, help='ID видео (для VK: owner_id_video_id)')
@click.option('--output', '-o', 'output_file', required=True, type=click.Path(),
              help='Путь для сохранения')
@click.option('--token', '-t', required=True, help='API токен платформы')
def download(platform, video_id, output_file, token):
    """Скачивает видео с платформы"""
    try:
        click.echo(f"{Fore.CYAN}📥 Downloading from {platform.upper()}...{Style.RESET_ALL}")
        
        if platform == 'vk':
            # Парсим owner_id и video_id
            if '_' in video_id:
                owner_id, vid = video_id.split('_')
                owner_id = int(owner_id)
                vid = int(vid)
            else:
                click.echo(f"{Fore.RED}❌ VK video ID format: owner_id_video_id{Style.RESET_ALL}", err=True)
                sys.exit(1)
            
            uploader = VKUploader(access_token=token)
            result = uploader.download(
                owner_id=owner_id,
                video_id=vid,
                output_path=output_file
            )
        else:  # rutube
            uploader = RuTubeUploader(access_token=token)
            result = uploader.download(
                video_id=video_id,
                output_path=output_file
            )
        
        click.echo(f"{Fore.GREEN}✅ Download complete: {result}{Style.RESET_ALL}")
        
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--input', '-i', 'input_file', required=True, type=click.Path(exists=True),
              help='Входной файл')
@click.option('--output', '-o', 'output_video', required=True, type=click.Path(),
              help='Выходное видео')
@click.option('--platform', '-p', required=True, type=click.Choice(['vk', 'rutube']),
              help='Платформа для загрузки')
@click.option('--token', '-t', required=True, help='API токен')
@click.option('--title', required=True, help='Название видео')
@click.option('--encrypt', is_flag=True, help='Шифровать файл')
@click.option('--password', help='Пароль для шифрования')
@click.option('--keep-video', is_flag=True, help='Оставить видео файл после загрузки')
def store(input_file, output_video, platform, token, title, encrypt, password, keep_video):
    """Кодирует и загружает файл одной командой"""
    try:
        # Кодируем
        if encrypt and not password:
            password = click.prompt('Enter encryption password', hide_input=True,
                                   confirmation_prompt=True)
        
        click.echo(f"{Fore.CYAN}🎬 Step 1/2: Encoding...{Style.RESET_ALL}")
        
        encoder = VideoEncoder(
            input_file=input_file,
            output_file=output_video,
            encryption_password=password if encrypt else None
        )
        encoder.encode()
        
        # Загружаем
        click.echo(f"{Fore.CYAN}📤 Step 2/2: Uploading to {platform.upper()}...{Style.RESET_ALL}")
        
        if platform == 'vk':
            uploader = VKUploader(access_token=token)
            result = uploader.upload(
                video_path=output_video,
                title=title,
                description=f"Encrypted: {encrypt}",
                is_private=True
            )
        else:
            uploader = RuTubeUploader(access_token=token)
            result = uploader.upload(
                video_path=output_video,
                title=title,
                description=f"Encrypted: {encrypt}",
                is_hidden=True
            )
        
        # Удаляем видео файл если не нужно его хранить
        if not keep_video:
            Path(output_video).unlink()
            click.echo(f"{Fore.YELLOW}🗑️  Temporary video file deleted{Style.RESET_ALL}")
        
        click.echo(f"{Fore.GREEN}✅ File stored successfully!{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}🔗 URL: {result['url']}{Style.RESET_ALL}")
        
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
