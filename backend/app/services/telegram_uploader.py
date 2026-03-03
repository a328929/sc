from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Awaitable, Callable

from telethon import TelegramClient
from telethon.errors import FloodWaitError

from app.core.settings import Settings

ProgressCallback = Callable[[int, int], Awaitable[None]]


class TelegramUploader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: TelegramClient | None = None

    async def _get_client(self) -> TelegramClient:
        if self._client and self._client.is_connected():
            return self._client

        session_path = Path(self.settings.telegram.session_file)
        if not session_path.is_absolute():
            session_path = Path.cwd() / session_path

        client = TelegramClient(str(session_path), self.settings.telegram.api_id, self.settings.telegram.api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram session 未授权，请先生成可用的 my_session.session")

        self._client = client
        return client

    async def close(self) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def upload_file(
        self,
        local_path: str,
        caption: str,
        progress_cb: ProgressCallback,
    ) -> int | None:
        retries = self.settings.upload.retry_max
        for attempt in range(retries + 1):
            try:
                client = await self._get_client()
                message = await client.send_file(
                    entity=self.settings.telegram.target_channel,
                    file=local_path,
                    caption=caption,
                    progress_callback=lambda sent, total: asyncio.create_task(progress_cb(sent, total)),
                )
                return int(message.id) if message else None
            except FloodWaitError as exc:
                await asyncio.sleep(exc.seconds + 1)
            except Exception:
                if attempt >= retries:
                    raise
                await asyncio.sleep(self.settings.upload.retry_backoff_seconds * (attempt + 1))
        return None
