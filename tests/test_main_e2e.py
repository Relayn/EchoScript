"""
Сквозные (End-to-End) тесты для CLI-интерфейса.
"""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from app.core.models import TranscriptionTask
from app.main import app

# Создаем экземпляр Runner для вызова команд
runner = CliRunner()


def test_transcribe_local_file_to_txt_dir(tmp_path: Path) -> None:
    """
    E2E Тест: Успешная транскрибация локального файла с сохранением в .txt.
    """
    # Arrange
    output_dir = tmp_path / "transcripts"
    fake_audio_file = tmp_path / "audio.wav"
    fake_audio_file.touch()

    with (
        patch("app.main._run_transcription") as mock_run,
        patch("app.main.pre_flight_check", return_value=True),
    ):
        # Act
        result = runner.invoke(
            app,
            [
                "transcribe",
                str(fake_audio_file),
                "--output-dir",
                str(output_dir),
                "--format",
                "txt",
            ],
        )

        # Assert
        assert result.exit_code == 0, f"CLI exited with error: {result.stdout}"
        mock_run.assert_called_once()


def test_transcribe_local_file_to_srt_dir(tmp_path: Path) -> None:
    """
    E2E Тест: Успешная транскрибация локального файла с сохранением в .srt.
    """
    # Arrange
    output_dir = tmp_path / "transcripts"
    fake_audio_file = tmp_path / "audio.wav"
    fake_audio_file.touch()

    with (
        patch("app.main._run_transcription") as mock_run,
        patch("app.main.pre_flight_check", return_value=True),
    ):
        # Act
        result = runner.invoke(
            app,
            [
                "transcribe",
                str(fake_audio_file),
                "--output-dir",
                str(output_dir),
                "--format",
                "srt",
            ],
        )

        # Assert
        assert result.exit_code == 0, f"CLI exited with error: {result.stdout}"
        mock_run.assert_called_once()


def test_translate_task_to_console(tmp_path: Path) -> None:
    """
    E2E Тест: Успешный перевод локального файла с выводом в консоль.
    """
    # Arrange
    fake_audio_file = tmp_path / "audio.wav"
    fake_audio_file.touch()

    with (
        patch("app.main._run_transcription") as mock_run,
        patch("app.main.pre_flight_check", return_value=True),
    ):
        # Act
        result = runner.invoke(
            app, ["transcribe", str(fake_audio_file), "--task", "translate"]
        )

        # Assert
        assert result.exit_code == 0, f"CLI exited with error: {result.stdout}"
        # Проверяем, что сервис был вызван с правильной задачей
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args.kwargs["task"] == TranscriptionTask.TRANSLATE


def test_transcribe_youtube_url_to_console() -> None:
    """
    E2E Тест: Успешная транскрибация YouTube URL с выводом в консоль.
    """
    # Arrange
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    with (
        patch("app.main._run_transcription") as mock_run,
        patch("app.main.pre_flight_check", return_value=True),
    ):
        # Act
        result = runner.invoke(app, ["transcribe", youtube_url])

        # Assert
        assert result.exit_code == 0, f"CLI exited with error: {result.stdout}"
        mock_run.assert_called_once()


def test_transcribe_file_not_found_error() -> None:
    """
    E2E Тест: Приложение корректно обрабатывает ошибку несуществующего файла.
    """
    # Arrange
    non_existent_file = "/path/to/non_existent_file.mp3"

    # Act
    result = runner.invoke(app, ["transcribe", non_existent_file])

    # Assert
    assert result.exit_code == 1
    assert "Файл не найден по пути" in result.stdout
