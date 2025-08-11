"""
Этот модуль отвечает за управление моделями Whisper, включая их
загрузку, кэширование и проверку целостности.
"""

import hashlib
import os
import urllib.request
from typing import Callable, Optional

import whisper

from app.core.models import ModelSize


class ModelManager:
    """Обрабатывает загрузку и кэширование моделей Whisper."""

    def __init__(self, model_size: ModelSize):
        self.model_size = model_size.value
        self._download_root = self._get_download_root()
        self.download_path = os.path.join(self._download_root, f"{self.model_size}.pt")

    def ensure_model_is_available(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Проверяет, доступна ли модель локально. Если нет, загружает ее.
        """
        if not self.is_model_downloaded(log_callback):
            if log_callback:
                log_callback(
                    f"Модель '{self.model_size}' не найдена. Начинаю загрузку..."
                )
            self._download_model(progress_callback, log_callback)
        else:
            if log_callback:
                log_callback(f"Модель '{self.model_size}' уже загружена.")

        return self.download_path

    def is_model_downloaded(
        self, log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """Проверяет, существует ли файл модели и соответствует ли его SHA256."""
        if not os.path.exists(self.download_path):
            return False

        expected_sha256 = whisper._MODELS[self.model_size].split("/")[-2]
        with open(self.download_path, "rb") as f:
            model_bytes = f.read()
        calculated_sha256 = hashlib.sha256(model_bytes).hexdigest()

        if calculated_sha256 != expected_sha256:
            if log_callback:
                log_callback(
                    f"ВНИМАНИЕ: Контрольная сумма локальной модели "
                    f"'{self.model_size}' не совпадает. Файл будет загружен заново."
                )
            os.remove(self.download_path)
            return False
        return True

    def _download_model(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Реализует атомарную загрузку модели и сообщает о прогрессе через callback."""
        url = whisper._MODELS[self.model_size]
        part_path = self.download_path + ".part"

        try:
            with urllib.request.urlopen(url) as source, open(part_path, "wb") as output:  # nosec B310
                total_size = int(source.info().get("Content-Length", 0))
                total_mb = total_size / (1024 * 1024)
                downloaded_bytes = 0
                last_logged_mb = -1

                while True:
                    buffer = source.read(8192)
                    if not buffer:
                        break
                    output.write(buffer)
                    downloaded_bytes += len(buffer)

                    # Обновляем прогресс-бар (часто)
                    if progress_callback:
                        progress_callback(downloaded_bytes, total_size)

                    # Обновляем текстовый статус (реже, раз в мегабайт)
                    current_mb = downloaded_bytes // (1024 * 1024)
                    if log_callback and current_mb > last_logged_mb:
                        log_callback(f"Загрузка: {current_mb:.0f} / {total_mb:.0f} МБ")
                        last_logged_mb = current_mb

            os.rename(part_path, self.download_path)
            if log_callback:
                log_callback(
                    f"Модель '{self.model_size}' успешно загружена и проверена."
                )

        except Exception as e:
            if log_callback:
                log_callback(f"Ошибка при загрузке модели: {e}")
            if os.path.exists(part_path):
                os.remove(part_path)
            raise

    def _get_download_root(self) -> str:
        """Определяет корневую директорию для кэша моделей."""
        default = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
        download_root = os.getenv("XDG_CACHE_HOME", default)
        os.makedirs(download_root, exist_ok=True)
        return download_root


def get_model(
    model_size: ModelSize,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
) -> whisper.Whisper:
    """
    Фабричная функция для получения полностью загруженной модели Whisper.
    Используется в CLI.
    """
    manager = ModelManager(model_size)
    model_path = manager.ensure_model_is_available(progress_callback, log_callback)

    if log_callback:
        log_callback(f"Загрузка модели '{model_size.value}' в память...")

    model = whisper.load_model(model_path)

    if log_callback:
        log_callback(f"Модель '{model_size.value}' готова к работе.")

    return model
