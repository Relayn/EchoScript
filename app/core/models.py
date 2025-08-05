"""Core data models and enumerations for the application."""

import enum
from typing import Optional, Union

from pydantic import BaseModel, FilePath, HttpUrl


class ModelSize(str, enum.Enum):
    """Enumeration for the available Whisper model sizes."""
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class OutputFormat(str, enum.Enum):
    """Enumeration for the supported output file formats."""
    TXT = "txt"
    MD = "md"


# A type hint representing a valid source: either a local file path or a YouTube URL
Source = Union[FilePath, HttpUrl]

class SourceType(str, enum.Enum):
    """Enumeration for the source type."""
    FILE = "file"
    YOUTUBE = "youtube"


class JobStatus(str, enum.Enum):
    """Enumeration for the transcription job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionJob(BaseModel):
    """Data model representing a single transcription job."""
    source: str
    source_type: SourceType
    status: JobStatus = JobStatus.PENDING
    result_text: Optional[str] = None
    error_message: Optional[str] = None