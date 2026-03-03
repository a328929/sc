from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"


class FileStatus(str, Enum):
    pending = "pending"
    uploading = "uploading"
    completed = "completed"
    failed = "failed"
    paused = "paused"


class CreateFileItem(BaseModel):
    name: str = Field(min_length=1)
    size: int = Field(ge=0)
    relative_path: Optional[str] = None
    mime_type: Optional[str] = None


class CreateTaskRequest(BaseModel):
    label: str = Field(default="批量上传任务", min_length=1)
    files: list[CreateFileItem] = Field(default_factory=list)


class TaskSummary(BaseModel):
    id: int
    label: str
    status: TaskStatus
    total_files: int
    completed_files: int
    failed_files: int
    total_bytes: int
    uploaded_bytes: int
    created_at: datetime
    updated_at: datetime


class FileProgress(BaseModel):
    id: int
    task_id: int
    name: str
    size: int
    relative_path: Optional[str]
    mime_type: Optional[str]
    status: FileStatus
    progress: float
    uploaded_bytes: int
    speed_kbps: float
    error_message: Optional[str]


class TaskDetail(TaskSummary):
    files: list[FileProgress]


class TaskEvent(BaseModel):
    id: int
    task_id: int
    level: str
    message: str
    created_at: datetime


class ConfigPreview(BaseModel):
    target_channel: str
    session_file: str
    concurrency: int
    retry_max: int


class UploadTaskCreateResponse(BaseModel):
    task: TaskSummary
    accepted_files: int
