"""
Этот модуль отвечает за управление моделями Whisper, включая их
загрузку, кэширование и проверку целостности.
"""
import base64
import gzip
import hashlib
import os
import pathlib
import tempfile
from typing import Dict

import torch
import whisper
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.console import Console
import urllib.request

from app.core.models import ModelSize

console = Console()


class ModelManager:
    """Обрабатывает загрузку и кэширование моделей Whisper."""

    def __init__(self, model_size: ModelSize):
        self.model_size = model_size.value
        self._download_root = self._get_download_root()
        self.download_path = os.path.join(self._download_root, f"{self.model_size}.pt")

    def ensure_model_is_available(self) -> str:
        """
        Проверяет, доступна ли модель локально. Если нет, загружает ее
        с прогресс-баром.

        Returns:
            Путь к загруженному файлу модели.
        """
        if not self.is_model_downloaded():
            console.print(
                f"[yellow]⏳ Модель '{self.model_size}' не найдена. Начинаю загрузку...[/yellow]"
            )
            self._download_model()
        else:
            console.print(f"[green]✅ Модель '{self.model_size}' уже загружена.[/green]")

        return self.download_path

    def is_model_downloaded(self) -> bool:
        """Проверяет, существует ли файл модели и соответствует ли его SHA256."""
        if not os.path.exists(self.download_path):
            return False

        expected_sha256 = whisper._MODELS[self.model_size].split("/")[-2]

        with open(self.download_path, "rb") as f:
            model_bytes = f.read()

        calculated_sha256 = hashlib.sha256(model_bytes).hexdigest()

        if calculated_sha256 != expected_sha256:
            console.print(
                f"[bold yellow]⚠️ Внимание:[/bold yellow] Контрольная сумма локальной модели "
                f"'{self.model_size}' не совпадает. Файл будет загружен заново."
            )
            os.remove(self.download_path)
            return False

        return True

    def _download_model(self):
        """
        Реализует атомарную загрузку модели с использованием rich.progress.
        """
        url = whisper._MODELS[self.model_size]
        part_path = self.download_path + ".part"

        try:
            with urllib.request.urlopen(url) as source, open(part_path, "wb") as output:
                with Progress(
                        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                        BarColumn(bar_width=None),
                        "[progress.percentage]{task.percentage:>3.1f}%",
                        "•",
                        DownloadColumn(),
                        "•",
                        TransferSpeedColumn(),
                        "•",
                        TimeRemainingColumn(),
                ) as progress:
                    task = progress.add_task(
                        "download",
                        total=int(source.info().get("Content-Length")),
                        filename=f"{self.model_size}.pt",
                    )
                    while True:
                        buffer = source.read(8192)
                        if not buffer:
                            break
                        output.write(buffer)
                        progress.update(task, advance=len(buffer))

            os.rename(part_path, self.download_path)
            console.print(f"[green]✅ Модель '{self.model_size}' успешно загружена и проверена.[/green]")

        except Exception as e:
            console.print(f"[bold red]❌ Ошибка при загрузке модели: {e}[/bold red]")
            if os.path.exists(part_path):
                os.remove(part_path)
            raise

    def _get_download_root(self) -> str:
        """Определяет корневую директорию для кэша моделей."""
        default = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
        download_root = os.getenv("XDG_CACHE_HOME", default)
        os.makedirs(download_root, exist_ok=True)
        return download_root


def get_model(model_size: ModelSize) -> whisper.Whisper:
    """
    Фабричная функция для получения полностью загруженной модели Whisper.
    """
    manager = ModelManager(model_size)
    model_path = manager.ensure_model_is_available()

    console.print(f"🧠 Загрузка модели '{model_size.value}' в память...")
    model = whisper.load_model(model_path)
    console.print(f"[green]✅ Модель '{model_size.value}' готова к работе.[/green]")
    return model