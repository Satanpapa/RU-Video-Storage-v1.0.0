"""
Setup script for RU Video Storage
"""
from setuptools import setup, find_packages
from pathlib import Path

# Читаем README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

# Читаем requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.startswith('#')
    ]

setup(
    name="ru-video-storage",
    version="1.0.0",
    author="RU Video Storage Team",
    author_email="example@example.com",
    description="Инструмент для хранения файлов на российских видеоплатформах (VK Видео, RuTube)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ru-video-storage",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'ru-video-storage=src.cli:cli',
        ],
    },
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-asyncio>=0.21.0',
            'pytest-cov>=4.1.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
