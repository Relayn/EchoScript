"""
Основной модуль для запуска графического интерфейса (GUI) приложения EchoScript.

Этот файл инициализирует главное окно приложения с использованием CustomTkinter
и запускает основной цикл обработки событий.
"""

import queue
from tkinter import messagebox

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from app.controllers.transcription_controller import (
    QueueMessage,
    TranscriptionController,
)
from app.core.models import ModelSize, OutputFormat


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    """
    Главный класс приложения, который инкапсулирует окно и его компоненты.
    Наследуется от CTk и DnDWrapper для поддержки Drag-n-Drop.
    """

    def __init__(self, **kwargs):
        """
        Инициализирует главное окно приложения и его базовую структуру.
        """
        super().__init__(**kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

        # --- Базовая настройка окна ---
        self.title("EchoScript - AI-Транскрибатор")
        self.geometry("850x600")
        self.resizable(False, False)

        # --- Настройка темы ---
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # --- Инициализация контроллера ---
        self.controller = TranscriptionController(self)

        # --- Настройка сетки (grid) для масштабирования ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        # --- Создание и наполнение виджетов ---
        self._create_widgets()

        # --- Настройка Drag-and-Drop ---
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._on_drop)

        # --- Запуск обработчика очереди ---
        self.after(100, self._process_queue)

    def _on_drop(self, event):
        """Обработчик события перетаскивания файла в окно."""
        # event.data - это строка с путями к файлам, заключенная в фигурные скобки
        # и разделенная пробелами, если файлов несколько.
        # Пример: '{C:/Users/user/file1.mp4} {C:/Users/user/file2.mp3}'
        # Мы берем только первый файл.
        if event.data:
            # Убираем фигурные скобки и берем первый путь до закрывающей скобки
            first_path = event.data.split("}")[0].lstrip("{")
            self.controller.handle_source_path(first_path)

    def _create_widgets(self):
        """Создает и размещает все виджеты в окне."""
        self._create_source_frame()
        self._create_main_frame()
        self._create_status_frame()

    def _create_source_frame(self):
        """Создает фрейм для выбора источника (файл или URL)."""
        source_frame = ctk.CTkFrame(self)
        source_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="new")
        source_frame.grid_columnconfigure(1, weight=1)
        source_frame.grid_columnconfigure(3, weight=1)

        self.file_button = ctk.CTkButton(
            source_frame, text="Выбрать файл", command=self.controller.select_file
        )
        self.file_button.grid(row=0, column=0, padx=(10, 5), pady=10)

        self.file_path_entry = ctk.CTkEntry(
            source_frame,
            placeholder_text="Путь к файлу (или перетащите сюда)",
            state="disabled",
        )
        self.file_path_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        ctk.CTkLabel(source_frame, text="или").grid(row=0, column=2, padx=10, pady=10)

        self.youtube_var = ctk.StringVar()
        self.youtube_var.trace_add("write", self.controller.on_youtube_entry_change)
        self.youtube_entry = ctk.CTkEntry(
            source_frame,
            placeholder_text="URL видео с YouTube",
            textvariable=self.youtube_var,
        )
        self.youtube_entry.grid(row=0, column=3, padx=(5, 10), pady=10, sticky="ew")

    def _create_main_frame(self):
        """Создает главный фрейм с настройками и полем для результата."""
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=0)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        settings_frame = ctk.CTkFrame(main_frame, width=200)
        settings_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ns")

        ctk.CTkLabel(
            settings_frame, text="Настройки", font=ctk.CTkFont(weight="bold")
        ).pack(pady=10, padx=10)

        ctk.CTkLabel(settings_frame, text="Задача:").pack(
            padx=10, pady=(10, 0), anchor="w"
        )
        self.task_segmented_button = ctk.CTkSegmentedButton(
            settings_frame,
            values=["Транскрибация", "Перевод"],
            command=self._on_task_select,
        )
        self.task_segmented_button.set("Транскрибация")
        self.task_segmented_button.pack(padx=10, pady=5, fill="x")

        ctk.CTkLabel(settings_frame, text="Модель Whisper:").pack(
            padx=10, pady=(10, 0), anchor="w"
        )
        model_names = [size.value for size in ModelSize]
        self.model_menu = ctk.CTkOptionMenu(
            settings_frame, values=model_names, command=self._on_model_select
        )
        self.model_menu.set(ModelSize.BASE.value)
        self.model_menu.pack(padx=10, pady=5, fill="x")

        ctk.CTkLabel(settings_frame, text="Формат вывода:").pack(
            padx=10, pady=(10, 0), anchor="w"
        )
        format_names = [f.value for f in OutputFormat]
        self.format_menu = ctk.CTkOptionMenu(settings_frame, values=format_names)
        self.format_menu.set(OutputFormat.TXT.value)
        self.format_menu.pack(padx=10, pady=5, fill="x")

        self.timestamps_checkbox = ctk.CTkCheckBox(
            settings_frame, text="Включить таймстемпы"
        )
        self.timestamps_checkbox.pack(padx=10, pady=10, anchor="w")

        self.start_button = ctk.CTkButton(
            settings_frame, text="Старт", command=self.controller.start_transcription
        )
        self.start_button.pack(padx=10, pady=10, side="bottom", fill="x")

        self.save_button = ctk.CTkButton(
            settings_frame,
            text="Сохранить результат",
            state="disabled",
            command=self.controller.save_result,
        )
        self.save_button.pack(padx=10, pady=5, side="bottom", fill="x")

        self.result_textbox = ctk.CTkTextbox(main_frame, wrap="word")
        self.result_textbox.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

    def _create_status_frame(self):
        """Создает нижний фрейм для статус-бара и прогресс-бара."""
        status_frame = ctk.CTkFrame(self)
        status_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="sew")
        status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_frame, text="Готов к работе...", anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(status_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=1, padx=10, pady=5, sticky="e")

    def _on_model_select(self, model_name: str):
        """Показывает предупреждение при выборе ресурсоемких моделей."""
        if model_name in [ModelSize.MEDIUM.value, ModelSize.LARGE.value]:
            messagebox.showinfo(
                "Требования к ресурсам",
                f"Вы выбрали модель '{model_name}'.\n\n"
                "Эта модель требует значительного объема видеопамяти (VRAM) "
                "для оптимальной работы (5-10 ГБ).\n\n"
                "Если у вас нет мощной видеокарты, обработка может быть очень "
                "медленной или привести к ошибкам нехватки памяти.",
            )

    def _on_task_select(self, selected_task: str):
        """Обрабатывает выбор задачи, отключая таймстемпы для перевода."""
        if selected_task == "Перевод":
            self.timestamps_checkbox.deselect()
            self.timestamps_checkbox.configure(state="disabled")
            self.format_menu.set(OutputFormat.TXT.value)
            self.format_menu.configure(state="disabled")
        else:
            self.timestamps_checkbox.configure(state="normal")
            self.format_menu.configure(state="normal")

    def _process_queue(self):
        """Обрабатывает сообщения из очереди, приходящие из рабочего потока."""
        try:
            message: QueueMessage = self.controller.task_queue.get_nowait()

            if message.status:
                self.status_label.configure(text=message.status)
            if message.progress is not None:
                self.progress_bar.set(message.progress)
            if message.result_text is not None:
                self.result_textbox.delete("1.0", "end")
                self.result_textbox.insert("1.0", message.result_text)
            if message.is_done:
                self.update_ui_for_task_end()

        except queue.Empty:
            pass
        finally:
            self.after(100, self._process_queue)

    def update_ui_for_task_start(self):
        """Блокирует элементы управления на время выполнения задачи."""
        self.start_button.configure(
            state="normal", text="Отмена", command=self.controller.cancel_transcription
        )
        self.save_button.configure(state="disabled")
        self.file_button.configure(state="disabled")
        self.youtube_entry.configure(state="disabled")
        self.model_menu.configure(state="disabled")
        self.format_menu.configure(state="disabled")
        self.timestamps_checkbox.configure(state="disabled")
        self.task_segmented_button.configure(state="disabled")
        self.result_textbox.delete("1.0", "end")

    def update_ui_for_task_end(self):
        """Разблокирует элементы управления после завершения задачи."""
        self.start_button.configure(
            state="normal", text="Старт", command=self.controller.start_transcription
        )
        self.save_button.configure(state="normal")
        self.file_button.configure(state="normal")
        self.youtube_entry.configure(state="normal")
        self.model_menu.configure(state="normal")
        self.format_menu.configure(state="normal")
        self.timestamps_checkbox.configure(state="normal")
        self.task_segmented_button.configure(state="normal")
        # Восстанавливаем состояние виджетов в зависимости от выбранной задачи
        self._on_task_select(self.task_segmented_button.get())


if __name__ == "__main__":
    # Для TkinterDnD2 требуется, чтобы главный класс наследовался от их Tk-обертки
    app = App()
    app.mainloop()
