"""
Адаптер для предварительной обработки локальных медиафайлов.
"""

import os
import pathlib
import shutil
import subprocess
import tempfile
from typing import Callable, Optional

from app.adapters.youtube import FFmpegNotFoundError
from app.core.utils import find_ffmpeg_path


class LocalFileAdapter:
    """
    Обрабатывает локальные медиафайлы, конвертируя их в стандартный
    формат WAV с помощью ffmpeg для дальнейшей обработки.
    """

    def __init__(self):
        self._temp_dir = tempfile.mkdtemp(prefix="echoscript_local_")
        self.ffmpeg_path = find_ffmpeg_path()
        if not self.ffmpeg_path:
            raise FFmpegNotFoundError(
                "Для обработки локальных файлов необходим ffmpeg, но он не найден."
            )

    def process_file(
        self, source_path: str, log_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Конвертирует исходный файл в временный WAV-файл.
        """
        if log_callback:
            log_callback(f"Обработка локального файла: {source_path}")
        source_path_obj = pathlib.Path(source_path)
        output_filename = f"{source_path_obj.stem}.wav"
        output_path = os.path.join(self._temp_dir, output_filename)

        command = [
            self.ffmpeg_path,
            "-i",
            str(source_path_obj),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-y",
            output_path,
        ]

        try:
            subprocess.run(
                command, check=True, capture_output=True, text=True, encoding="utf-8"
            )
            if log_callback:
                log_callback(f"Файл успешно конвертирован в: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            if log_callback:
                log_callback("Ошибка при конвертации файла с помощью ffmpeg:")
                log_callback(f"Stderr: {e.stderr}")
            msg = (
                f"Не удалось обработать файл '{source_path_obj.name}' с помощью ffmpeg."
            )
            raise IOError(msg) from e
        except Exception as e:
            if log_callback:
                log_callback(f"Непредвиденная ошибка в LocalFileAdapter: {e}")
            raise

    def cleanup(self, log_callback: Optional[Callable[[str], None]] = None):
        """Удаляет временную директорию и все ее содержимое."""
        if os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                if log_callback:
                    log_callback("Временные файлы локальной обработки очищены.")
            except Exception as e:
                if log_callback:
                    log_callback(f"Не удалось очистить временные файлы: {e}")
