# 会话注册表：记录 thread_id / 标题 / 时间，供前端会话列表使用
# 注意：这里只存"会话元数据"；对话内容存在 LangGraph 的 checkpointer 里（见 app/main.py）
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "rescources" / "sessions.db"

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                thread_id  TEXT PRIMARY KEY,
                title      TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


_init_db()


def create_session(thread_id: str, title: str) -> dict:
    """创建会话；title 一般取用户第一条消息的前 30 个字"""
    now = datetime.now().isoformat(timespec="seconds")
    with _lock, _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (thread_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (thread_id, title or "新会话", now, now),
        )
    return {"thread_id": thread_id, "title": title or "新会话", "created_at": now, "updated_at": now}


def touch_session(thread_id: str) -> None:
    """会话有新消息时刷新 updated_at，前端据此排序"""
    now = datetime.now().isoformat(timespec="seconds")
    with _lock, _conn() as conn:
        conn.execute("UPDATE sessions SET updated_at = ? WHERE thread_id = ?", (now, thread_id))


def list_sessions() -> list[dict]:
    with _lock, _conn() as conn:
        rows = conn.execute(
            "SELECT thread_id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_session(thread_id: str) -> bool:
    with _lock, _conn() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE thread_id = ?", (thread_id,))
    return cur.rowcount > 0


session_service = type("SessionService", (), {
    "create": staticmethod(create_session),
    "touch": staticmethod(touch_session),
    "list": staticmethod(list_sessions),
    "delete": staticmethod(delete_session),
})()
