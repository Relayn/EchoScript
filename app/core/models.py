"""Ключевые модели данных и перечисления для приложения."""

import enum
from typing import Optional, Union

from pydantic import BaseModel, FilePath, HttpUrl


class ModelSize(str, enum.Enum):
    """Перечисление доступных размеров моделей Whisper."""

    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class OutputFormat(str, enum.Enum):
    """Перечисление поддерживаемых форматов итоговых файлов."""

    TXT = "txt"
    MD = "md"
    SRT = "srt"
    DOCX = "docx"


# Типовая подсказка, представляющая валидный источник:
# локальный путь к файлу или URL YouTube
Source = Union[FilePath, HttpUrl]


class SourceType(str, enum.Enum):
    """Перечисление для типов источников данных."""

    FILE = "file"
    YOUTUBE = "youtube"


class JobStatus(str, enum.Enum):
    """Перечисление для статусов задачи транскрибации."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionJob(BaseModel):
    """Модель данных, представляющая одну задачу на транскрибацию."""

    source: str
    source_type: SourceType
    status: JobStatus = JobStatus.PENDING
    result_text: Optional[str] = None
    error_message: Optional[str] = None


class TranscriptionTask(str, enum.Enum):
    """Перечисление для задач, выполняемых моделью."""

    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"
