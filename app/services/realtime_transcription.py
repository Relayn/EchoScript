"""
Сервис для транскрибации аудиопотока с микрофона в реальном времени.
"""

import queue
import threading
from typing import Any, Callable

import numpy as np
import sounddevice as sd
import whisper

# --- Константы для аудиопотока ---
SAMPLE_RATE = 16000  # Частота дискретизации, стандарт для Whisper
CHANNELS = 1  # Моно-аудио
DTYPE = "float32"  # Тип данных для аудио
BLOCK_DURATION_MS = 1000  # Длительность блока аудио, который мы получаем от микрофона
BLOCKSIZE = int(SAMPLE_RATE * BLOCK_DURATION_MS / 1000)  # Размер блока в сэмплах

# --- Константы для обработки ---
# Мы будем накапливать аудио в течение нескольких секунд перед отправкой в Whisper.
# Это компромисс между задержкой и качеством транскрипции.
PROCESSING_INTERVAL_SECONDS = 5
PROCESSING_QUEUE_SIZE = int(SAMPLE_RATE * PROCESSING_INTERVAL_SECONDS)


class RealtimeTranscriptionService:
    """
    Управляет захватом аудио с микрофона, обработкой и транскрибацией.
    """

    def __init__(
        self,
        model: whisper.Whisper,
        device_id: int,
        task: str,
        result_callback: Callable[[str], None],
        status_callback: Callable[[str], None],
    ):
        self.model = model
        self.device_id = device_id
        self.task = task
        self.result_callback = result_callback
        self.status_callback = status_callback

        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._processing_thread: threading.Thread | None = None
        self._stream: sd.InputStream | None = None
        self._stop_event = threading.Event()

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time: Any, status: Any
    ) -> None:
        """Этот callback вызывается из потока sounddevice для каждого блока аудио."""
        if status:
            self.status_callback(f"Ошибка аудиопотока: {status}")
        self._audio_queue.put(indata.copy())

    def _processing_worker(self) -> None:
        """
        Рабочий поток, который извлекает аудио из очереди, накапливает его
        и отправляет в Whisper для транскрипции.
        """
        processing_buffer = np.array([], dtype=DTYPE)

        while not self._stop_event.is_set():
            try:
                # Ждем данные не более секунды, чтобы регулярно проверять stop_event
                audio_chunk = self._audio_queue.get(timeout=1)
                processing_buffer = np.concatenate(
                    (processing_buffer, audio_chunk.flatten())
                )

                # Если накопили достаточно данных, отправляем на обработку
                if len(processing_buffer) >= PROCESSING_QUEUE_SIZE:
                    self.status_callback("Обработка фрагмента...")

                    options: dict[str, Any] = {
                        "language": None,
                        "verbose": False,
                        "task": self.task,
                    }
                    result = self.model.transcribe(audio=processing_buffer, **options)

                    transcribed_text = result.get("text", "").strip()
                    if transcribed_text:
                        self.result_callback(transcribed_text)

                    # Очищаем буфер после обработки
                    processing_buffer = np.array([], dtype=DTYPE)
                    self.status_callback("Ожидание аудио...")

            except queue.Empty:
                # Это нормально, просто продолжаем цикл
                continue
            except Exception as e:
                self.status_callback(f"Ошибка в потоке обработки: {e}")
                break

    def start(self) -> None:
        """Запускает аудиопоток и рабочий поток обработки."""
        self.status_callback("Запуск записи...")
        self._stop_event.clear()

        self._processing_thread = threading.Thread(target=self._processing_worker)
        self._processing_thread.daemon = True
        self._processing_thread.start()

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCKSIZE,
            device=self.device_id,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._audio_callback,
        )
        self._stream.start()
        self.status_callback("Ожидание аудио...")

    def stop(self) -> None:
        """Останавливает аудиопоток и рабочий поток."""
        if not self._stop_event.is_set():
            self.status_callback("Остановка записи...")
            self._stop_event.set()

            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            if self._processing_thread:
                self._processing_thread.join(timeout=2)
                self._processing_thread = None

            # Очищаем очередь от оставшихся данных
            with self._audio_queue.mutex:
                self._audio_queue.queue.clear()

            self.status_callback("Запись остановлена.")
