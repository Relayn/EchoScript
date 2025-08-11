"""
Юнит-тесты для LocalFileAdapter.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.local_file import LocalFileAdapter
from app.adapters.youtube import FFmpegNotFoundError


@patch("shutil.which", return_value="/fake/path/to/ffmpeg")
def test_process_file_success(mock_which: MagicMock, tmp_path: Path) -> None:
    """
    Тест: Успешная конвертация локального файла.
    """
    # Arrange
    adapter = LocalFileAdapter()
    source_file = tmp_path / "audio.mp4"
    source_file.touch()
    expected_output_path = os.path.join(adapter._temp_dir, f"{source_file.stem}.wav")

    with patch("subprocess.run") as mock_subprocess:
        mock_subprocess.return_value = MagicMock(check_returncode=lambda: None)

        # Act
        result_path = adapter.process_file(str(source_file))

        # Assert
        mock_subprocess.assert_called_once()
        # Проверяем, что команда содержит правильные пути и параметры
        cmd_list = mock_subprocess.call_args[0][0]
        assert cmd_list[0] == "/fake/path/to/ffmpeg"
        assert cmd_list[2] == str(source_file)
        assert cmd_list[-1] == expected_output_path
        assert result_path == expected_output_path

    adapter.cleanup()


def test_adapter_raises_error_if_ffmpeg_not_found() -> None:
    """
    Тест: Конструктор вызывает FFmpegNotFoundError, если ffmpeg не найден.
    """
    with patch("shutil.which", return_value=None):
        with pytest.raises(FFmpegNotFoundError, match="необходим ffmpeg"):
            LocalFileAdapter()


@patch("shutil.which", return_value="/fake/path/to/ffmpeg")
def test_process_file_raises_error_on_ffmpeg_failure(
    mock_which: MagicMock, tmp_path: Path
) -> None:
    """
    Тест: process_file вызывает IOError, если ffmpeg завершается с ошибкой.
    """
    # Arrange
    adapter = LocalFileAdapter()
    source_file = tmp_path / "audio.mp4"
    source_file.touch()

    with patch("subprocess.run") as mock_subprocess:
        # Имитируем ошибку выполнения процесса
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, "ffmpeg", stderr="ffmpeg error"
        )

        # Act & Assert
        with pytest.raises(IOError, match="Не удалось обработать файл"):
            adapter.process_file(str(source_file))

    adapter.cleanup()
