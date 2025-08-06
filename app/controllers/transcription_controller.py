"""
Контроллер, управляющий логикой транскрипции и состоянием GUI.
Этот класс является ViewModel в архитектуре MVVM.
"""
import pathlib
import queue
import threading
from typing import TYPE_CHECKING, Optional

from customtkinter import filedialog
from pydantic import BaseModel

from app.adapters.export import get_exporter
from app.core.models import ModelSize, OutputFormat

if TYPE_CHECKING:
    from app.gui_main import App


class QueueMessage(BaseModel):
    """Модель сообщения для обмена между потоками."""
    status: Optional[str] = None
    progress: Optional[float] = None
    result_text: Optional[str] = None
    is_done: bool = False


class TranscriptionController:
    """
    Класс-оркестратор, который связывает View (GUI) и Model (сервисы).
    """

    def __init__(self, view: 'App'):
        """
        Инициализирует контроллер.

        Args:
            view: Экземпляр главного окна приложения (App).
        """
        self.view = view
        self.task_queue = queue.Queue()
        self.is_running = False

    def select_file(self):
        """Открывает диалоговое окно для выбора файла и обновляет поле ввода в GUI."""
        if self.is_running:
            return
        file_path = filedialog.askopenfilename(
            title="Выберите медиафайл",
            filetypes=(("Медиафайлы", "*.mp3 *.wav *.m4a *.mp4 *.mov"), ("Все файлы", "*.*")),
        )
        if not file_path:
            return
        self.view.file_path_entry.configure(state="normal")
        self.view.file_path_entry.delete(0, "end")
        self.view.file_path_entry.insert(0, file_path)
        self.view.file_path_entry.configure(state="disabled")
        self.view.youtube_entry.delete(0, "end")

    def on_youtube_entry_change(self, _, __, ___):
        """Очищает поле выбора файла, если пользователь начинает вводить URL."""
        if self.is_running:
            return
        if self.view.youtube_entry.get():
            self.view.file_path_entry.configure(state="normal")
            self.view.file_path_entry.delete(0, "end")
            self.view.file_path_entry.configure(state="disabled")

    def start_transcription(self):
        """Запускает процесс транскрипции в отдельном потоке."""
        if self.is_running:
            return

        source_file = self.view.file_path_entry.get()
        source_url = self.view.youtube_entry.get()

        if not source_file and not source_url:
            self.task_queue.put(QueueMessage(status="Ошибка: Укажите источник (файл или URL)"))
            self.task_queue.put(QueueMessage(is_done=True))
            return

        self.is_running = True
        self.view.update_ui_for_task_start()

        params = {
            "source": source_file or source_url,
            "is_youtube": bool(source_url),
            "model_size": ModelSize(self.view.model_menu.get()),
            "timestamps": self.view.timestamps_checkbox.get(),
        }

        thread = threading.Thread(target=self._transcription_worker, args=(params,))
        thread.daemon = True
        thread.start()

    def save_result(self):
        """Сохраняет транскрибированный текст в файл."""
        text_to_save = self.view.result_textbox.get("1.0", "end-1c")
        if not text_to_save:
            self.task_queue.put(QueueMessage(status="Нечего сохранять."))
            return

        output_format = OutputFormat(self.view.format_menu.get())
        file_extension = f".{output_format.value}"

        file_path = filedialog.asksaveasfilename(
            title="Сохранить результат",
            defaultextension=file_extension,
            filetypes=[
                ("Текстовые файлы", "*.txt"),
                ("Markdown файлы", "*.md"),
                ("Все файлы", "*.*"),
            ],
        )

        if not file_path:
            return

        try:
            exporter = get_exporter(output_format)
            # В GUI-версии мы не выводим сообщение в консоль, поэтому передаем
            # экземпляр адаптера без вызова его метода export из CLI
            exporter.export(text=text_to_save, destination_path=pathlib.Path(file_path))
            self.task_queue.put(QueueMessage(status=f"Файл успешно сохранен: {file_path}"))
        except Exception as e:
            self.task_queue.put(QueueMessage(status=f"Ошибка при сохранении файла: {e}"))

    def _transcription_worker(self, params: dict):
        """
        Этот метод выполняется в фоновом потоке и выполняет всю тяжелую работу.
        Он выступает в роли дирижера, вызывая другие методы для каждого этапа.
        """
        # --- ОТЛОЖЕННАЯ ЗАГРУЗКА ---
        # Импортируем тяжелые библиотеки здесь, а не на старте приложения.
        from app.adapters.youtube import FFmpegNotFoundError

        # -----------------------------
        adapters = {"youtube": None, "local": None}
        try:
            processed_path = self._process_source(params, adapters)
            if not processed_path:
                raise IOError("Не удалось обработать исходный файл или URL.")

            result_text = self._execute_transcription(processed_path, params)

            self.task_queue.put(QueueMessage(status="Готово!", progress=1.0, result_text=result_text))

        except (FFmpegNotFoundError, IOError) as e:
            self.task_queue.put(QueueMessage(status=f"Ошибка: {e}"))
        except Exception as e:
            self.task_queue.put(QueueMessage(status=f"Критическая ошибка: {e}"))
        finally:
            self._cleanup_resources(adapters)
            self.task_queue.put(QueueMessage(is_done=True))
            self.is_running = False

    def _process_source(self, params: dict, adapters: dict) -> str:
        """Обрабатывает источник (файл или URL) и возвращает путь к готовому WAV файлу."""
        from app.adapters.local_file import LocalFileAdapter
        from app.adapters.youtube import YoutubeAdapter

        log_callback = lambda message: self.task_queue.put(QueueMessage(status=message))
        audio_path = params["source"]

        if params["is_youtube"]:
            log_callback("Загрузка с YouTube...")
            adapter = YoutubeAdapter()
            adapters["youtube"] = adapter
            return adapter.download_audio(url=audio_path, log_callback=log_callback)
        else:
            log_callback("Обработка локального файла...")
            adapter = LocalFileAdapter()
            adapters["local"] = adapter
            return adapter.process_file(source_path=audio_path, log_callback=log_callback)

    def _execute_transcription(self, audio_path: str, params: dict) -> str:
        """Загружает модель и выполняет транскрибацию."""
        import whisper
        from app.services.model_manager import ModelManager
        from app.services.transcription import TranscriptionService

        log_callback = lambda message: self.task_queue.put(QueueMessage(status=message))
        self.task_queue.put(QueueMessage(progress=0.2))

        # Этап 2.1: Скачивание файла модели
        def model_progress_callback(downloaded_bytes, total_bytes):
            if total_bytes > 0:
                progress = 0.2 + (downloaded_bytes / total_bytes) * 0.1
                self.task_queue.put(QueueMessage(progress=progress))

        manager = ModelManager(params["model_size"])
        model_path = manager.ensure_model_is_available(
            progress_callback=model_progress_callback, log_callback=log_callback
        )

        # Этап 2.2: Загрузка модели в память
        log_callback(f"Загрузка модели '{params['model_size'].value}' в память... (может занять время)")
        self.task_queue.put(QueueMessage(progress=0.3))
        model = whisper.load_model(model_path)

        # Этап 3: Транскрибация
        log_callback("Подготовка к транскрибации...")
        self.task_queue.put(QueueMessage(progress=0.35))

        def transcription_progress_callback(processed_chunks, total_chunks):
            if total_chunks > 0:
                progress = 0.35 + (processed_chunks / total_chunks) * 0.65
                self.task_queue.put(QueueMessage(progress=progress))
                if processed_chunks % 5 == 0 or processed_chunks == total_chunks:
                    log_callback(f"Транскрибация... ({processed_chunks}/{total_chunks})")

        service = TranscriptionService(model=model)
        return service.transcribe(
            source_path=audio_path,
            language=None,
            timestamps=params["timestamps"],
            progress_callback=transcription_progress_callback,
        )

    def _cleanup_resources(self, adapters: dict):
        """Очищает временные файлы, созданные адаптерами."""
        log_callback = lambda message: self.task_queue.put(QueueMessage(status=message))
        if adapters["youtube"]:
            adapters["youtube"].cleanup(log_callback=log_callback)
        if adapters["local"]:
            adapters["local"].cleanup(log_callback=log_callback)
