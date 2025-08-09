"""
Юнит-тесты для вспомогательных функций.
"""

import os
from unittest.mock import patch

from app.core.utils import find_ffmpeg_path


def test_find_ffmpeg_path_dev_mode():
    """Тест: в режиме разработки (не frozen) используется shutil.which."""
    # create=True нужно, чтобы можно было патчить несуществующий атрибут
    with (
        patch("sys.frozen", False, create=True),
        patch("shutil.which", return_value="/usr/bin/ffmpeg") as mock_which,
    ):
        assert find_ffmpeg_path() == "/usr/bin/ffmpeg"
        mock_which.assert_called_once_with("ffmpeg")


def test_find_ffmpeg_path_frozen_mode_found():
    """Тест: в frozen-режиме путь к ffmpeg успешно находится внутри пакета."""
    executable_path = "/path/to/app/gui_main.exe"
    expected_path = os.path.join(
        os.path.dirname(executable_path), "ffmpeg", "ffmpeg.exe"
    )

    with (
        patch("sys.executable", executable_path),
        patch("sys.frozen", True, create=True),
        patch("os.path.exists", return_value=True) as mock_exists,
        patch("shutil.which") as mock_which,
    ):
        assert find_ffmpeg_path() == expected_path
        mock_exists.assert_called_once_with(expected_path)
        mock_which.assert_not_called()  # shutil.which не должен вызываться


def test_find_ffmpeg_path_frozen_mode_fallback():
    """Тест: в frozen-режиме, если ffmpeg не найден, используется fallback."""
    executable_path = "/path/to/app/gui_main.exe"

    with (
        patch("sys.executable", executable_path),
        patch("sys.frozen", True, create=True),
        patch("os.path.exists", return_value=False),
        patch("shutil.which", return_value="/usr/bin/ffmpeg") as mock_which,
    ):
        assert find_ffmpeg_path() == "/usr/bin/ffmpeg"
        mock_which.assert_called_once_with("ffmpeg")
