"""
Юнит-тесты для адаптеров экспорта и фабричной функции.
"""
import pathlib
import pytest

from app.adapters.export import get_exporter, MdExportAdapter, TxtExportAdapter
from app.core.models import OutputFormat


def test_txt_export_adapter_saves_file(tmp_path: pathlib.Path):
    """
    Проверяет, что TxtExportAdapter корректно сохраняет текстовый файл.
    """
    # Arrange
    adapter = TxtExportAdapter()
    text_content = "Hello, world!"
    destination_file = tmp_path / "output.txt"

    # Act
    adapter.export(text=text_content, destination_path=destination_file)

    # Assert
    assert destination_file.exists()
    assert destination_file.read_text(encoding="utf-8") == text_content


def test_md_export_adapter_saves_file(tmp_path: pathlib.Path):
    """
    Проверяет, что MdExportAdapter корректно сохраняет markdown файл.
    """
    # Arrange
    adapter = MdExportAdapter()
    text_content = "# Hello\n\nThis is markdown."
    destination_file = tmp_path / "output.md"

    # Act
    adapter.export(text=text_content, destination_path=destination_file)

    # Assert
    assert destination_file.exists()
    assert destination_file.read_text(encoding="utf-8") == text_content


def test_get_exporter_returns_correct_adapter():
    """
    Проверяет, что фабрика get_exporter возвращает правильные экземпляры адаптеров.
    """
    # Act
    txt_adapter = get_exporter(OutputFormat.TXT)
    md_adapter = get_exporter(OutputFormat.MD)

    # Assert
    assert isinstance(txt_adapter, TxtExportAdapter)
    assert isinstance(md_adapter, MdExportAdapter)


def test_get_exporter_raises_error_for_unknown_format():
    """
    Проверяет, что get_exporter вызывает ValueError для неизвестного формата.
    """
    # Act & Assert
    with pytest.raises(ValueError, match="Не найден адаптер для формата 'invalid_format'"):
        get_exporter("invalid_format")