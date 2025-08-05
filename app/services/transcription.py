"""
This service contains the core logic for transcribing audio sources.
"""
import whisper
from rich.console import Console

console = Console()


class TranscriptionService:
    """Orchestrates the transcription process."""

    def __init__(self, model: whisper.Whisper):
        self.model = model

    def transcribe(self, source_path: str, language: str | None) -> str:
        """
        Транскрибирует аудио из указанного источника.

        Args:
            source_path: Путь к локальному аудиофайлу.
            language: Язык для транскрибации (опционально).

        Returns:
            Транскрибированный текст.
        """
        console.print(
            "🎧 [bold blue]Начинаю транскрибацию файла...[/bold blue] (Это может занять время в зависимости от размера файла и модели)"
        )

        # Метод .transcribe из whisper корректно обрабатывает None для языка
        result = self.model.transcribe(audio=source_path, language=language, verbose=False)

        transcribed_text = result["text"].strip()
        return transcribed_text