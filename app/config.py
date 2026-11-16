"""Configuration from environment variables (.env supported)."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: tuple[int, ...]
    db_path: str
    services: tuple[str, ...]
    work_start: int
    work_end: int


def _ids(raw: str) -> tuple[int, ...]:
    return tuple(int(x) for x in raw.replace(" ", "").split(",") if x)


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise SystemExit("BOT_TOKEN is not set (see .env.example)")
    services = os.getenv("SERVICES", "Консультация,Стрижка,Окрашивание,Маникюр")
    return Config(
        bot_token=token,
        admin_ids=_ids(os.getenv("ADMIN_IDS", "")),
        db_path=os.getenv("DB_PATH", "leads.db"),
        services=tuple(s.strip() for s in services.split(",") if s.strip()),
        work_start=int(os.getenv("WORK_START", "9")),
        work_end=int(os.getenv("WORK_END", "20")),
    )
