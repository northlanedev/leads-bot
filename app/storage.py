"""SQLite storage for leads. No Telegram imports, fully unit-tested."""
from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import dataclass
from datetime import datetime

STATUSES = {
    "new": "Новая",
    "in_work": "В работе",
    "done": "Выполнена",
    "cancelled": "Отменена",
}


@dataclass
class Lead:
    id: int | None
    user_id: int
    username: str | None
    service: str
    name: str
    phone: str
    slot: datetime
    comment: str
    status: str = "new"
    created_at: datetime | None = None


class LeadStore:
    def __init__(self, path: str = "leads.db") -> None:
        self.path = path
        # Keep one connection for in-memory databases, otherwise data would vanish.
        self._memory_conn = sqlite3.connect(":memory:") if path == ":memory:" else None
        self._init()

    def _conn(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        return sqlite3.connect(self.path)

    def _run(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        conn = self._conn()
        cur = conn.execute(sql, params)
        conn.commit()
        if self._memory_conn is None:
            rows = cur.fetchall()
            lastrowid, rowcount = cur.lastrowid, cur.rowcount
            conn.close()
            return _Result(rows, lastrowid, rowcount)  # type: ignore[return-value]
        return cur

    def _init(self) -> None:
        self._run(
            """CREATE TABLE IF NOT EXISTS leads (
                   id         INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id    INTEGER NOT NULL,
                   username   TEXT,
                   service    TEXT NOT NULL,
                   name       TEXT NOT NULL,
                   phone      TEXT NOT NULL,
                   slot       TEXT NOT NULL,
                   comment    TEXT NOT NULL DEFAULT '',
                   status     TEXT NOT NULL DEFAULT 'new',
                   created_at TEXT NOT NULL
               )"""
        )

    # ------------------------------------------------------------------ write
    def add(self, lead: Lead) -> int:
        created = lead.created_at or datetime.now()
        cur = self._run(
            "INSERT INTO leads(user_id, username, service, name, phone, slot, comment, status, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (
                lead.user_id, lead.username, lead.service, lead.name, lead.phone,
                lead.slot.isoformat(timespec="minutes"), lead.comment, lead.status,
                created.isoformat(timespec="seconds"),
            ),
        )
        return int(cur.lastrowid)

    def set_status(self, lead_id: int, status: str) -> bool:
        if status not in STATUSES:
            raise ValueError(f"unknown status: {status}")
        cur = self._run("UPDATE leads SET status=? WHERE id=?", (status, lead_id))
        return cur.rowcount > 0

    # ------------------------------------------------------------------- read
    def get(self, lead_id: int) -> Lead | None:
        rows = self._run("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchall()
        return _row_to_lead(rows[0]) if rows else None

    def latest(self, limit: int = 10, status: str | None = None) -> list[Lead]:
        if status:
            rows = self._run(
                "SELECT * FROM leads WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)
            ).fetchall()
        else:
            rows = self._run("SELECT * FROM leads ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_row_to_lead(r) for r in rows]

    def busy_slots(self, day_start: datetime, day_end: datetime) -> set[datetime]:
        """Slots already taken by active (not cancelled) leads in a time range."""
        rows = self._run(
            "SELECT slot FROM leads WHERE status!='cancelled' AND slot>=? AND slot<?",
            (day_start.isoformat(timespec="minutes"), day_end.isoformat(timespec="minutes")),
        ).fetchall()
        return {datetime.fromisoformat(r[0]) for r in rows}

    def export_csv(self) -> bytes:
        """All leads as a UTF-8 CSV (with BOM so Excel opens Cyrillic correctly)."""
        rows = self._run("SELECT * FROM leads ORDER BY id").fetchall()
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["ID", "Создана", "Услуга", "Имя", "Телефон", "Время", "Комментарий", "Статус", "Telegram"])
        for r in rows:
            lead = _row_to_lead(r)
            w.writerow([
                lead.id,
                lead.created_at.strftime("%d.%m.%Y %H:%M") if lead.created_at else "",
                lead.service, lead.name, lead.phone,
                lead.slot.strftime("%d.%m.%Y %H:%M"), lead.comment,
                STATUSES.get(lead.status, lead.status),
                f"@{lead.username}" if lead.username else lead.user_id,
            ])
        return ("﻿" + buf.getvalue()).encode("utf-8")


class _Result:
    """Detached cursor result for file databases (connection already closed)."""

    def __init__(self, rows, lastrowid, rowcount):
        self._rows, self.lastrowid, self.rowcount = rows, lastrowid, rowcount

    def fetchall(self):
        return self._rows


def _row_to_lead(r: tuple) -> Lead:
    return Lead(
        id=r[0], user_id=r[1], username=r[2], service=r[3], name=r[4], phone=r[5],
        slot=datetime.fromisoformat(r[6]), comment=r[7], status=r[8],
        created_at=datetime.fromisoformat(r[9]),
    )
