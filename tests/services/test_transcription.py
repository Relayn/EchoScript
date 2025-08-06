"""
Юнит-тесты для TranscriptionService.
"""
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest

from app.services.transcription import CHUNK_DURATION_SECONDS, TranscriptionService


@pytest.fixture
def mock_whisper_model() -> MagicMock:
    """Фикстура, создающая мок-объект для модели Whisper."""
    model = MagicMock()
    model.transcribe.side_effect = [
        {"text": "Это первая часть. ", "segments": [{"start": 0, "end": 5, "text": " Это первая часть. "}]},
        {"text": "Это вторая часть.", "segments": [{"start": 30, "end": 35, "text": " Это вторая часть."}]},
    ]
    return model


@pytest.fixture
def mock_sound_file():
    """Фикстура, создающая мок для soundfile.SoundFile."""
    fake_samplerate = 16000
    total_duration_seconds = int(CHUNK_DURATION_SECONDS * 1.5)
    fake_audio_data = np.zeros(total_duration_seconds * fake_samplerate)
    chunk_size_frames = CHUNK_DURATION_SECONDS * fake_samplerate

    mock_sf = MagicMock()
    mock_sf.__len__.return_value = len(fake_audio_data)
    mock_sf.samplerate = fake_samplerate
    chunks = [
        fake_audio_data[i: i + chunk_size_frames]
        for i in range(0, len(fake_audio_data), chunk_size_frames)
    ]
    chunks.append(np.array([]))
    mock_sf.read.side_effect = chunks

    with patch("soundfile.SoundFile") as mock_sf_constructor:
        mock_sf_constructor.return_value.__enter__.return_value = mock_sf
        yield mock_sf_constructor


def test_transcribe_without_timestamps(mock_whisper_model, mock_sound_file):
    """Тест: транскрибация без временных меток."""
    service = TranscriptionService(model=mock_whisper_model)
    result = service.transcribe(source_path="/fake/path.wav", language="ru", timestamps=False, progress_callback=None)
    assert result == "Это первая часть. \nЭто вторая часть."


def test_transcribe_with_timestamps(mock_whisper_model, mock_sound_file):
    """Тест: транскрибация с временными метками."""
    service = TranscriptionService(model=mock_whisper_model)
    result = service.transcribe(source_path="/fake/path.wav", language=None, timestamps=True, progress_callback=None)
    expected_output = "[00:00:00 -> 00:00:05] Это первая часть.\n[00:00:30 -> 00:00:35] Это вторая часть."
    assert result == expected_output


def test_transcribe_with_progress_callback(mock_whisper_model, mock_sound_file):
    """Тест: progress_callback вызывается корректное количество раз с верными аргументами."""
    # Arrange
    service = TranscriptionService(model=mock_whisper_model)
    mock_callback = MagicMock()

    # Act
    service.transcribe(source_path="/fake/path.wav", language=None, timestamps=False, progress_callback=mock_callback)

    # Assert
    assert mock_callback.call_count == 2
    mock_callback.assert_has_calls([
        call(1, 2),  # (обработано_чанков, всего_чанков)
        call(2, 2)
    ])