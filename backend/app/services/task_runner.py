from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from pathlib import Path

from fastapi import WebSocket

from app.core.settings import Settings
from app.db.repository import Repository
from app.models.schemas import FileStatus, TaskStatus
from app.services.telegram_uploader import TelegramUploader


class SocketHub:
    def __init__(self) -> None:
        self.clients: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, task_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self.clients[task_id].add(ws)

    def disconnect(self, task_id: int, ws: WebSocket) -> None:
        self.clients[task_id].discard(ws)

    async def publish(self, task_id: int, payload: dict) -> None:
        stale: list[WebSocket] = []
        for ws in self.clients.get(task_id, set()):
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(task_id, ws)


class TaskRunner:
    def __init__(self, repo: Repository, settings: Settings, hub: SocketHub, tg_uploader: TelegramUploader):
        self.repo = repo
        self.settings = settings
        self.hub = hub
        self.tg_uploader = tg_uploader
        self.running_tasks: dict[int, asyncio.Task] = {}

    def start(self, task_id: int) -> None:
        if task_id in self.running_tasks and not self.running_tasks[task_id].done():
            return
        self.running_tasks[task_id] = asyncio.create_task(self._run_task(task_id))

    async def shutdown(self) -> None:
        tasks = [task for task in self.running_tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def pause(self, task_id: int) -> None:
        await self.repo.update_task_status(task_id, TaskStatus.paused)
        await self.repo.add_event(task_id, "warning", "任务已暂停")
        await self.hub.publish(task_id, {"type": "task_status", "status": "paused"})

    async def _run_task(self, task_id: int) -> None:
        await self.repo.reset_paused_files_to_pending(task_id)
        await self.repo.update_task_status(task_id, TaskStatus.running)
        await self.repo.add_event(task_id, "info", "任务开始执行")
        await self.hub.publish(task_id, {"type": "task_status", "status": "running"})

        async def worker() -> None:
            while True:
                task = await self.repo.get_task(task_id)
                if not task or task["status"] == TaskStatus.paused.value:
                    return

                file_item = await self.repo.claim_next_file(task_id)
                if not file_item:
                    return

                await self.repo.add_event(task_id, "info", f"开始上传 {file_item['name']}")
                file_size = max(int(file_item["size"]), 1)
                local_path = file_item["relative_path"]
                if not local_path or not Path(local_path).exists():
                    await self.repo.mark_file_failed(file_item["id"], 0, "服务端文件不存在")
                    await self.repo.add_event(task_id, "error", f"文件丢失: {file_item['name']}")
                    await self.repo.refresh_task_aggregates(task_id)
                    continue

                last_emit_at = 0.0
                last_sent = 0

                async def on_progress(sent: int, total: int) -> None:
                    nonlocal last_emit_at, last_sent
                    now = time.monotonic()
                    elapsed = now - last_emit_at
                    if elapsed < self.settings.upload.progress_tick_ms / 1000:
                        return
                    delta = max(sent - last_sent, 0)
                    speed = (delta / max(elapsed, 0.001)) / 1024
                    last_emit_at = now
                    last_sent = sent
                    progress = (sent / max(total, 1)) * 100

                    await self.repo.update_file_progress(
                        file_item["id"],
                        FileStatus.uploading,
                        sent,
                        progress,
                        speed,
                    )
                    await self.repo.refresh_task_aggregates(task_id)
                    await self.hub.publish(
                        task_id,
                        {
                            "type": "file_progress",
                            "file_id": file_item["id"],
                            "progress": progress,
                            "uploaded_bytes": sent,
                            "speed_kbps": speed,
                            "status": FileStatus.uploading.value,
                        },
                    )

                try:
                    message_id = await self.tg_uploader.upload_file(
                        local_path=local_path,
                        caption=file_item["name"],
                        progress_cb=on_progress,
                    )
                    await self.repo.mark_file_completed(file_item["id"], file_size, message_id)
                    await self.repo.add_event(task_id, "info", f"上传完成 {file_item['name']}")
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    await self.repo.mark_file_failed(file_item["id"], 0, str(exc))
                    await self.repo.add_event(task_id, "error", f"上传失败 {file_item['name']}: {exc}")
                await self.repo.refresh_task_aggregates(task_id)

        workers = [asyncio.create_task(worker()) for _ in range(max(self.settings.upload.concurrency, 1))]
        try:
            await asyncio.gather(*workers)
        except asyncio.CancelledError:
            for worker_task in workers:
                worker_task.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            raise

        await self.repo.refresh_task_aggregates(task_id)
        task = await self.repo.get_task(task_id)
        if task and task["status"] == TaskStatus.paused.value:
            return
        if task and task["failed_files"] > 0:
            await self.repo.update_task_status(task_id, TaskStatus.failed)
            end_status = TaskStatus.failed.value
        else:
            await self.repo.update_task_status(task_id, TaskStatus.completed)
            end_status = TaskStatus.completed.value
        await self.repo.add_event(task_id, "info", f"任务结束，状态: {end_status}")
        await self.hub.publish(task_id, {"type": "task_status", "status": end_status})
