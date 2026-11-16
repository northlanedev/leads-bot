"""Input validation for the lead form. Pure functions, no Telegram imports."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

_NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі' -]{2,60}$")


def validate_name(raw: str) -> str | None:
    """Return a cleaned name or None if it does not look like a person's name."""
    name = " ".join(raw.split())
    if not _NAME_RE.match(name):
        return None
    return name.title() if name.islower() or name.isupper() else name


def normalize_phone(raw: str) -> str | None:
    """Normalize a phone number to +<digits>.

    Accepts the common local formats used in Kazakhstan / Russia
    (8 777 123-45-67, +7 (777) 123 45 67) and international numbers.
    Returns None for anything that cannot be a phone number.
    """
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] == "8":
        digits = "7" + digits[1:]
    elif len(digits) == 10 and digits[0] in "79":
        # 10 digits without the country code, e.g. 777 123 45 67
        digits = "7" + digits
    if not 10 <= len(digits) <= 15:
        return None
    return "+" + digits


_DATE_TIME_RE = re.compile(
    r"^(?:(?P<word>сегодня|завтра|today|tomorrow)|(?P<d>\d{1,2})[./](?P<m>\d{1,2})(?:[./](?P<y>\d{2,4}))?)"
    r"\s+(?P<h>\d{1,2})[:.](?P<min>\d{2})$",
    re.IGNORECASE,
)


def parse_slot(
    text: str,
    now: datetime,
    work_start: int = 9,
    work_end: int = 20,
) -> datetime | None:
    """Parse a desired appointment time.

    Supported: "25.11 14:00", "25.11.2026 14:00", "завтра 15:00", "сегодня 18:30".
    The slot must be in the future and inside working hours [work_start, work_end).
    """
    m = _DATE_TIME_RE.match(text.strip())
    if not m:
        return None
    hour, minute = int(m["h"]), int(m["min"])
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return None

    if m["word"]:
        base = now.date()
        if m["word"].lower() in ("завтра", "tomorrow"):
            base = base + timedelta(days=1)
        day, month, year = base.day, base.month, base.year
    else:
        day, month = int(m["d"]), int(m["m"])
        if m["y"]:
            year = int(m["y"])
            if year < 100:
                year += 2000
        else:
            year = now.year
    try:
        slot = datetime(year, month, day, hour, minute)
    except ValueError:
        return None

    # "25.01" typed in December means next January.
    if not m["word"] and not m["y"] and slot < now - timedelta(days=1):
        try:
            slot = slot.replace(year=slot.year + 1)
        except ValueError:
            return None

    if slot <= now:
        return None
    if not (work_start <= slot.hour < work_end):
        return None
    return slot
