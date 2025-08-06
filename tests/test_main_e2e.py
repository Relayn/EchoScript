"""
Сквозные (End-to-End) тесты для CLI-интерфейса.
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from app.main import app

# Создаем экземпляр Runner для вызова команд
runner = CliRunner()


def test_transcribe_local_file_to_output_dir(tmp_path: Path):
    """
    E2E Тест: Успешная транскрибация локального файла с сохранением в директорию.
    """
    # Arrange
    output_dir = tmp_path / "transcripts"
    fake_audio_file = tmp_path / "audio.wav"
    fake_audio_file.touch()

    # Патчим зависимости там, где они ОПРЕДЕЛЕНЫ
    with patch("app.services.model_manager.get_model"), \
         patch("app.services.transcription.TranscriptionService") as mock_service_class:

        mock_service_instance = MagicMock()
        mock_service_instance.transcribe.return_value = "Это тестовый текст."
        mock_service_class.return_value = mock_service_instance

        # Act
        result = runner.invoke(app, [
            "transcribe",
            str(fake_audio_file),
            "--output-dir", str(output_dir),
            "--model", "tiny"
        ])

        # Assert
        assert result.exit_code == 0
        assert "Транскрибация завершена" in result.stdout
        assert "Результат сохранен в" in result.stdout

        expected_output_file = output_dir / "audio.txt"
        assert expected_output_file.exists()
        assert expected_output_file.read_text(encoding="utf-8") == "Это тестовый текст."


def test_transcribe_youtube_url_to_console():
    """
    E2E Тест: Успешная транскрибация YouTube URL с выводом в консоль.
    """
    # Arrange
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    fake_audio_path = "/tmp/fake_youtube_audio.m4a"

    # Патчим зависимости там, где они ОПРЕДЕЛЕНЫ
    with patch("app.services.model_manager.get_model"), \
         patch("app.adapters.youtube.YoutubeAdapter") as mock_youtube_adapter, \
         patch("app.services.transcription.TranscriptionService") as mock_service_class:

        mock_youtube_adapter.return_value.download_audio.return_value = fake_audio_path
        mock_service_class.return_value.transcribe.return_value = "Never gonna give you up"

        # Act
        result = runner.invoke(app, ["transcribe", youtube_url])

        # Assert
        assert result.exit_code == 0
        assert "Транскрибация завершена" in result.stdout
        assert "Never gonna give you up" in result.stdout


def test_transcribe_file_not_found_error():
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