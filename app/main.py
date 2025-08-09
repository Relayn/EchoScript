"""
Этот модуль определяет интерфейс командной строки (CLI) для EchoScript.
Он использует Typer для создания удобного и надежного инструмента.
"""

import importlib.metadata
import pathlib
import threading

import typer
from rich.console import Console
from typing_extensions import Annotated

from app.core.models import ModelSize, OutputFormat, TranscriptionTask

app = typer.Typer(
    name="echoscript",
    help="Утилита для транскрибации аудио/видео и ссылок YouTube с помощью Whisper.",
    add_completion=False,
    rich_markup_mode="markdown",
    no_args_is_help=True,
)

console = Console()


def pre_flight_check(source: str) -> bool:
    """
    Выполняет предварительную проверку источника.
    """
    if source.startswith(("http://", "https://")):
        if "youtube.com" in source or "youtu.be" in source:
            console.print(
                "[green]✅ Предварительная проверка:[/green] "
                "Обнаружена ссылка на YouTube."
            )
            return True
        else:
            console.print(
                "[bold red]❌ Ошибка:[/bold red] Неподдерживаемый URL. "
                "Принимаются только ссылки на YouTube."
            )
            return False

    file_path = pathlib.Path(source)
    if not file_path.exists():
        console.print(
            f"[bold red]❌ Ошибка:[/bold red] Файл не найден по пути '{file_path}'."
        )
        return False

    if not file_path.is_file():
        console.print(
            f"[bold red]❌ Ошибка:[/bold red] Путь '{file_path}' "
            f"указывает на директорию."
        )
        return False

    console.print(
        "[green]✅ Предварительная проверка:[/green] Обнаружен локальный файл."
    )
    return True


@app.command()
def version():
    """Показывает версию приложения."""
    version_str = importlib.metadata.version("echoscript")
    console.print(f"EchoScript v[bold green]{version_str}[/bold green]")


def _run_transcription(
    source: str,
    model_size: ModelSize,
    output_dir: pathlib.Path | None,
    output_format: OutputFormat,
    language: str | None,
    task: TranscriptionTask,
):
    """Основная логика транскрибации, вынесенная из команды Typer."""
    from rich.progress import (
        BarColumn,
        DownloadColumn,
        MofNCompleteColumn,
        Progress,
        TextColumn,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )

    from app.adapters.export import get_exporter
    from app.adapters.youtube import FFmpegNotFoundError, YoutubeAdapter
    from app.services.model_manager import get_model
    from app.services.transcription import TranscriptionService

    download_progress = Progress(
        TextColumn("[bold blue]Загрузка модели...[/]"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        transient=True,
    )

    def download_callback(downloaded, total):
        if not download_progress.tasks:
            download_progress.add_task("download", total=total)
        download_progress.update(download_progress.tasks.id, completed=downloaded)

    try:
        whisper_model = get_model(
            model_size=model_size,
            progress_callback=download_callback,
            log_callback=console.print,
        )
    except Exception as e:
        console.print(
            f"[bold red]❌ Критическая ошибка при загрузке модели: {e}[/bold red]"
        )
        raise typer.Exit(code=1) from e

    audio_path = source
    youtube_adapter = None

    try:
        if source.startswith(("http", "https")):
            try:
                youtube_adapter = YoutubeAdapter()
                audio_path = youtube_adapter.download_audio(url=source)
                if not audio_path:
                    console.print(
                        "[bold red]Не удалось получить аудиофайл с YouTube.[/bold red]"
                    )
                    raise typer.Exit(code=1)
            except FFmpegNotFoundError as e:
                console.print(f"[bold red]❌ Ошибка зависимости:[/bold red]\n{e}")
                raise typer.Exit(code=1) from e

        service = TranscriptionService(model=whisper_model)
        transcription_progress = Progress(
            TextColumn("[cyan]Транскрибация...[/]"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            transient=True,
        )

        def transcription_callback(processed, total):
            if not transcription_progress.tasks:
                transcription_progress.add_task("transcribe", total=total)
            transcription_progress.update(
                transcription_progress.tasks.id, completed=processed
            )

        with transcription_progress:
            cancel_event = threading.Event()
            result_data = service.transcribe(
                source_path=audio_path,
                language=language,
                task=task,
                cancel_event=cancel_event,
                progress_callback=transcription_callback,
            )

        console.print("\n[bold green]✅ Транскрибация завершена.[/bold green]")

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            base_filename = pathlib.Path(audio_path).stem
            output_filename = f"{base_filename}.{output_format.value}"
            destination_path = output_dir / output_filename
            exporter = get_exporter(output_format)
            exporter.export(
                result_data=result_data, destination_path=destination_path, silent=False
            )
        else:
            console.print(f"📄 Результат:\n[italic]{result_data['text']}[/italic]")

    finally:
        if youtube_adapter:
            youtube_adapter.cleanup()


@app.command()
def transcribe(
    source: Annotated[
        str, typer.Argument(help="Источник: путь к файлу или URL YouTube.")
    ],
    model: Annotated[
        ModelSize,
        typer.Option(
            "--model",
            "-m",
            help="Модель Whisper для использования.",
            case_sensitive=False,
        ),
    ] = ModelSize.BASE,
    output_dir: Annotated[
        pathlib.Path,
        typer.Option(
            "--output-dir", "-o", help="Директория для сохранения результата."
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format", "-f", help="Формат итогового файла.", case_sensitive=False
        ),
    ] = OutputFormat.TXT,
    language: Annotated[
        str,
        typer.Option("--lang", "-l", help="Язык аудио (определяется автоматически)."),
    ] = None,
    task: Annotated[
        TranscriptionTask,
        typer.Option(
            "--task", help="Задача: транскрибация или перевод.", case_sensitive=False
        ),
    ] = TranscriptionTask.TRANSCRIBE,
):
    """Запускает процесс транскрибации для указанного источника."""
    console.print(f"🚀 Запуск транскрибации для: [bold cyan]{source}[/bold cyan]")

    if not pre_flight_check(source):
        raise typer.Exit(code=1)

    _run_transcription(
        source=source,
        model_size=model,
        output_dir=output_dir,
        output_format=output_format,
        language=language,
        task=task,
    )


if __name__ == "__main__":
    app()
