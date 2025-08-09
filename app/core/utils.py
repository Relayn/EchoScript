"""
Общие вспомогательные функции для проекта.
"""

import os
import shutil
import sys


def find_ffmpeg_path() -> str | None:
    """
    Находит путь к ffmpeg.

    Сначала ищет его внутри упакованного приложения (если оно запущено
    из сборки PyInstaller), а затем, если не находит, ищет в системном PATH.

    Returns:
        Строка с путем к ffmpeg.exe или None, если он не найден.
    """
    # Проверяем, запущено ли приложение из "замороженной" сборки PyInstaller
    if getattr(sys, "frozen", False):
        # Если да, то базовый путь - это директория с исполняемым файлом
        application_path = os.path.dirname(sys.executable)
        # Собираем предполагаемый путь к ffmpeg внутри нашей сборки
        ffmpeg_path = os.path.join(application_path, "ffmpeg", "ffmpeg.exe")
        if os.path.exists(ffmpeg_path):
            return ffmpeg_path

    # Если мы не в "замороженном" приложении или ffmpeg не найден внутри,
    # ищем его в системном PATH. Это поведение для режима разработки.
    return shutil.which("ffmpeg")
