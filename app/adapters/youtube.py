"""
Этот адаптер отвечает за обработку URL-адресов YouTube, загрузку
аудиопотока и предоставление пути к аудиофайлу, используя yt-dlp.
"""

import os
import pathlib
import shutil
import subprocess  # nosec B404
import tempfile
from typing import Callable, Optional

import yt_dlp

from app.core.utils import find_ffmpeg_path


class YoutubeAdapterError(Exception):
    """Пользовательское исключение для ошибок YoutubeAdapter."""


class FFmpegNotFoundError(YoutubeAdapterError):
    """Исключение, вызываемое, когда ffmpeg не найден в системе."""


class YoutubeAdapter:
    """Обрабатывает загрузку аудио с URL-адресов YouTube с помощью yt-dlp."""

    def __init__(self) -> None:
        self._temp_dir: str = tempfile.mkdtemp(prefix="echoscript_")
        self.ffmpeg_path: Optional[str] = find_ffmpeg_path()
        if not self.ffmpeg_path:
            msg = (
                "Для работы с YouTube необходим ffmpeg, "
                "но он не найден в вашей системе.\n"
                "Пожалуйста, установите его и убедитесь, что он доступен в системном "
                "PATH.\n"
                "Инструкции по установке: https://ffmpeg.org/download.html"
            )
            raise FFmpegNotFoundError(msg)

    def download_audio(
        self, url: str, log_callback: Optional[Callable[[str], None]] = None
    ) -> str | None:
        """
        Загружает и конвертирует аудио из URL YouTube в стандартный формат WAV.
        """
        if log_callback:
            log_callback(f"Загрузка аудио с YouTube: {url}")

        output_template = os.path.join(self._temp_dir, "%(id)s.%(ext)s")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
            "noprogress": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if log_callback:
                    log_callback(f"Название: {info.get('title', 'N/A')}")
                    log_callback(f"Длительность: {info.get('duration_string', 'N/A')}")
                ydl.download([url])
                downloaded_files = os.listdir(self._temp_dir)
                if not downloaded_files:
                    raise YoutubeAdapterError(
                        "yt-dlp завершил работу, но файл не был создан."
                    )

                # --- ЭТАП 2: Конвертация в стандартный WAV формат ---
                source_m4a_path = os.path.join(self._temp_dir, downloaded_files[0])
                if log_callback:
                    log_callback("Конвертация в стандартный формат WAV...")

                if not self.ffmpeg_path:
                    raise FFmpegNotFoundError("Путь к ffmpeg не определен.")

                output_wav_path = str(pathlib.Path(source_m4a_path).with_suffix(".wav"))
                command = [
                    self.ffmpeg_path,
                    "-i",
                    source_m4a_path,
                    "-vn",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-y",
                    output_wav_path,
                ]
                subprocess.run(  # nosec B603
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )

                if log_callback:
                    log_callback("Аудио успешно подготовлено для транскрибации.")
                return output_wav_path

        except (yt_dlp.utils.DownloadError, subprocess.CalledProcessError) as e:
            error_message = getattr(e, "stderr", str(e))
            if log_callback:
                log_callback(f"Ошибка при обработке YouTube ссылки: {error_message}")
            self.cleanup(log_callback)
            return None
        except Exception as e:
            if log_callback:
                log_callback(f"Непредвиденная ошибка в YoutubeAdapter: {e}")
            self.cleanup(log_callback)
            return None

    def cleanup(self, log_callback: Optional[Callable[[str], None]] = None) -> None:
        """Удаляет временную директорию и все ее содержимое."""
        if os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                if log_callback:
                    log_callback("Временные файлы YouTube очищены.")
            except Exception as e:
                if log_callback:
                    log_callback(f"Не удалось очистить временные файлы: {e}")
