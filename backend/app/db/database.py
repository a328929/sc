from __future__ import annotations

from pathlib import Path

import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  label TEXT NOT NULL,
  status TEXT NOT NULL,
  total_files INTEGER NOT NULL,
  completed_files INTEGER NOT NULL DEFAULT 0,
  failed_files INTEGER NOT NULL DEFAULT 0,
  total_bytes INTEGER NOT NULL,
  uploaded_bytes INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  size INTEGER NOT NULL,
  relative_path TEXT,
  mime_type TEXT,
  status TEXT NOT NULL,
  progress REAL NOT NULL DEFAULT 0,
  uploaded_bytes INTEGER NOT NULL DEFAULT 0,
  speed_kbps REAL NOT NULL DEFAULT 0,
  error_message TEXT,
  telegram_message_id INTEGER,
  FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_files_task_status ON files(task_id, status);
CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id);
"""


async def init_db(path: str) -> None:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA_SQL)
        # lightweight migration for old schema
        columns = [row[1] for row in await (await db.execute("PRAGMA table_info(files)")).fetchall()]
        if "telegram_message_id" not in columns:
            await db.execute("ALTER TABLE files ADD COLUMN telegram_message_id INTEGER")
        await db.commit()
