"""
Юнит-тесты для TranscriptionController.
"""
from unittest.mock import MagicMock, patch, call

import pytest

from app.controllers.transcription_controller import TranscriptionController
from app.core.models import ModelSize, OutputFormat


@pytest.fixture
def mock_view():
    """Фикстура, создающая мок-объект для View (App)."""
    view = MagicMock()
    # Настраиваем моки для всех виджетов, к которым обращается контроллер
    view.file_path_entry = MagicMock()
    view.youtube_entry = MagicMock()
    view.model_menu = MagicMock()
    view.timestamps_checkbox = MagicMock()
    view.result_textbox = MagicMock()
    view.format_menu = MagicMock()
    return view


@pytest.fixture
def controller(mock_view):
    """Фикстура для создания экземпляра TranscriptionController с моком View."""
    yield TranscriptionController(view=mock_view)


def test_select_file_updates_view(controller, mock_view):
    """Тест: выбор файла через диалог корректно обновляет GUI."""
    # Arrange
    fake_path = "/path/to/fake/audio.mp3"
    with patch("app.controllers.transcription_controller.filedialog.askopenfilename",
               return_value=fake_path) as mock_dialog:
        # Act
        controller.select_file()
        # Assert
        mock_dialog.assert_called_once()
        assert mock_view.file_path_entry.configure.call_args_list == [call(state="normal"), call(state="disabled")]
        mock_view.file_path_entry.delete.assert_called_once_with(0, "end")
        mock_view.file_path_entry.insert.assert_called_once_with(0, fake_path)
        mock_view.youtube_entry.delete.assert_called_once_with(0, "end")


def test_start_transcription_no_source(controller):
    """Тест: запуск транскрипции без указания источника отправляет ошибку в очередь."""
    # Arrange
    controller.view.file_path_entry.get.return_value = ""
    controller.view.youtube_entry.get.return_value = ""
    # Act
    controller.start_transcription()
    # Assert
    message = controller.task_queue.get_nowait()
    assert "Укажите источник" in message.status
    final_message = controller.task_queue.get_nowait()
    assert final_message.is_done is True


@patch("app.controllers.transcription_controller.threading.Thread")
def test_start_transcription_starts_thread(mock_thread, controller, mock_view):
    """Тест: успешный запуск транскрипции создает и запускает фоновый поток."""
    # Arrange
    mock_view.file_path_entry.get.return_value = "/fake/file.mp3"
    mock_view.model_menu.get.return_value = "tiny"
    # Act
    controller.start_transcription()
    # Assert
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()
    controller.view.update_ui_for_task_start.assert_called_once()


def test_transcription_worker_file_path(controller):
    """Тест: воркер корректно обрабатывает локальный файл и кладет сообщения в очередь."""
    # Arrange
    params = {
        "source": "/fake/audio.mp3",
        "is_youtube": False,
        "model_size": ModelSize.TINY,
        "timestamps": False,
    }
    # Мокируем зависимости там, где они ОПРЕДЕЛЕНЫ, а не там, где они импортируются.
    # Это самый надежный способ для отложенных импортов.
    with patch("app.adapters.local_file.LocalFileAdapter") as mock_local_adapter_class, \
         patch("app.services.model_manager.ModelManager") as mock_model_manager_class, \
         patch("app.services.transcription.TranscriptionService") as mock_service_class, \
         patch("whisper.load_model") as mock_load_model:

        # Настраиваем моки для каждого класса
        mock_local_adapter_instance = MagicMock()
        mock_local_adapter_instance.process_file.return_value = "/fake/processed.wav"
        mock_local_adapter_class.return_value = mock_local_adapter_instance

        mock_model_manager_instance = MagicMock()
        mock_model_manager_instance.ensure_model_is_available.return_value = "/fake/model.pt"
        mock_model_manager_class.return_value = mock_model_manager_instance

        mock_service_instance = MagicMock()
        mock_service_instance.transcribe.return_value = "Тестовый текст."
        mock_service_class.return_value = mock_service_instance

        # Act
        controller._transcription_worker(params)

        # Assert
        mock_local_adapter_class.assert_called_once()
        mock_model_manager_class.assert_called_once_with(ModelSize.TINY)
        mock_model_manager_instance.ensure_model_is_available.assert_called_once()
        mock_load_model.assert_called_once_with("/fake/model.pt")
        mock_service_class.assert_called_once()
        mock_service_instance.transcribe.assert_called_once()


@patch("app.controllers.transcription_controller.get_exporter")
def test_save_result(mock_get_exporter, controller, mock_view):
    """Тест: сохранение результата вызывает диалог и экспортер."""
    # Arrange
    mock_view.result_textbox.get.return_value = "Результат для сохранения"
    mock_view.format_menu.get.return_value = "txt"
    fake_save_path = "/path/to/save.txt"

    mock_exporter_instance = MagicMock()
    mock_get_exporter.return_value = mock_exporter_instance

    with patch("app.controllers.transcription_controller.filedialog.asksaveasfilename",
               return_value=fake_save_path) as mock_dialog:
        # Act
        controller.save_result()
        # Assert
        mock_dialog.assert_called_once()
        mock_get_exporter.assert_called_with(OutputFormat.TXT)
        mock_exporter_instance.export.assert_called_once()

        message = controller.task_queue.get_nowait()
        assert "Файл успешно сохранен" in message.status