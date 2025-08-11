"""
Этот модуль содержит адаптеры для экспорта транскрибированного текста
в различные форматы файлов.
"""

import abc
import pathlib
from typing import Any, Dict, Type

from rich.console import Console

from app.core.models import OutputFormat

console = Console()

# Константа для сообщения об успешном сохранении
_SUCCESS_SAVE_MESSAGE = "💾 [green]Результат сохранен в:[/green]"


def _format_srt_time(seconds: float) -> str:
    """Конвертирует секунды в формат времени SRT (ЧЧ:ММ:СС,мс)."""
    if seconds < 0:
        raise ValueError("Ожидается неотрицательная временная метка")
    milliseconds = round(seconds * 1000.0)

    hours = int(milliseconds / 3_600_000)
    milliseconds -= hours * 3_600_000

    minutes = int(milliseconds / 60_000)
    milliseconds -= minutes * 60_000

    seconds = int(milliseconds / 1000)
    milliseconds -= seconds * 1000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


class ExportAdapter(abc.ABC):
    """Абстрактный базовый класс для всех адаптеров экспорта."""

    @abc.abstractmethod
    def export(
        self,
        result_data: dict[str, Any],
        destination_path: pathlib.Path,
        silent: bool = True,
    ) -> None:
        """
        Сохраняет данные транскрипции в указанный путь.

        Args:
            result_data: Словарь с результатами от TranscriptionService.
                         Ожидается как минимум ключ "text".
            destination_path: Полный путь к файлу для сохранения.
            silent: Если False, выводит сообщение об успехе в консоль.
        """
        raise NotImplementedError


class TxtExportAdapter(ExportAdapter):
    """Сохраняет транскрипцию в простой текстовый файл (.txt)."""

    def export(
        self,
        result_data: dict[str, Any],
        destination_path: pathlib.Path,
        silent: bool = True,
    ) -> None:
        """Сохраняет текст в файл с расширением .txt."""
        try:
            destination_path.write_text(result_data["text"], encoding="utf-8")
            if not silent:
                console.print(_SUCCESS_SAVE_MESSAGE)
                console.print(f"[bold cyan]{destination_path}[/bold cyan]")
        except IOError as e:
            console.print(f"[bold red]❌ Ошибка при сохранении файла: {e}[/bold red]")


class MdExportAdapter(ExportAdapter):
    """Сохраняет транскрипцию в файл Markdown (.md)."""

    def export(
        self,
        result_data: dict[str, Any],
        destination_path: pathlib.Path,
        silent: bool = True,
    ) -> None:
        """Сохраняет текст в файл с расширением .md."""
        try:
            destination_path.write_text(result_data["text"], encoding="utf-8")
            if not silent:
                console.print(_SUCCESS_SAVE_MESSAGE)
                console.print(f"[bold cyan]{destination_path}[/bold cyan]")
        except IOError as e:
            console.print(f"[bold red]❌ Ошибка при сохранении файла: {e}[/bold red]")


class SrtExportAdapter(ExportAdapter):
    """Сохраняет транскрипцию в файл субтитров SubRip (.srt)."""

    def export(
        self,
        result_data: dict[str, Any],
        destination_path: pathlib.Path,
        silent: bool = True,
    ) -> None:
        """Форматирует сегменты в SRT и сохраняет в файл."""
        srt_content = []
        segments = result_data.get("segments", [])
        for i, segment in enumerate(segments, start=1):
            start_time = _format_srt_time(segment["start"])
            end_time = _format_srt_time(segment["end"])
            text = segment["text"].strip()
            srt_content.append(f"{i}\n{start_time} --> {end_time}\n{text}\n")

        try:
            destination_path.write_text("\n".join(srt_content), encoding="utf-8")
            if not silent:
                console.print(
                    f"{_SUCCESS_SAVE_MESSAGE}\n"
                    f"[bold cyan]{destination_path}[/bold cyan]"
                )
        except IOError as e:
            console.print(f"[bold red]❌ Ошибка при сохранении файла: {e}[/bold red]")


class DocxExportAdapter(ExportAdapter):
    """Сохраняет транскрипцию в файл Microsoft Word (.docx)."""

    def export(
        self,
        result_data: dict[str, Any],
        destination_path: pathlib.Path,
        silent: bool = True,
    ) -> None:
        """Создает .docx файл и сохраняет в него текст."""
        try:
            import docx

            document = docx.Document()
            document.add_paragraph(result_data["text"])
            document.save(str(destination_path))
            if not silent:
                console.print(_SUCCESS_SAVE_MESSAGE)
                console.print(f"[bold cyan]{destination_path}[/bold cyan]")
        except ImportError as e:
            msg = "Для экспорта в .docx требуется библиотека 'python-docx'."
            console.print(f"[bold red]❌ Ошибка: {msg}[/bold red]")
            # В GUI это исключение будет перехвачено и показано пользователю
            raise ValueError(msg) from e
        except IOError as e:
            console.print(f"[bold red]❌ Ошибка при сохранении файла: {e}[/bold red]")


# Словарь-фабрика для выбора нужного адаптера
_EXPORTERS: Dict[OutputFormat, Type[ExportAdapter]] = {
    OutputFormat.TXT: TxtExportAdapter,
    OutputFormat.MD: MdExportAdapter,
    OutputFormat.SRT: SrtExportAdapter,
    OutputFormat.DOCX: DocxExportAdapter,
}


def get_exporter(output_format: OutputFormat) -> ExportAdapter:
    """
    Фабричная функция для получения экземпляра нужного экспорт-адаптера.

    Args:
        output_format: Требуемый формат вывода.

    Returns:
        Экземпляр класса, реализующего ExportAdapter.

    Raises:
        ValueError: Если для указанного формата нет адаптера.
    """
    exporter_class = _EXPORTERS.get(output_format)
    if not exporter_class:
        raise ValueError(f"Не найден адаптер для формата '{output_format}'")
    return exporter_class()
