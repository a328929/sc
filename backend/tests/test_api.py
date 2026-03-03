from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.settings import Settings
from app.db.database import init_db
from app.db.repository import Repository
from app.services.task_runner import SocketHub, TaskRunner


class DummyTelegramUploader:
    async def upload_file(self, local_path: str, caption: str, progress_cb):
        size = Path(local_path).stat().st_size
        await progress_cb(size, size)
        return 12345

    async def close(self):
        return None


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    uploads_dir = tmp_path / "uploads"
    settings = Settings.model_validate(
        {
            "database": {"path": str(db_path)},
            "upload": {"progress_tick_ms": 20, "uploads_dir": str(uploads_dir), "concurrency": 1},
            "telegram": {"target_channel": "@demo", "session_file": "my_session.session"},
        }
    )

    asyncio.run(init_db(str(db_path)))

    repo = Repository(str(db_path))
    hub = SocketHub()
    tg = DummyTelegramUploader()
    runner = TaskRunner(repo, settings, hub, tg)
    main_module.app_state = main_module.AppState(settings=settings, repo=repo, hub=hub, runner=runner, tg_uploader=tg)

    with TestClient(main_module.app) as tc:
        yield tc


def test_create_and_fetch_task(client: TestClient):
    payload = {
        "label": "test task",
        "files": [
            {"name": "a.txt", "size": 1000, "relative_path": "/tmp/a.txt"},
            {"name": "b.txt", "size": 2000, "relative_path": "/tmp/b.txt"},
        ],
    }
    created = client.post("/api/tasks", json=payload)
    assert created.status_code == 200
    task_id = created.json()["id"]

    detail = client.get(f"/api/tasks/{task_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["total_files"] == 2
    assert len(body["files"]) == 2


def test_upload_endpoint_and_start_task(client: TestClient):
    files = [
        ("files", ("x.txt", b"abc", "text/plain")),
        ("files", ("y.txt", b"12345", "text/plain")),
    ]
    created = client.post("/api/tasks/upload", data={"label": "run"}, files=files)
    assert created.status_code == 200
    task_id = created.json()["task"]["id"]

    started = client.post(f"/api/tasks/{task_id}/start")
    assert started.status_code == 200

    detail = client.get(f"/api/tasks/{task_id}").json()
    assert detail["total_files"] == 2
    assert detail["status"] in {"pending", "running", "completed"}


def test_upload_endpoint_can_append_files_to_existing_task(client: TestClient):
    first_batch = [
        ("files", ("a.txt", b"a", "text/plain")),
        ("files", ("b.txt", b"bb", "text/plain")),
    ]
    created = client.post("/api/tasks/upload", data={"label": "batch"}, files=first_batch)
    assert created.status_code == 200
    task_id = created.json()["task"]["id"]

    second_batch = [
        ("files", ("c.txt", b"ccc", "text/plain")),
    ]
    appended = client.post(
        "/api/tasks/upload",
        data={"label": "batch", "task_id": str(task_id)},
        files=second_batch,
    )
    assert appended.status_code == 200
    assert appended.json()["task"]["id"] == task_id

    detail = client.get(f"/api/tasks/{task_id}").json()
    assert detail["total_files"] == 3
    assert detail["total_bytes"] == 6
