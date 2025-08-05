"""
Этот модуль содержит адаптеры для экспорта транскрибированного текста
в различные форматы файлов.
"""
import abc
import pathlib
from typing import Dict, Type

from rich.console import Console

from app.core.models import OutputFormat

console = Console()


class ExportAdapter(abc.ABC):
    """Абстрактный базовый класс для всех адаптеров экспорта."""

    @abc.abstractmethod
    def export(self, text: str, destination_path: pathlib.Path):
        """
        Сохраняет данный текст в указанный путь.

        Args:
            text: Транскрибированный текст для сохранения.
            destination_path: Полный путь к файлу для сохранения.
        """
        raise NotImplementedError


class TxtExportAdapter(ExportAdapter):
    """Сохраняет транскрипцию в простой текстовый файл (.txt)."""

    def export(self, text: str, destination_path: pathlib.Path):
        """Сохраняет текст в файл с расширением .txt."""
        try:
            destination_path.write_text(text, encoding="utf-8")
            console.print(
                f"💾 [green]Результат сохранен в:[/green] [bold cyan]{destination_path}[/bold cyan]"
            )
        except IOError as e:
            console.print(f"[bold red]❌ Ошибка при сохранении файла: {e}[/bold red]")


class MdExportAdapter(ExportAdapter):
    """Сохраняет транскрипцию в файл Markdown (.md)."""

    def export(self, text: str, destination_path: pathlib.Path):
        """Сохраняет текст в файл с расширением .md."""
        # На данный момент логика идентична TXT, но структура готова
        # для будущих улучшений (например, добавление заголовков).
        try:
            destination_path.write_text(text, encoding="utf-8")
            console.print(
                f"💾 [green]Результат сохранен в:[/green] [bold cyan]{destination_path}[/bold cyan]"
            )
        except IOError as e:
            console.print(f"[bold red]❌ Ошибка при сохранении файла: {e}[/bold red]")


# Словарь-фабрика для выбора нужного адаптера
_EXPORTERS: Dict[OutputFormat, Type[ExportAdapter]] = {
    OutputFormat.TXT: TxtExportAdapter,
    OutputFormat.MD: MdExportAdapter,
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