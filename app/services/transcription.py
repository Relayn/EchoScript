"""
Этот сервис содержит основную логику для транскрибации аудиоисточников.
"""

import threading
from typing import Callable, Optional

import numpy as np
import soundfile as sf
import whisper
from rich.console import Console

from app.core.models import TranscriptionTask

console = Console()

# Определяем размер чанка в секундах. 30 секунд - стандарт для Whisper.
CHUNK_DURATION_SECONDS = 30


class TranscriptionService:
    """Управляет процессом транскрибации, используя нарезку аудио на части (чанки)."""

    def __init__(self, model: whisper.Whisper):
        self.model = model

    def transcribe(
        self,
        source_path: str,
        language: str | None,
        task: TranscriptionTask,
        cancel_event: threading.Event,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> dict:
        """
        Транскрибирует аудио из указанного источника, обрабатывая его по частям.

        Args:
            source_path: Путь к локальному аудиофайлу.
            language: Язык для транскрибиции (опционально).
            progress_callback: Функция для отслеживания прогресса.
                               Принимает (обработано_чанков, всего_чанков).

        Returns:
            Словарь с результатами, содержащий ключи 'text' и 'segments'.
        """
        try:
            with sf.SoundFile(source_path, "r") as audio_file:
                samplerate = audio_file.samplerate
                total_frames = len(audio_file)
                chunk_size_frames = CHUNK_DURATION_SECONDS * samplerate
                num_chunks = int(np.ceil(total_frames / chunk_size_frames))

                all_segments = []
                options = {
                    "language": language,
                    "verbose": True,
                    "task": task.value,
                }
                chunk_offset_seconds = 0.0

                for i, chunk_data in enumerate(
                    self._read_chunks(audio_file, chunk_size_frames)
                ):
                    if cancel_event.is_set():
                        console.print(
                            "[yellow]Отмена транскрибации по запросу "
                            "пользователя.[/yellow]"
                        )
                        break  # Выходим из цикла, если запрошена отмена

                    audio_chunk = chunk_data.astype(np.float32)
                    result = self.model.transcribe(audio=audio_chunk, **options)

                    for segment in result.get("segments", []):
                        segment["start"] += chunk_offset_seconds
                        segment["end"] += chunk_offset_seconds
                        all_segments.append(segment)

                    chunk_offset_seconds += CHUNK_DURATION_SECONDS
                    if progress_callback is not None:
                        progress_callback(i + 1, num_chunks)

                full_text = " ".join(s["text"].strip() for s in all_segments)
                return {"text": full_text, "segments": all_segments}

        except Exception as e:
            console.print(
                f"[bold red]❌ Произошла ошибка во время транскрибации: {e}[/bold red]"
            )
            return {"text": "", "segments": []}

    def _read_chunks(self, audio_file: sf.SoundFile, chunk_size_frames: int):
        """Генератор, который читает аудиофайл по частям."""
        while True:
            data = audio_file.read(chunk_size_frames)
            if not len(data):
                break
            yield data
