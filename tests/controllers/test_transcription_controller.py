"""
Юнит-тесты для TranscriptionController.
"""

import queue
import threading
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.youtube import FFmpegNotFoundError
from app.controllers.transcription_controller import (
    QueueMessage,
    TranscriptionController,
)
from app.core.models import ModelSize, TranscriptionTask
from app.services.realtime_transcription import RealtimeTranscriptionService


def _drain_queue(q: queue.Queue) -> list[QueueMessage]:
    """Вспомогательная функция для извлечения всех сообщений из очереди."""
    messages = []
    while not q.empty():
        messages.append(q.get_nowait())
    return messages


@pytest.fixture
def mock_view():
    """Фикстура, создающая мок-объект для View (App)."""
    view = MagicMock()
    view.file_path_entry = MagicMock()
    view.youtube_entry = MagicMock()
    view.model_menu = MagicMock()
    view.timestamps_checkbox = MagicMock()
    view.result_textbox = MagicMock()
    view.format_menu = MagicMock()
    view.task_segmented_button = MagicMock()
    return view


@pytest.fixture
def controller(mock_view):
    """Фикстура для создания экземпляра TranscriptionController с моком View."""
    yield TranscriptionController(view=mock_view)


# --- Тесты публичных методов и реакции на действия пользователя ---


def test_select_file_happy_path(controller, mock_view):
    """Тест: успешный выбор файла через диалог."""
    with patch(
        "app.controllers.transcription_controller.filedialog.askopenfilename",
        return_value="/fake.mp3",
    ):
        controller.select_file()
        mock_view.file_path_entry.insert.assert_called_with(0, "/fake.mp3")
        mock_view.youtube_entry.delete.assert_called_with(0, "end")


def test_on_youtube_entry_change_clears_file_path(controller, mock_view):
    """Тест: ввод URL в поле YouTube очищает поле выбора файла."""
    mock_view.youtube_entry.get.return_value = "some_url"
    controller.on_youtube_entry_change(None, None, None)
    mock_view.file_path_entry.delete.assert_called_once_with(0, "end")


@patch("app.controllers.transcription_controller.threading.Thread")
def test_start_transcription_starts_thread(mock_thread, controller, mock_view):
    """Тест: успешный запуск транскрипции создает и запускает фоновый поток."""
    mock_view.file_path_entry.get.return_value = "/fake/file.mp3"
    mock_view.model_menu.get.return_value = "tiny"
    mock_view.task_segmented_button.get.return_value = "Транскрибация"
    controller.start_transcription()
    mock_thread.assert_called_once()


def test_start_transcription_no_source(controller):
    """Тест: запуск без источника отправляет ошибку в очередь."""
    controller.view.file_path_entry.get.return_value = ""
    controller.view.youtube_entry.get.return_value = ""
    controller.start_transcription()
    messages = _drain_queue(controller.task_queue)
    assert any("Укажите источник" in msg.status for msg in messages if msg.status)


def test_save_result_no_result(controller):
    """Тест: попытка сохранить пустой результат отправляет сообщение в очередь."""
    controller.last_transcription_result = None
    controller.save_result()
    msg = controller.task_queue.get(timeout=1)
    assert msg.status == "Нечего сохранять."


@patch("app.controllers.transcription_controller.messagebox.showerror")
def test_save_result_srt_error(mock_showerror, controller, mock_view):
    """Тест: ошибка при попытке сохранить в SRT без включенных таймстемпов."""
    controller.last_transcription_result = {"text": "test", "segments": []}
    controller.last_timestamps_enabled = False
    mock_view.format_menu.get.return_value = "srt"
    controller.save_result()
    mock_showerror.assert_called_once()


# --- Тесты потоков выполнения _transcription_worker ---


@patch("app.services.transcription.TranscriptionService")
@patch("whisper.load_model")
@patch("app.services.model_manager.ModelManager")
@patch("app.adapters.local_file.LocalFileAdapter")
def test_worker_success_flow(
    mock_local_adapter, mock_manager, mock_load_model, mock_service, controller
):
    """Тест: "счастливый путь" для _transcription_worker."""
    mock_local_adapter.return_value.process_file.return_value = "/fake/processed.wav"
    mock_manager.return_value.ensure_model_is_available.return_value = "/fake/model.pt"
    mock_service.return_value.transcribe.return_value = {"text": "ok", "segments": []}
    controller.last_timestamps_enabled = False
    params = {
        "is_youtube": False,
        "source": "file",
        "model_size": ModelSize.TINY,
        "task": TranscriptionTask.TRANSCRIBE,
        "cancel_event": threading.Event(),
    }

    controller._transcription_worker(params)

    messages = _drain_queue(controller.task_queue)
    final_status_msg = next(msg for msg in messages if msg.status == "Готово!")
    assert final_status_msg.result_text == "ok"
    assert any(msg.is_done for msg in messages)


def test_worker_known_error_flow(controller):
    """Тест: _transcription_worker корректно обрабатывает известные ошибки."""
    params = {"is_youtube": True, "source": "url"}
    with patch("app.adapters.youtube.YoutubeAdapter") as mock_youtube_adapter:
        mock_youtube_adapter.side_effect = FFmpegNotFoundError("ffmpeg not found")
        controller._transcription_worker(params)

    messages = _drain_queue(controller.task_queue)
    assert any(
        "Ошибка: ffmpeg not found" in msg.status for msg in messages if msg.status
    )
    assert any(msg.is_done for msg in messages)


