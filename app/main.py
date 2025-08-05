"""
Этот модуль определяет интерфейс командной строки (CLI) для EchoScript.
Он использует Typer для создания удобного и надежного инструмента.
"""

import pathlib
import importlib.metadata
from typing_extensions import Annotated

import typer
from rich.console import Console

from app.core.models import ModelSize, OutputFormat

# Создаем экземпляр приложения Typer
app = typer.Typer(
    name="echoscript",
    help="CLI-утилита для транскрибации аудио/видео файлов и ссылок YouTube с помощью Whisper.",
    add_completion=False,
    rich_markup_mode="markdown",
    no_args_is_help=True,
)

console = Console()


def pre_flight_check(source: str) -> bool:
    """
    Выполняет предварительную проверку источника, чтобы убедиться в его корректности
    перед началом обработки.
    """
    if source.startswith(("http://", "https://")):
        if "youtube.com" in source or "youtu.be" in source:
            console.print("[green]✅ Предварительная проверка пройдена:[/green] Обнаружена ссылка на YouTube.")
            return True
        else:
            console.print("[bold red]❌ Ошибка:[/bold red] Неподдерживаемый URL. Принимаются только ссылки на YouTube.")
            return False

    file_path = pathlib.Path(source)
    if not file_path.exists():
        console.print(f"[bold red]❌ Ошибка:[/bold red] Файл не найден по пути '{file_path}'.")
        return False

    if not file_path.is_file():
        console.print(f"[bold red]❌ Ошибка:[/bold red] Путь '{file_path}' указывает на директорию, а не на файл.")
        return False

    console.print("[green]✅ Предварительная проверка пройдена:[/green] Обнаружен локальный файл.")
    return True


@app.command()
def version():
    """
    Показывает версию приложения.
    """
    version = importlib.metadata.version("echoscript")
    console.print(f"EchoScript v[bold green]{version}[/bold green]")


@app.command()
def transcribe(
    source: Annotated[
        str,
        typer.Argument(help="Источник для транскрибации: путь к локальному файлу или URL YouTube.")
    ],
    model: Annotated[
        ModelSize,
        typer.Option("--model", "-m", help="Модель Whisper для использования.", case_sensitive=False),
    ] = ModelSize.BASE,
    output_dir: Annotated[
        pathlib.Path,
        typer.Option("--output-dir", "-o", help="Директория для сохранения файла. Если не указана, результат выводится в консоль."),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Формат итогового файла транскрибации.", case_sensitive=False),
    ] = OutputFormat.TXT,
    language: Annotated[
        str,
        typer.Option("--lang", "-l", help="Язык аудио. Определяется автоматически, если не указан."),
    ] = None,
    timestamps: Annotated[
        bool,
        typer.Option("--timestamps", "-t", help="Включить временные метки в итоговый файл."),
    ] = False,
):
    """
    Запускает процесс транскрибации для указанного источника.
    """
    console.print(f"🚀 Запуск транскрибации для: [bold cyan]{source}[/bold cyan]")

    if not pre_flight_check(source):
        raise typer.Exit(code=1)

    from app.services.model_manager import get_model
    from app.services.transcription import TranscriptionService
    from app.adapters.youtube import YoutubeAdapter, FFmpegNotFoundError
    from app.adapters.export import get_exporter

    try:
        whisper_model = get_model(model)
    except Exception:
        raise typer.Exit(code=1)

    audio_path = source
    youtube_adapter = None

    try:
        if source.startswith(("http", "https")):
            try:
                youtube_adapter = YoutubeAdapter()
                audio_path = youtube_adapter.download_audio(url=source)
                if not audio_path:
                    console.print("[bold red]Не удалось получить аудиофайл с YouTube. Прерывание.[/bold red]")
                    raise typer.Exit(code=1)
            except FFmpegNotFoundError as e:
                console.print(f"[bold red]❌ Ошибка зависимости:[/bold red]\n{e}")
                raise typer.Exit(code=1)

        service = TranscriptionService(model=whisper_model)
        transcribed_text = service.transcribe(
            source_path=audio_path, language=language, timestamps=timestamps
        )

        console.print("\n[bold green]✅ Транскрибация завершена.[/bold green]")

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            base_filename = pathlib.Path(audio_path).stem
            output_filename = f"{base_filename}.{output_format.value}"
            destination_path = output_dir / output_filename

            exporter = get_exporter(output_format)
            exporter.export(text=transcribed_text, destination_path=destination_path)
        else:
            console.print(f"📄 Результат:\n[italic]{transcribed_text}[/italic]")

    finally:
        if youtube_adapter:
            youtube_adapter.cleanup()


if __name__ == "__main__":
    app()