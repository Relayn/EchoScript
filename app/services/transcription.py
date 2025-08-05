"""
This service contains the core logic for transcribing audio sources.
"""
import numpy as np
import soundfile as sf
import whisper
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)

console = Console()

# Определяем размер чанка в секундах. 30 секунд - стандарт для Whisper.
CHUNK_DURATION_SECONDS = 30


class TranscriptionService:
    """Orchestrates the transcription process using chunking."""

    def __init__(self, model: whisper.Whisper):
        self.model = model

    def transcribe(self, source_path: str, language: str | None, timestamps: bool) -> str:
        """
        Транскрибирует аудио из указанного источника, обрабатывая его по частям.

        Args:
            source_path: Путь к локальному аудиофайлу.
            language: Язык для транскрибиции (опционально).
            timestamps: Включать ли временные метки в вывод.

        Returns:
            Полный транскрибированный текст.
        """
        try:
            with sf.SoundFile(source_path, "r") as audio_file:
                samplerate = audio_file.samplerate
                total_frames = len(audio_file)
                chunk_size_frames = CHUNK_DURATION_SECONDS * samplerate
                num_chunks = int(np.ceil(total_frames / chunk_size_frames))

                console.print(
                    "🎧 [bold blue]Начинаю транскрибацию...[/bold blue] (Файл будет обработан по частям)"
                )

                full_text = []
                # Whisper возвращает генератор сегментов, если verbose=True
                # В whisper-библиотеке опция для таймстемпов - это verbose=True
                options = {"language": language, "verbose": timestamps}

                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    MofNCompleteColumn(),
                    TimeRemainingColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task("[cyan]Транскрибация...", total=num_chunks)

                    for i, chunk_data in enumerate(
                        self._read_chunks(audio_file, chunk_size_frames)
                    ):
                        audio_chunk = chunk_data.astype(np.float32)

                        result = self.model.transcribe(audio=audio_chunk, **options)

                        if timestamps:
                            # Если нужны таймстемпы, собираем сегменты
                            for segment in result["segments"]:
                                start = int(segment['start'])
                                end = int(segment['end'])
                                # Простое форматирование времени из секунд
                                start_time = f"{start // 3600:02d}:{(start % 3600) // 60:02d}:{start % 60:02d}"
                                end_time = f"{end // 3600:02d}:{(end % 3600) // 60:02d}:{end % 60:02d}"
                                text = segment['text']
                                full_text.append(f"[{start_time} -> {end_time}] {text.strip()}")
                        else:
                            full_text.append(result["text"])

                        progress.update(task, advance=1)

                return "\n".join(full_text).strip()

        except Exception as e:
            console.print(f"[bold red]❌ Произошла ошибка во время транскрибации: {e}[/bold red]")
            return ""

    def _read_chunks(self, audio_file: sf.SoundFile, chunk_size_frames: int):
        """Генератор, который читает аудиофайл по частям."""
        while True:
            data = audio_file.read(chunk_size_frames)
            if not len(data):
                break
            yield data