def test_worker_critical_error_flow(controller):
    """Тест: _transcription_worker корректно обрабатывает критические ошибки."""
    params = {"is_youtube": False, "source": "file"}
    with patch("app.adapters.local_file.LocalFileAdapter") as mock_local_adapter:
        mock_local_adapter.side_effect = ValueError("Something went very wrong")
        controller._transcription_worker(params)

    messages = _drain_queue(controller.task_queue)
    assert any(
        "Критическая ошибка: Something went very wrong" in msg.status
        for msg in messages
        if msg.status
    )
    assert any(msg.is_done for msg in messages)


# --- Тесты вспомогательных методов ---


def test_format_result_for_gui_with_timestamps(controller):
    """Тест: форматирование результата для GUI с включенными таймстемпами."""
    controller.last_timestamps_enabled = True
    result_data = {
        "segments": [
            {"start": 1, "end": 2.5, "text": "Hello"},
            {"start": 3, "end": 4.2, "text": "World"},
        ]
    }
    formatted_text = controller._format_result_for_gui(result_data)
    assert "[00:00:01 -> 00:00:02] Hello" in formatted_text
    assert "[00:00:03 -> 00:00:04] World" in formatted_text


def test_cleanup_resources_handles_exception(controller):
    """Тест: _cleanup_resources не падает и логирует ошибку при сбое."""
    mock_adapter = MagicMock()
    mock_adapter.cleanup.side_effect = Exception("Cleanup failed")
    adapters = {"youtube": mock_adapter, "local": None}

    controller._cleanup_resources(adapters)

    messages = _drain_queue(controller.task_queue)
    assert any(
        "Не удалось очистить временные файлы" in msg.status
        for msg in messages
        if msg.status
    )


# --- Тесты для Real-time транскрипции ---


@patch("app.controllers.transcription_controller.threading.Thread")
def test_toggle_realtime_transcription_starts_recording(
    mock_thread, controller, mock_view
):
    """Тест: toggle_realtime_transcription успешно запускает запись."""
    # Arrange
    controller.is_recording = False
    mock_view.task_segmented_button.get.return_value = "Транскрибация"
    mock_view.mic_menu.get.return_value = "Fake Mic (ID: 1)"
    mock_view.model_menu.get.return_value = "tiny"

    # Act
    controller.toggle_realtime_transcription()

    # Assert
    assert controller.is_recording is True
    mock_view.update_ui_for_recording_start.assert_called_once()
    mock_thread.assert_called_once()
    # Проверяем, что воркер запускается с правильными параметрами
    call_args = mock_thread.call_args
    assert call_args.kwargs["target"] == controller._realtime_worker_start


def test_toggle_realtime_transcription_stops_recording(controller, mock_view):
    """Тест: toggle_realtime_transcription успешно останавливает запись."""
    # Arrange
    controller.is_recording = True
    # "Захватываем" мок в локальную переменную
    mock_service_instance = MagicMock(spec=RealtimeTranscriptionService)
    controller.realtime_service = mock_service_instance

    # Act
    controller.toggle_realtime_transcription()

    # Assert
    assert controller.is_recording is False
    # Выполняем проверку на локальной переменной
    mock_service_instance.stop.assert_called_once()
    assert controller.realtime_service is None
    mock_view.update_ui_for_recording_end.assert_called_once()


@patch("app.controllers.transcription_controller.RealtimeTranscriptionService")
@patch("whisper.load_model")
@patch("app.services.model_manager.ModelManager")
def test_realtime_worker_start_success(
    mock_manager, mock_load_model, mock_realtime_service, controller
):
    """Тест: _realtime_worker_start успешно инициализирует и запускает сервис."""
    # Arrange
    params = {
        "model_size": ModelSize.TINY,
        "task": TranscriptionTask.TRANSCRIBE,
        "mic_id": 1,
    }
    mock_manager.return_value.ensure_model_is_available.return_value = "/fake/model.pt"

    # Act
    controller._realtime_worker_start(params)

    # Assert
    mock_manager.assert_called_once_with(ModelSize.TINY)
    mock_load_model.assert_called_once_with("/fake/model.pt")
    mock_realtime_service.assert_called_once()
    # Проверяем, что у созданного экземпляра сервиса был вызван метод start
    mock_realtime_service.return_value.start.assert_called_once()


@patch("app.services.model_manager.ModelManager")
def test_realtime_worker_start_handles_exception(mock_manager, controller):
    """Тест: _realtime_worker_start обрабатывает исключение и обновляет GUI."""
    # Arrange
    params = {"model_size": ModelSize.TINY, "task": "task", "mic_id": 1}
    mock_manager.side_effect = Exception("Model load failed")
    controller.is_recording = True  # Имитируем состояние "в процессе запуска"

    # Act
    controller._realtime_worker_start(params)

    # Assert
    assert controller.is_recording is False
    messages = _drain_queue(controller.task_queue)
    assert any("Критическая ошибка" in msg.status for msg in messages if msg.status)
    assert any(msg.is_done for msg in messages)
