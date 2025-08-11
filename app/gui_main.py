"""
Основной модуль для запуска графического интерфейса (GUI) приложения EchoScript.

Этот файл инициализирует главное окно приложения с использованием CustomTkinter
и запускает основной цикл обработки событий.
"""

import queue
from tkinter import TclError, messagebox
from typing import Any

import customtkinter as ctk
import sounddevice as sd
from tkinterdnd2 import DND_FILES, TkinterDnD

from app.controllers.transcription_controller import (
    QueueMessage,
    TranscriptionController,
)
from app.core.config import save_language
from app.core.localization import _
from app.core.models import ModelSize, OutputFormat


class App(ctk.CTk, TkinterDnD.DnDWrapper):  # type: ignore[misc]
    """
    Главный класс приложения, который инкапсулирует окно и его компоненты.
    Наследуется от CTk и DnDWrapper для поддержки Drag-n-Drop.
    """

    TAB_FILE = _("Из файла")
    TAB_REALTIME = _("С микрофона")

    # Карта для отображения языков пользователю и их сохранения
    LANG_MAP = {"English": "en_US", "Русский": "ru_RU"}

    def __init__(self, **kwargs: Any) -> None:
        """
        Инициализирует главное окно приложения и его базовую структуру.
        """
        super().__init__(**kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

        # --- Базовая настройка окна ---
        self.title(_("EchoScript - AI-Транскрибатор"))
        self.geometry("850x600")
        self.resizable(True, True)

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

    def _on_drop(self, event: Any) -> None:
        """Обработчик события перетаскивания файла в окно."""
        if event.data:
            first_path = event.data.split("}")[0].lstrip("{")
            self.controller.handle_source_path(first_path)

    def _create_widgets(self) -> None:
        """Создает и размещает все виджеты в окне."""
        self._create_tab_view()
        self._create_main_frame()
        self._create_status_frame()

    def _create_tab_view(self) -> None:
        """Создает и управляет вкладочным интерфейсом."""
        self.tab_view = ctk.CTkTabview(self, anchor="w", height=70)
        self.tab_view.grid(row=0, column=0, padx=10, pady=(0, 5), sticky="new")
        self.tab_view.add(self.TAB_FILE)
        self.tab_view.add(self.TAB_REALTIME)
        self._create_source_frame(self.tab_view.tab(self.TAB_FILE))
        self._create_realtime_frame(self.tab_view.tab(self.TAB_REALTIME))

    def _create_source_frame(self, parent_tab: ctk.CTkFrame) -> None:
        """Создает фрейм для выбора источника (файл или URL)."""
        parent_tab.grid_columnconfigure(1, weight=1)
        parent_tab.grid_columnconfigure(3, weight=1)
        self.file_button = ctk.CTkButton(
            parent_tab, text=_("Выбрать файл"), command=self.controller.select_file
        )
        self.file_button.grid(row=0, column=0, padx=(0, 5), pady=10)
        self.file_path_entry = ctk.CTkEntry(
            parent_tab,
            placeholder_text=_("Путь к файлу (или перетащите сюда)"),
            state="disabled",
        )
        self.file_path_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        ctk.CTkLabel(parent_tab, text=_("или")).grid(row=0, column=2, padx=10, pady=10)
        self.youtube_var = ctk.StringVar()
        self.youtube_var.trace_add("write", self.controller.on_youtube_entry_change)
        self.youtube_entry = ctk.CTkEntry(
            parent_tab,
            placeholder_text=_("URL видео с YouTube"),
            textvariable=self.youtube_var,
        )
        self.youtube_entry.grid(row=0, column=3, padx=(5, 0), pady=10, sticky="ew")

    def _create_realtime_frame(self, parent_tab: ctk.CTkFrame) -> None:
        """Создает фрейм для транскрибации в реальном времени."""
        parent_tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(parent_tab, text=_("Микрофон:")).grid(
            row=0, column=0, padx=(0, 5), pady=10
        )
        mic_list = self._get_input_devices()
        self.mic_menu = ctk.CTkOptionMenu(parent_tab, values=mic_list)
        if not mic_list:
            self.mic_menu.set(_("Микрофоны не найдены"))
            self.mic_menu.configure(state="disabled")
        self.mic_menu.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.record_button = ctk.CTkButton(
            parent_tab,
            text=_("Начать запись"),
            command=self.controller.toggle_realtime_transcription,
        )
        if not mic_list:
            self.record_button.configure(state="disabled")
        self.record_button.grid(row=0, column=2, padx=(10, 0), pady=10)

    def _get_input_devices(self) -> list[str]:
        """Возвращает список доступных устройств ввода (микрофонов)."""
        try:
            devices = sd.query_devices()
            return [
                _("{} (ID: {})").format(device["name"], i)
                for i, device in enumerate(devices)
                if device["max_input_channels"] > 0
            ]
        except (TclError, sd.PortAudioError) as e:
            self.status_label.configure(text=_("Ошибка аудио: {}").format(e))
            return []

    def _create_main_frame(self) -> None:
        """Создает главный фрейм с настройками и полем для результата."""
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=0)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        settings_frame = ctk.CTkScrollableFrame(main_frame, width=220)
        settings_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ns")
        ctk.CTkLabel(
            settings_frame, text=_("Настройки"), font=ctk.CTkFont(weight="bold")
        ).pack(pady=10, padx=10)
        ctk.CTkLabel(settings_frame, text=_("Задача:")).pack(
            padx=10, pady=(10, 0), anchor="w"
        )
        self.task_segmented_button = ctk.CTkSegmentedButton(
            settings_frame,
            values=[_("Транскрибация"), _("Перевод")],
            command=self._on_task_select,
        )
        self.task_segmented_button.set(_("Транскрибация"))
        self.task_segmented_button.pack(padx=10, pady=5, fill="x")
        ctk.CTkLabel(settings_frame, text=_("Модель Whisper:")).pack(
            padx=10, pady=(10, 0), anchor="w"
        )
        model_names = [size.value for size in ModelSize]
        self.model_menu = ctk.CTkOptionMenu(
            settings_frame, values=model_names, command=self._on_model_select
        )
        self.model_menu.set(ModelSize.BASE.value)
        self.model_menu.pack(padx=10, pady=5, fill="x")
        ctk.CTkLabel(settings_frame, text=_("Формат вывода:")).pack(
            padx=10, pady=(10, 0), anchor="w"
        )
        format_names = [f.value for f in OutputFormat]
        self.format_menu = ctk.CTkOptionMenu(settings_frame, values=format_names)
        self.format_menu.set(OutputFormat.TXT.value)
        self.format_menu.pack(padx=10, pady=5, fill="x")
        self.timestamps_checkbox = ctk.CTkCheckBox(
            settings_frame, text=_("Включить таймстемпы")
        )
        self.timestamps_checkbox.pack(padx=10, pady=10, anchor="w")

        # --- Виджет выбора языка ---
        ctk.CTkLabel(settings_frame, text=_("Язык интерфейса:")).pack(
            padx=10, pady=(10, 0), anchor="w"
        )
        self.lang_menu = ctk.CTkOptionMenu(
            settings_frame,
            values=list(self.LANG_MAP.keys()),
            command=self._on_language_select,
        )
        self.lang_menu.pack(padx=10, pady=5, fill="x")

        self.start_button = ctk.CTkButton(
            settings_frame, text=_("Старт"), command=self.controller.start_transcription
        )
        self.start_button.pack(padx=10, pady=10, side="bottom", fill="x")
        self.save_button = ctk.CTkButton(
            settings_frame,
            text=_("Сохранить результат"),
            state="disabled",
            command=self.controller.save_result,
        )
        self.save_button.pack(padx=10, pady=5, side="bottom", fill="x")
        self.result_textbox = ctk.CTkTextbox(main_frame, wrap="word")
        self.result_textbox.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

    def _create_status_frame(self) -> None:
        """Создает нижний фрейм для статус-бара и прогресс-бара."""
        status_frame = ctk.CTkFrame(self)
        status_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="sew")
        status_frame.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(
            status_frame, text=_("Готов к работе..."), anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.progress_bar = ctk.CTkProgressBar(status_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=1, padx=10, pady=5, sticky="e")

    def _on_language_select(self, lang_name: str) -> None:
        """Сохраняет выбор языка и просит перезапустить приложение."""
        lang_code = self.LANG_MAP.get(lang_name)
        if lang_code:
            save_language(lang_code)
            messagebox.showinfo(
                _("Смена языка"),
                _("Язык интерфейса будет изменен после перезапуска приложения."),
            )

    def _on_model_select(self, model_name: str) -> None:
        """Показывает предупреждение при выборе ресурсоемких моделей."""
        if model_name in [ModelSize.MEDIUM.value, ModelSize.LARGE.value]:
            messagebox.showinfo(
                _("Требования к ресурсам"),
                _(
                    "Вы выбрали модель '{}'.\n\n"
                    "Эта модель требует значительного объема видеопамяти (VRAM) "
                    "для оптимальной работы (5-10 ГБ).\n\n"
                    "Если у вас нет мощной видеокарты, обработка может быть очень "
                    "медленной или привести к ошибкам нехватки памяти."
                ).format(model_name),
            )

    def _on_task_select(self, selected_task: str) -> None:
        """Обрабатывает выбор задачи, отключая таймстемпы для перевода."""
        if selected_task == _("Перевод"):
            self.timestamps_checkbox.deselect()
            self.timestamps_checkbox.configure(state="disabled")
            self.format_menu.set(OutputFormat.TXT.value)
            self.format_menu.configure(state="disabled")
        else:
            self.timestamps_checkbox.configure(state="normal")
            self.format_menu.configure(state="normal")

    def _process_queue(self) -> None:
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
            if message.partial_result is not None:
                self.result_textbox.insert("end", message.partial_result)
                self.result_textbox.see("end")
            if message.is_done:
                self.update_ui_for_task_end()
        except queue.Empty:
            pass
        finally:
            self.after(100, self._process_queue)

    def update_ui_for_task_start(self) -> None:
        """Блокирует элементы управления на время выполнения задачи."""
        self.start_button.configure(
            state="normal",
            text=_("Отмена"),
            command=self.controller.cancel_transcription,
        )
        for widget in [
            self.save_button,
            self.file_button,
            self.youtube_entry,
            self.model_menu,
            self.format_menu,
            self.timestamps_checkbox,
            self.task_segmented_button,
            self.mic_menu,
            self.record_button,
            self.lang_menu,
        ]:
            widget.configure(state="disabled")
        self.result_textbox.delete("1.0", "end")
        self.tab_view.configure(state="disabled")

    def update_ui_for_task_end(self) -> None:
        """Разблокирует элементы управления после завершения задачи."""
        self.start_button.configure(
            state="normal", text=_("Старт"), command=self.controller.start_transcription
        )
        for widget in [
            self.save_button,
            self.file_button,
            self.youtube_entry,
            self.model_menu,
            self.format_menu,
            self.timestamps_checkbox,
            self.task_segmented_button,
            self.lang_menu,
        ]:
            widget.configure(state="normal")
        if self.mic_menu.cget("values"):
            self.mic_menu.configure(state="normal")
            self.record_button.configure(state="normal")
        self.tab_view.configure(state="normal")
        self._on_task_select(self.task_segmented_button.get())

    def update_ui_for_recording_start(self) -> None:
        """Обновляет UI при начале записи с микрофона."""
        self.record_button.configure(text=_("Остановить запись"))
        for widget in [
            self.save_button,
            self.model_menu,
            self.task_segmented_button,
            self.lang_menu,
        ]:
            widget.configure(state="disabled")
        self.result_textbox.delete("1.0", "end")
        self.tab_view.configure(state="disabled")
        self.tab_view.set(self.TAB_REALTIME)

    def update_ui_for_recording_end(self) -> None:
        """Восстанавливает UI после окончания записи."""
        self.record_button.configure(text=_("Начать запись"))
        for widget in [
            self.save_button,
            self.model_menu,
            self.task_segmented_button,
            self.lang_menu,
        ]:
            widget.configure(state="normal")
        self.tab_view.configure(state="normal")


if __name__ == "__main__":
    app = App()
    app.mainloop()
