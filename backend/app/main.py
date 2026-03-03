from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI

from app.api.routes import router
from app.core.settings import Settings, load_settings
from app.db.database import init_db
from app.db.repository import Repository
from app.services.task_runner import SocketHub, TaskRunner
from app.services.telegram_uploader import TelegramUploader


@dataclass
class AppState:
    settings: Settings
    repo: Repository
    hub: SocketHub
    runner: TaskRunner
    tg_uploader: TelegramUploader


settings = load_settings()
repo = Repository(settings.database.path)
hub = SocketHub()
tg_uploader = TelegramUploader(settings)
runner = TaskRunner(repo=repo, settings=settings, hub=hub, tg_uploader=tg_uploader)
app_state = AppState(settings=settings, repo=repo, hub=hub, runner=runner, tg_uploader=tg_uploader)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db(settings.database.path)
    try:
        yield
    finally:
        await runner.shutdown()
        await tg_uploader.close()


app = FastAPI(title="Telegram Uploader Backend", version="0.3.1", lifespan=lifespan)
app.include_router(router)
