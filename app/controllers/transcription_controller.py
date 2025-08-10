"""
Контроллер, управляющий логикой транскрипции и состоянием GUI.
Этот класс является ViewModel в архитектуре MVVM.
"""

import pathlib
import queue
import threading
from tkinter import messagebox
from typing import TYPE_CHECKING, Optional

from customtkinter import filedialog
from pydantic import BaseModel

from app.adapters.export import get_exporter
from app.core.models import ModelSize, OutputFormat, TranscriptionTask
from app.services.realtime_transcription import RealtimeTranscriptionService

if TYPE_CHECKING:
    from app.gui_main import App


class QueueMessage(BaseModel):
    """Модель сообщения для обмена между потоками."""

    status: Optional[str] = None
    progress: Optional[float] = None
    result_text: Optional[str] = None
    partial_result: Optional[str] = None  # Для real-time результатов
    is_done: bool = False


class TranscriptionController:
    """
    Класс-оркестратор, который связывает View (GUI) и Model (сервисы).
    """

    def __init__(self, view: "App"):
        self.view = view
        self.task_queue = queue.Queue()
        self.is_running = False
        self.is_recording = False
        self.last_transcription_result: Optional[dict] = None
        self.last_timestamps_enabled: bool = False
        self.cancel_event: Optional[threading.Event] = None
        self.realtime_service: Optional[RealtimeTranscriptionService] = None
        self.realtime_full_text: str = ""

    def _log_to_queue(self, message: str):
        """Отправляет статусное сообщение в очередь GUI."""
        self.task_queue.put(QueueMessage(status=message))

    def select_file(self):
        if self.is_running:
            return
        file_path = filedialog.askopenfilename(
            title="Выберите медиафайл",
            filetypes=(
                ("Медиафайлы", "*.mp3 *.wav *.m4a *.mp4 *.mov"),
                ("Все файлы", "*.*"),
            ),
        )
        self.handle_source_path(file_path)

    def handle_source_path(self, file_path: str):
        if not file_path or self.is_running:
            return
        self.view.file_path_entry.configure(state="normal")
        self.view.file_path_entry.delete(0, "end")
        self.view.file_path_entry.insert(0, file_path)
        self.view.file_path_entry.configure(state="disabled")
        self.view.youtube_entry.delete(0, "end")

    def on_youtube_entry_change(self, _, __, ___):
        if self.is_running:
            return
        if self.view.youtube_entry.get():
            self.view.file_path_entry.configure(state="normal")
            self.view.file_path_entry.delete(0, "end")
            self.view.file_path_entry.configure(state="disabled")

    def start_transcription(self):
        if self.is_running:
            return

        source_file = self.view.file_path_entry.get()
        source_url = self.view.youtube_entry.get()

        if not source_file and not source_url:
            self._log_to_queue("Ошибка: Укажите источник (файл или URL)")
            self.task_queue.put(QueueMessage(is_done=True))
            return

        self.is_running = True
        self.last_transcription_result = None
        self.cancel_event = threading.Event()
        self.view.update_ui_for_task_start()

        self.last_timestamps_enabled = self.view.timestamps_checkbox.get()
        selected_task_str = self.view.task_segmented_button.get()
        task = (
            TranscriptionTask.TRANSLATE
            if selected_task_str == "Перевод"
            else TranscriptionTask.TRANSCRIBE
        )

        params = {
            "source": source_file or source_url,
            "is_youtube": bool(source_url),
            "model_size": ModelSize(self.view.model_menu.get()),
            "task": task,
            "cancel_event": self.cancel_event,
        }

        thread = threading.Thread(target=self._transcription_worker, args=(params,))
        thread.daemon = True
        thread.start()

    def cancel_transcription(self):
        if self.cancel_event:
            self._log_to_queue("Отмена операции...")
            self.cancel_event.set()

    def save_result(self):
        if not self.last_transcription_result or not self.last_transcription_result.get(
            "text"
        ):
            self._log_to_queue("Нечего сохранять.")
            return

        output_format = OutputFormat(self.view.format_menu.get())

        if output_format == OutputFormat.SRT and not self.last_timestamps_enabled:
            messagebox.showerror(
                "Ошибка сохранения",
                "Для сохранения в формате .srt необходимо выполнить транскрибацию "
                "с включенной опцией 'Включить таймстемпы'.",
            )
            return

        file_extension = f".{output_format.value}"
        file_types = [
            ("Текстовые файлы", "*.txt"),
            ("Markdown файлы", "*.md"),
            ("SRT субтитры", "*.srt"),
            ("Все файлы", "*.*"),
        ]

        file_path = filedialog.asksaveasfilename(
            title="Сохранить результат",
            defaultextension=file_extension,
            filetypes=file_types,
        )

        if not file_path:
            return

        try:
            exporter = get_exporter(output_format)
            exporter.export(
                result_data=self.last_transcription_result,
                destination_path=pathlib.Path(file_path),
            )
            self._log_to_queue(f"Файл успешно сохранен: {file_path}")
        except Exception as e:
            self._log_to_queue(f"Ошибка при сохранении файла: {e}")

    def _log_to_status_bar(self, message: str):
        """Отправляет только статусное сообщение в очередь GUI."""
        self.task_queue.put(QueueMessage(status=message))

    def _on_realtime_result(self, partial_text: str):
        """Callback для получения частичного результата от Realtime сервиса."""
        self.realtime_full_text += partial_text + " "
        self.task_queue.put(QueueMessage(partial_result=partial_text + " "))

    def toggle_realtime_transcription(self):
        """Переключает состояние записи с микрофона."""
        if self.is_recording:
            if self.realtime_service:
                self.realtime_service.stop()
                self.realtime_service = None
            self.is_recording = False
            self.view.update_ui_for_recording_end()
        else:
            self.is_recording = True
            self.view.update_ui_for_recording_start()
            self.realtime_full_text = ""  # Сбрасываем текст перед началом

            selected_task_str = self.view.task_segmented_button.get()
            task = (
                TranscriptionTask.TRANSLATE
                if selected_task_str == "Перевод"
                else TranscriptionTask.TRANSCRIBE
            )
            mic_id_str = self.view.mic_menu.get()
            try:
                mic_id = int(mic_id_str.split("ID: ")[1].strip(")"))
            except (IndexError, ValueError):
                self._log_to_status_bar("Ошибка: Не удалось определить ID микрофона.")
                self.is_recording = False
                self.view.update_ui_for_recording_end()
                return

            params = {
                "model_size": ModelSize(self.view.model_menu.get()),
                "task": task,
                "mic_id": mic_id,
            }
            thread = threading.Thread(
                target=self._realtime_worker_start, args=(params,)
            )
            thread.daemon = True
            thread.start()

    def _realtime_worker_start(self, params: dict):
        """Загружает модель и запускает сервис записи в фоновом потоке."""
        import whisper

        from app.services.model_manager import ModelManager

        try:
            manager = ModelManager(params["model_size"])
            model_path = manager.ensure_model_is_available(
                log_callback=self._log_to_status_bar
            )
            self._log_to_status_bar(
                f"Загрузка модели '{params['model_size'].value}' в память..."
            )
            model = whisper.load_model(model_path)

            self.realtime_service = RealtimeTranscriptionService(
                model=model,
                device_id=params["mic_id"],
                task=params["task"].value,
                result_callback=self._on_realtime_result,
                status_callback=self._log_to_status_bar,
            )
            self.realtime_service.start()

        except Exception as e:
            self._log_to_status_bar(f"Критическая ошибка при запуске записи: {e}")
            self.is_recording = False
            # Отправляем сообщение в основной поток для обновления GUI
            self.task_queue.put(QueueMessage(is_done=True))

    def _transcription_worker(self, params: dict):
        from app.adapters.youtube import FFmpegNotFoundError

        adapters = {"youtube": None, "local": None}
        try:
            processed_path = self._process_source(params, adapters)
            if not processed_path:
                raise IOError("Не удалось обработать исходный файл или URL.")

            if params["cancel_event"].is_set():
                return

            result_data = self._execute_transcription(processed_path, params)
            self.last_transcription_result = result_data

            if params["cancel_event"].is_set():
                result_text = "Операция была отменена пользователем."
            else:
                result_text = self._format_result_for_gui(result_data)

            self.task_queue.put(
                QueueMessage(status="Готово!", progress=1.0, result_text=result_text)
            )

        except (FFmpegNotFoundError, IOError) as e:
            self._log_to_queue(f"Ошибка: {e}")
        except Exception as e:
            self._log_to_queue(f"Критическая ошибка: {e}")
        finally:
            self._cleanup_resources(adapters)
            self.task_queue.put(QueueMessage(is_done=True))
            self.is_running = False
            self.cancel_event = None

    def _format_result_for_gui(self, result_data: dict) -> str:
        if not self.last_timestamps_enabled:
            return result_data.get("text", "")

        text_parts = []
        for segment in result_data.get("segments", []):
            start = int(segment["start"])
            end = int(segment["end"])
            start_time = (
                f"{start // 3600:02d}:{(start % 3600) // 60:02d}:{start % 60:02d}"
            )
            end_time = f"{end // 3600:02d}:{(end % 3600) // 60:02d}:{end % 60:02d}"
            text = segment["text"].strip()
            text_parts.append(f"[{start_time} -> {end_time}] {text}")

        return "\n".join(text_parts)

    def _process_source(self, params: dict, adapters: dict) -> str:
        """Обрабатывает источник (файл или URL) и возвращает путь к WAV файлу."""
        from app.adapters.local_file import LocalFileAdapter
        from app.adapters.youtube import YoutubeAdapter

        audio_path = params["source"]

        if params["is_youtube"]:
            self._log_to_queue("Загрузка с YouTube...")
            adapter = YoutubeAdapter()
            adapters["youtube"] = adapter
            return adapter.download_audio(
                url=audio_path, log_callback=self._log_to_queue
            )
        else:
            self._log_to_queue("Обработка локального файла...")
            adapter = LocalFileAdapter()
            adapters["local"] = adapter
            return adapter.process_file(
                source_path=audio_path, log_callback=self._log_to_queue
            )

    def _execute_transcription(self, audio_path: str, params: dict) -> dict:
        import whisper

        from app.services.model_manager import ModelManager
        from app.services.transcription import TranscriptionService

        self.task_queue.put(QueueMessage(progress=0.2))

        def model_progress_callback(downloaded_bytes, total_bytes):
            if total_bytes > 0:
                progress = 0.2 + (downloaded_bytes / total_bytes) * 0.1
                self.task_queue.put(QueueMessage(progress=progress))

        manager = ModelManager(params["model_size"])
        model_path = manager.ensure_model_is_available(
            progress_callback=model_progress_callback, log_callback=self._log_to_queue
        )

        if params["cancel_event"].is_set():
            return {"text": "", "segments": []}

        self._log_to_queue(
            f"Загрузка модели '{params['model_size'].value}' в память..."
        )
        self.task_queue.put(QueueMessage(progress=0.3))
        model = whisper.load_model(model_path)

        self._log_to_queue("Подготовка к транскрибации...")
        self.task_queue.put(QueueMessage(progress=0.35))

        def transcription_progress_callback(processed_chunks, total_chunks):
            if total_chunks > 0:
                progress = 0.35 + (processed_chunks / total_chunks) * 0.65
                self.task_queue.put(QueueMessage(progress=progress))
                if processed_chunks % 5 == 0 or processed_chunks == total_chunks:
                    self._log_to_queue(
                        f"Транскрибация... ({processed_chunks}/{total_chunks})"
                    )

        service = TranscriptionService(model=model)
        return service.transcribe(
            source_path=audio_path,
            language=None,
            task=params["task"],
            cancel_event=params["cancel_event"],
            progress_callback=transcription_progress_callback,
        )

    def _cleanup_resources(self, adapters: dict):
        for adapter_name, adapter_instance in adapters.items():
            if adapter_instance:
                try:
                    adapter_instance.cleanup(log_callback=self._log_to_queue)
                except Exception as e:
                    msg = f"Не удалось очистить временные файлы {adapter_name}: {e}"
                    self._log_to_queue(msg)
