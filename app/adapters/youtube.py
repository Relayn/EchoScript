# app/adapters/youtube.py
"""
Этот адаптер отвечает за обработку URL-адресов YouTube, загрузку
аудиопотока и предоставление пути к аудиофайлу, используя yt-dlp.
"""
import os
import shutil
import tempfile

import yt_dlp
from rich.console import Console

console = Console()


class YoutubeAdapterError(Exception):
    """Пользовательское исключение для ошибок YoutubeAdapter."""
    pass


class FFmpegNotFoundError(YoutubeAdapterError):
    """Исключение, вызываемое, когда ffmpeg не найден в системе."""
    pass


class YoutubeAdapter:
    """Обрабатывает загрузку аудио с URL-адресов YouTube с помощью yt-dlp."""

    def __init__(self):
        self._temp_dir = tempfile.mkdtemp(prefix="echoscript_")
        self._downloaded_file_path = None
        # Проверяем наличие ffmpeg при инициализации
        if not shutil.which("ffmpeg"):
            raise FFmpegNotFoundError(
                "Для работы с YouTube необходим ffmpeg, но он не найден в вашей системе.\n"
                "Пожалуйста, установите его и убедитесь, что он доступен в системном PATH.\n"
                "Инструкции по установке: https://ffmpeg.org/download.html"
            )

    def download_audio(self, url: str) -> str | None:
        """
        Загружает аудио из URL-адреса YouTube.

        Args:
            url: URL-адрес видео на YouTube.

        Returns:
            Путь к загруженному аудиофайлу или None в случае ошибки.
        """
        console.print(f"▶️ [bold blue]Загрузка аудио с YouTube (используя yt-dlp):[/bold blue] {url}")

        output_template = os.path.join(self._temp_dir, "%(id)s.%(ext)s")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a', # m4a - хороший компромисс между качеством и размером
            }],
            'noprogress': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                console.print(f"   - Название: [italic]{info.get('title', 'N/A')}[/italic]")
                console.print(f"   - Длительность: [italic]{info.get('duration_string', 'N/A')}[/italic]")

                ydl.download([url])

                downloaded_files = os.listdir(self._temp_dir)
                if not downloaded_files:
                    raise YoutubeAdapterError("yt-dlp завершил работу, но файл не был создан.")

                self._downloaded_file_path = os.path.join(self._temp_dir, downloaded_files[0])
                console.print(f"   - [green]Аудио успешно извлечено в:[/green] {self._downloaded_file_path}")
                return self._downloaded_file_path

        except yt_dlp.utils.DownloadError as e:
            console.print(f"[bold red]❌ Ошибка при загрузке с YouTube (yt-dlp):[/bold red] {e}")
            self.cleanup()
            return None
        except Exception as e:
            console.print(f"[bold red]❌ Непредвиденная ошибка в YoutubeAdapter:[/bold red] {e}")
            self.cleanup()
            return None


    def cleanup(self):
        """Удаляет временную директорию и все ее содержимое."""
        if os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                console.print(f"   - [dim]Временные файлы очищены ({self._temp_dir}).[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Не удалось очистить временные файлы: {e}[/yellow]")