"""
Интеграционные тесты для YoutubeAdapter.
"""
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yt_dlp

from app.adapters.youtube import YoutubeAdapter, FFmpegNotFoundError


def test_adapter_raises_error_if_ffmpeg_not_found():
    """
    Проверяет, что конструктор вызывает FFmpegNotFoundError, если ffmpeg не найден.
    """
    # Arrange: Мокируем shutil.which, чтобы он "не нашел" ffmpeg
    with patch("shutil.which", return_value=None):
        # Act & Assert: Ожидаем, что будет вызвано наше кастомное исключение
        with pytest.raises(FFmpegNotFoundError, match="необходим ffmpeg"):
            YoutubeAdapter()


@patch("shutil.which", return_value="/fake/path/to/ffmpeg")
def test_download_audio_handles_yt_dlp_error(mock_which):
    """
    Проверяет, что адаптер корректно обрабатывает ошибку загрузки от yt-dlp.
    """
    # Arrange
    adapter = YoutubeAdapter()
    # Мокируем yt_dlp.YoutubeDL, чтобы он вызывал ошибку при загрузке
    with patch("yt_dlp.YoutubeDL") as mock_yt_dlp:
        mock_instance = mock_yt_dlp.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {"title": "Test Video"}
        mock_instance.download.side_effect = yt_dlp.utils.DownloadError(
            "Video unavailable"
        )

        # Act
        result = adapter.download_audio("https://www.youtube.com/watch?v=invalid")

        # Assert
        assert result is None

    adapter.cleanup()


@patch("shutil.which", return_value="/fake/path/to/ffmpeg")
def test_download_audio_success_path(mock_which):
    """
    Проверяет успешный сценарий: ffmpeg найден, видео загружено и сконвертировано.
    """
    # Arrange
    adapter = YoutubeAdapter()
    temp_dir = adapter._temp_dir
    # Путь к файлу, который "скачает" yt-dlp
    source_m4a_path = Path(temp_dir) / "test_video_id.m4a"
    # Путь к файлу, который должен получиться после конвертации
    expected_wav_path = source_m4a_path.with_suffix(".wav")

    # Мокируем yt_dlp и subprocess
    with patch("yt_dlp.YoutubeDL") as mock_yt_dlp, \
         patch("subprocess.run") as mock_subprocess:

        mock_yt_instance = mock_yt_dlp.return_value.__enter__.return_value
        mock_yt_instance.extract_info.return_value = {
            "title": "Test Video", "duration_string": "01:23",
        }

        # Имитируем, что yt-dlp создал .m4a файл
        def fake_download(*args, **kwargs):
            source_m4a_path.touch()
        mock_yt_instance.download.side_effect = fake_download

        # Act
        result = adapter.download_audio("https://www.youtube.com/watch?v=test_video_id")

        # Assert
        # Проверяем, что subprocess.run был вызван для конвертации
        mock_subprocess.assert_called_once()
        # Проверяем, что функция вернула правильный путь к .wav файлу
        assert result == str(expected_wav_path)

    adapter.cleanup()