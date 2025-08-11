"""
Юнит-тесты для модуля управления конфигурацией (app.core.config).
"""

import pathlib
from unittest.mock import patch

import pytest

from app.core import config


@pytest.fixture
def mock_config_dir(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> pathlib.Path:
    """
    Фикстура для перенаправления конфиг-файла во временную директорию.
    """
    test_config_dir = tmp_path / "test_config"
    test_config_dir.mkdir()
    monkeypatch.setattr(config, "APP_CONFIG_DIR", test_config_dir)
    return test_config_dir


def test_save_and_load_language_success(mock_config_dir: pathlib.Path) -> None:
    """
    Тест: Успешное сохранение и последующая загрузка языка.
    """
    # Arrange
    lang_code = "en_US"
    # Используем новую функцию для получения пути внутри теста
    expected_file = config._get_lang_config_path()

    # Act
    config.save_language(lang_code)
    loaded_lang = config.load_language()

    # Assert
    assert expected_file.exists()
    assert expected_file.read_text(encoding="utf-8") == lang_code
    assert loaded_lang == lang_code


def test_load_language_file_not_exists(mock_config_dir: pathlib.Path) -> None:
    """
    Тест: Загрузка языка, когда конфигурационный файл не существует.
    Ожидание: Должен вернуться None.
    """
    # Act
    loaded_lang = config.load_language()

    # Assert
    assert loaded_lang is None


def test_save_language_handles_io_error(mock_config_dir: pathlib.Path) -> None:
    """
    Тест: save_language не вызывает исключение при ошибке записи.
    """
    # Arrange
    with patch.object(pathlib.Path, "write_text", side_effect=IOError("Disk full")):
        # Act & Assert
        try:
            config.save_language("ru_RU")
        except IOError:
            pytest.fail("IOError не должна была быть проброшена из save_language")


def test_load_language_handles_io_error(mock_config_dir: pathlib.Path) -> None:
    """
    Тест: load_language возвращает None при ошибке чтения.
    """
    # Arrange
    config._get_lang_config_path().touch()
    with patch.object(
        pathlib.Path, "read_text", side_effect=IOError("Permission denied")
    ):
        # Act
        loaded_lang = config.load_language()

        # Assert
        assert loaded_lang is None
