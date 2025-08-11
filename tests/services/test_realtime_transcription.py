"""
Юнит-тесты для RealtimeTranscriptionService.
"""

import threading
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.realtime_transcription import (
    DTYPE,
    PROCESSING_QUEUE_SIZE,
    RealtimeTranscriptionService,
)


@pytest.fixture
def mock_model() -> MagicMock:
    """Фикстура для мока модели Whisper."""
    model = MagicMock()
    model.transcribe.return_value = {"text": "test"}
    return model


@pytest.fixture
def mock_callbacks() -> dict[str, MagicMock]:
    """Фикстура для мока колбэков."""
    return {"result": MagicMock(), "status": MagicMock()}


@pytest.fixture
def service(
    mock_model: MagicMock, mock_callbacks: dict[str, MagicMock]
) -> RealtimeTranscriptionService:
    """Фикстура для создания экземпляра сервиса."""
    return RealtimeTranscriptionService(
        model=mock_model,
        device_id=1,
        task="transcribe",
        result_callback=mock_callbacks["result"],
        status_callback=mock_callbacks["status"],
    )


@patch("sounddevice.InputStream")
@patch("threading.Thread")
def test_start_initializes_stream_and_thread(
    mock_thread_class: MagicMock,
    mock_stream_class: MagicMock,
    service: RealtimeTranscriptionService,
) -> None:
    """Тест: метод start() корректно инициализирует и запускает поток и стрим."""
    # Arrange
    mock_thread_instance = mock_thread_class.return_value
    mock_stream_instance = mock_stream_class.return_value

    # Act
    service.start()

    # Assert
    mock_thread_class.assert_called_once_with(target=service._processing_worker)
    mock_thread_instance.start.assert_called_once()
    mock_stream_class.assert_called_once()
    mock_stream_instance.start.assert_called_once()
    assert not service._stop_event.is_set()


@patch("sounddevice.InputStream")
@patch("threading.Thread")
def test_stop_stops_stream_and_thread(
    mock_thread_class: MagicMock,
    mock_stream_class: MagicMock,
    service: RealtimeTranscriptionService,
) -> None:
    """Тест: метод stop() корректно останавливает поток и стрим."""
    # Arrange
    # "Захватываем" моки в локальные переменные до вызова тестируемого метода
    mock_stream_instance = mock_stream_class.return_value
    mock_thread_instance = mock_thread_class.return_value
    service._stream = mock_stream_instance
    service._processing_thread = mock_thread_instance

    # Act
    service.stop()

    # Assert
    # Проверяем вызовы на локальных переменных, а не на атрибутах сервиса
    assert service._stop_event.is_set()
    mock_stream_instance.stop.assert_called_once()
    mock_stream_instance.close.assert_called_once()
    mock_thread_instance.join.assert_called_once()


def test_processing_worker_transcribes_and_calls_callbacks(
    service: RealtimeTranscriptionService,
    mock_model: MagicMock,
    mock_callbacks: dict[str, MagicMock],
) -> None:
    """
    Тест: рабочий поток правильно обрабатывает очередь, вызывает модель
    и передает результат в колбэки.
    """
    # Arrange
    # Помещаем в очередь достаточно данных для одного цикла обработки
    fake_audio_chunk = np.zeros((PROCESSING_QUEUE_SIZE,), dtype=DTYPE)
    service._audio_queue.put(fake_audio_chunk)

    # Запускаем воркер в отдельном потоке, чтобы он мог выйти из цикла
    def worker_wrapper() -> None:
        service._processing_worker()

    thread = threading.Thread(target=worker_wrapper)
    thread.start()

    # Даем воркеру время на обработку
    thread.join(timeout=2)

    # Останавливаем сервис, чтобы воркер точно завершился
    service._stop_event.set()
    thread.join(timeout=1)

    # Assert
    mock_model.transcribe.assert_called_once()
    mock_callbacks["status"].assert_any_call("Обработка фрагмента...")
    mock_callbacks["result"].assert_called_with("test")


def test_audio_callback_puts_data_in_queue(
    service: RealtimeTranscriptionService,
) -> None:
    """Тест: аудио-колбэк помещает данные в очередь."""
    # Arrange
    rng = np.random.default_rng(seed=42)
    fake_indata = rng.random((1024, 1)).astype(DTYPE)

    # Act
    service._audio_callback(fake_indata, frames=1024, time=None, status=None)

    # Assert
    assert service._audio_queue.qsize() == 1
    queued_data = service._audio_queue.get()
    np.testing.assert_array_equal(fake_indata, queued_data)
