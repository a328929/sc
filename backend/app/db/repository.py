from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import aiosqlite

from app.models.schemas import CreateFileItem, CreateTaskRequest, FileStatus, TaskStatus


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def _open(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self.db_path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys=ON")
        return db

    async def create_task(self, payload: CreateTaskRequest) -> int:
        created = now_iso()
        total_bytes = sum(item.size for item in payload.files)
        db = await self._open()
        try:
            cursor = await db.execute(
                """
                INSERT INTO tasks(label,status,total_files,total_bytes,created_at,updated_at)
                VALUES(?,?,?,?,?,?)
                """,
                (payload.label, TaskStatus.pending.value, len(payload.files), total_bytes, created, created),
            )
            task_id = cursor.lastrowid
            for item in payload.files:
                await db.execute(
                    """
                    INSERT INTO files(task_id,name,size,relative_path,mime_type,status)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (task_id, item.name, item.size, item.relative_path, item.mime_type, FileStatus.pending.value),
                )
            await db.execute(
                "INSERT INTO events(task_id,level,message,created_at) VALUES(?,?,?,?)",
                (task_id, "info", f"任务已创建，文件数: {len(payload.files)}", created),
            )
            await db.commit()
            return int(task_id)
        finally:
            await db.close()

    async def append_files_to_task(self, task_id: int, files: list[CreateFileItem]) -> None:
        if not files:
            return

        db = await self._open()
        try:
            for item in files:
                await db.execute(
                    """
                    INSERT INTO files(task_id,name,size,relative_path,mime_type,status)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (task_id, item.name, item.size, item.relative_path, item.mime_type, FileStatus.pending.value),
                )
            await db.execute(
                """
                UPDATE tasks
                SET total_files=total_files+?, total_bytes=total_bytes+?, updated_at=?
                WHERE id=?
                """,
                (len(files), sum(item.size for item in files), now_iso(), task_id),
            )
            await db.execute(
                "INSERT INTO events(task_id,level,message,created_at) VALUES(?,?,?,?)",
                (task_id, "info", f"追加文件: {len(files)}", now_iso()),
            )
            await db.commit()
        finally:
            await db.close()

    async def list_tasks(self) -> list[dict[str, Any]]:
        db = await self._open()
        try:
            rows = await (await db.execute("SELECT * FROM tasks ORDER BY id DESC")).fetchall()
            return [dict(r) for r in rows]
        finally:
            await db.close()

    async def get_task(self, task_id: int) -> dict[str, Any] | None:
        db = await self._open()
        try:
            row = await (await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))).fetchone()
            return dict(row) if row else None
        finally:
            await db.close()

    async def list_task_files(self, task_id: int) -> list[dict[str, Any]]:
        db = await self._open()
        try:
            rows = await (await db.execute("SELECT * FROM files WHERE task_id=? ORDER BY id", (task_id,))).fetchall()
            return [dict(r) for r in rows]
        finally:
            await db.close()

    async def list_events(self, task_id: int, limit: int = 200) -> list[dict[str, Any]]:
        db = await self._open()
        try:
            rows = await (
                await db.execute("SELECT * FROM events WHERE task_id=? ORDER BY id DESC LIMIT ?", (task_id, limit))
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            await db.close()

    async def update_task_status(self, task_id: int, status: TaskStatus) -> None:
        db = await self._open()
        try:
            await db.execute("UPDATE tasks SET status=?,updated_at=? WHERE id=?", (status.value, now_iso(), task_id))
            await db.commit()
        finally:
            await db.close()

    async def add_event(self, task_id: int, level: str, message: str) -> None:
        db = await self._open()
        try:
            await db.execute(
                "INSERT INTO events(task_id,level,message,created_at) VALUES(?,?,?,?)",
                (task_id, level, message, now_iso()),
            )
            await db.commit()
        finally:
            await db.close()

    async def reset_paused_files_to_pending(self, task_id: int) -> None:
        db = await self._open()
        try:
            await db.execute(
                "UPDATE files SET status=? WHERE task_id=? AND status=?",
                (FileStatus.pending.value, task_id, FileStatus.paused.value),
            )
            await db.commit()
        finally:
            await db.close()

    async def claim_next_file(self, task_id: int) -> dict[str, Any] | None:
        db = await self._open()
        try:
            row = await (
                await db.execute(
                    "SELECT * FROM files WHERE task_id=? AND status=? ORDER BY id LIMIT 1",
                    (task_id, FileStatus.pending.value),
                )
            ).fetchone()
            if not row:
                return None
            await db.execute("UPDATE files SET status=? WHERE id=?", (FileStatus.uploading.value, row["id"]))
            await db.commit()
            fresh = await (await db.execute("SELECT * FROM files WHERE id=?", (row["id"],))).fetchone()
            return dict(fresh) if fresh else None
        finally:
            await db.close()

    async def update_file_progress(
        self, file_id: int, status: FileStatus, uploaded_bytes: int, progress: float, speed_kbps: float
    ) -> None:
        db = await self._open()
        try:
            await db.execute(
                "UPDATE files SET status=?,uploaded_bytes=?,progress=?,speed_kbps=? WHERE id=?",
                (status.value, uploaded_bytes, progress, speed_kbps, file_id),
            )
            await db.commit()
        finally:
            await db.close()

    async def mark_file_completed(self, file_id: int, uploaded_bytes: int, telegram_message_id: int | None) -> None:
        db = await self._open()
        try:
            await db.execute(
                """
                UPDATE files
                SET status=?,uploaded_bytes=?,progress=100,speed_kbps=0,error_message=NULL,telegram_message_id=?
                WHERE id=?
                """,
                (FileStatus.completed.value, uploaded_bytes, telegram_message_id, file_id),
            )
            await db.commit()
        finally:
            await db.close()

    async def mark_file_failed(self, file_id: int, uploaded_bytes: int, error_message: str) -> None:
        db = await self._open()
        try:
            await db.execute(
                """
                UPDATE files
                SET status=?,uploaded_bytes=?,error_message=?,speed_kbps=0
                WHERE id=?
                """,
                (FileStatus.failed.value, uploaded_bytes, error_message[:500], file_id),
            )
            await db.commit()
        finally:
            await db.close()

    async def refresh_task_aggregates(self, task_id: int) -> None:
        db = await self._open()
        try:
            row = await (
                await db.execute(
                    """
                    SELECT
                      SUM(uploaded_bytes) AS uploaded_bytes,
                      SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed_files,
                      SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS failed_files
                    FROM files WHERE task_id=?
                    """,
                    (task_id,),
                )
            ).fetchone()
            await db.execute(
                "UPDATE tasks SET uploaded_bytes=?,completed_files=?,failed_files=?,updated_at=? WHERE id=?",
                (
                    int(row["uploaded_bytes"] or 0),
                    int(row["completed_files"] or 0),
                    int(row["failed_files"] or 0),
                    now_iso(),
                    task_id,
                ),
            )
            await db.commit()
        finally:
            await db.close()
