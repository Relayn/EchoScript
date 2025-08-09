"""
Юнит-тесты для адаптеров экспорта и фабричной функции.
"""

import pathlib

import pytest

from app.adapters.export import (
    MdExportAdapter,
    SrtExportAdapter,
    TxtExportAdapter,
    get_exporter,
)
from app.core.models import OutputFormat


def test_txt_export_adapter_saves_file(tmp_path: pathlib.Path):
    """
    Проверяет, что TxtExportAdapter корректно сохраняет текстовый файл.
    """
    adapter = TxtExportAdapter()
    result_data = {"text": "Hello, world!"}
    destination_file = tmp_path / "output.txt"

    adapter.export(result_data=result_data, destination_path=destination_file)

    assert destination_file.exists()
    assert destination_file.read_text(encoding="utf-8") == "Hello, world!"


def test_md_export_adapter_saves_file(tmp_path: pathlib.Path):
    """
    Проверяет, что MdExportAdapter корректно сохраняет markdown файл.
    """
    adapter = MdExportAdapter()
    result_data = {"text": "# Hello\n\nThis is markdown."}
    destination_file = tmp_path / "output.md"

    adapter.export(result_data=result_data, destination_path=destination_file)

    assert destination_file.exists()
    assert (
        destination_file.read_text(encoding="utf-8") == "# Hello\n\nThis is markdown."
    )


def test_srt_export_adapter_saves_file(tmp_path: pathlib.Path):
    """
    Проверяет, что SrtExportAdapter корректно сохраняет SRT файл.
    """
    adapter = SrtExportAdapter()
    result_data = {
        "text": "First line. Second line.",
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "First line."},
            {"start": 3.1, "end": 5.8, "text": "Second line."},
        ],
    }
    destination_file = tmp_path / "output.srt"

    adapter.export(result_data=result_data, destination_path=destination_file)

    content = destination_file.read_text(encoding="utf-8")
    assert "1\n00:00:00,000 --> 00:00:02,500\nFirst line.\n" in content
    assert "2\n00:00:03,100 --> 00:00:05,800\nSecond line.\n" in content


def test_get_exporter_returns_correct_adapter():
    """
    Проверяет, что фабрика get_exporter возвращает правильные экземпляры адаптеров.
    """
    txt_adapter = get_exporter(OutputFormat.TXT)
    md_adapter = get_exporter(OutputFormat.MD)
    srt_adapter = get_exporter(OutputFormat.SRT)

    assert isinstance(txt_adapter, TxtExportAdapter)
    assert isinstance(md_adapter, MdExportAdapter)
    assert isinstance(srt_adapter, SrtExportAdapter)


def test_get_exporter_raises_error_for_unknown_format():
    """
    Проверяет, что get_exporter вызывает ValueError для неизвестного формата.
    """
    with pytest.raises(
        ValueError, match="Не найден адаптер для формата 'invalid_format'"
    ):
        get_exporter("invalid_format")
