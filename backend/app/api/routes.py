from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

from app.models.schemas import (
    ConfigPreview,
    CreateFileItem,
    CreateTaskRequest,
    TaskDetail,
    TaskEvent,
    TaskSummary,
    TaskStatus,
    UploadTaskCreateResponse,
)

router = APIRouter(prefix="/api")


def get_services():
    from app.main import app_state

    return app_state


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config", response_model=ConfigPreview)
async def config_preview(services=Depends(get_services)) -> ConfigPreview:
    settings = services.settings
    return ConfigPreview(
        target_channel=settings.telegram.target_channel,
        session_file=settings.telegram.session_file,
        concurrency=settings.upload.concurrency,
        retry_max=settings.upload.retry_max,
    )


@router.post("/tasks/upload", response_model=UploadTaskCreateResponse)
async def create_task_by_upload(
    label: str = Form("批量上传任务"),
    files: list[UploadFile] = File(...),
    services=Depends(get_services),
) -> UploadTaskCreateResponse:
    if not files:
        raise HTTPException(status_code=400, detail="至少需要一个文件")

    upload_dir = Path(services.settings.upload.uploads_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_items: list[CreateFileItem] = []
    for item in files:
        filename = item.filename or f"unnamed-{uuid.uuid4().hex}.bin"
        token = uuid.uuid4().hex
        destination = upload_dir / f"{token}_{filename}"
        with destination.open("wb") as buffer:
            shutil.copyfileobj(item.file, buffer)
        size = destination.stat().st_size
        file_items.append(
            CreateFileItem(
                name=filename,
                size=size,
                relative_path=str(destination.resolve()),
                mime_type=item.content_type,
            )
        )

    payload = CreateTaskRequest(label=label, files=file_items)
    task_id = await services.repo.create_task(payload)
    task = await services.repo.get_task(task_id)
    return UploadTaskCreateResponse(task=TaskSummary(**task), accepted_files=len(file_items))


@router.post("/tasks", response_model=TaskSummary)
async def create_task(payload: CreateTaskRequest, services=Depends(get_services)) -> TaskSummary:
    if not payload.files:
        raise HTTPException(status_code=400, detail="至少需要一个文件")
    task_id = await services.repo.create_task(payload)
    task = await services.repo.get_task(task_id)
    return TaskSummary(**task)


@router.get("/tasks", response_model=list[TaskSummary])
async def list_tasks(services=Depends(get_services)) -> list[TaskSummary]:
    tasks = await services.repo.list_tasks()
    return [TaskSummary(**item) for item in tasks]


@router.get("/tasks/{task_id}", response_model=TaskDetail)
async def get_task(task_id: int, services=Depends(get_services)) -> TaskDetail:
    task = await services.repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    files = await services.repo.list_task_files(task_id)
    return TaskDetail(**task, files=files)


@router.get("/tasks/{task_id}/events", response_model=list[TaskEvent])
async def get_events(task_id: int, services=Depends(get_services)) -> list[TaskEvent]:
    events = await services.repo.list_events(task_id)
    return [TaskEvent(**item) for item in events]


@router.post("/tasks/{task_id}/start", response_model=TaskSummary)
async def start_task(task_id: int, services=Depends(get_services)) -> TaskSummary:
    task = await services.repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["status"] in {TaskStatus.completed.value, TaskStatus.failed.value}:
        raise HTTPException(status_code=400, detail="任务已结束，不能再次开始")
    services.runner.start(task_id)
    updated = await services.repo.get_task(task_id)
    return TaskSummary(**updated)


@router.post("/tasks/{task_id}/pause", response_model=TaskSummary)
async def pause_task(task_id: int, services=Depends(get_services)) -> TaskSummary:
    task = await services.repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    await services.runner.pause(task_id)
    updated = await services.repo.get_task(task_id)
    return TaskSummary(**updated)


@router.websocket("/ws/tasks/{task_id}")
async def task_ws(task_id: int, websocket: WebSocket):
    services = get_services()
    await services.hub.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        services.hub.disconnect(task_id, websocket)
