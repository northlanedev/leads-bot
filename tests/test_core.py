from datetime import datetime

import pytest

from app.storage import Lead, LeadStore
from app.texts import lead_card, leads_list
from app.validators import normalize_phone, parse_slot, validate_name

NOW = datetime(2026, 11, 16, 12, 0)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("8 777 123-45-67", "+77771234567"),
        ("+7 (777) 123 45 67", "+77771234567"),
        ("777 123 45 67", "+77771234567"),
        ("+44 20 7946 0958", "+442079460958"),
        ("12345", None),
        ("phone please", None),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  иван  ", "Иван"),
        ("АННА-МАРИЯ", "Анна-Мария"),
        ("Данияр Ахметов", "Данияр Ахметов"),
        ("John", "John"),
        ("a", None),
        ("123", None),
        ("<script>", None),
    ],
)
def test_validate_name(raw, expected):
    assert validate_name(raw) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("завтра 15:30", datetime(2026, 11, 17, 15, 30)),
        ("сегодня 18:00", datetime(2026, 11, 16, 18, 0)),
        ("25.11 14:00", datetime(2026, 11, 25, 14, 0)),
        ("25.11.2026 9:05", datetime(2026, 11, 25, 9, 5)),
        ("10.01 10:00", datetime(2027, 1, 10, 10, 0)),  # rolls over to next year
        ("сегодня 10:00", None),  # already in the past
        ("завтра 22:00", None),  # outside working hours
        ("31.02 10:00", None),  # no such date
        ("когда-нибудь", None),
    ],
)
def test_parse_slot(text, expected):
    assert parse_slot(text, NOW) == expected


def _lead(**kw) -> Lead:
    base = dict(
        id=None, user_id=1, username="client", service="Стрижка", name="Иван",
        phone="+77771234567", slot=datetime(2026, 11, 17, 15, 0), comment="",
    )
    base.update(kw)
    return Lead(**base)


@pytest.fixture(params=[":memory:", "file"])
def store(request, tmp_path):
    path = ":memory:" if request.param == ":memory:" else str(tmp_path / "leads.db")
    return LeadStore(path)


def test_add_get_and_status(store):
    lead_id = store.add(_lead(comment="Первый раз"))
    got = store.get(lead_id)
    assert got.name == "Иван" and got.comment == "Первый раз" and got.status == "new"
    assert store.set_status(lead_id, "in_work") is True
    assert store.get(lead_id).status == "in_work"
    assert store.set_status(999, "done") is False
    with pytest.raises(ValueError):
        store.set_status(lead_id, "unknown")


def test_latest_and_filter(store):
    ids = [store.add(_lead(name=f"Клиент{i}", slot=datetime(2026, 11, 17, 10 + i))) for i in range(3)]
    store.set_status(ids[0], "done")
    assert [l.id for l in store.latest(10)] == ids[::-1]
    assert [l.id for l in store.latest(10, status="new")] == ids[:0:-1]


def test_busy_slots_ignore_cancelled(store):
    a = store.add(_lead(slot=datetime(2026, 11, 17, 10, 0)))
    store.add(_lead(slot=datetime(2026, 11, 17, 11, 0)))
    store.set_status(a, "cancelled")
    busy = store.busy_slots(datetime(2026, 11, 17), datetime(2026, 11, 18))
    assert busy == {datetime(2026, 11, 17, 11, 0)}


def test_export_csv_is_excel_friendly(store):
    store.add(_lead(comment="позвонить вечером"))
    data = store.export_csv()
    assert data.startswith("﻿".encode())
    text = data.decode("utf-8-sig")
    header, row = text.strip().splitlines()
    assert header.split(";")[:4] == ["ID", "Создана", "Услуга", "Имя"]
    assert "позвонить вечером" in row and "@client" in row and "Новая" in row


def test_texts_escape_html():
    card = lead_card(_lead(id=7, name="Иван", comment="<b>hack</b>"), for_admin=True)
    assert "&lt;b&gt;hack&lt;/b&gt;" in card and "Заявка №7" in card
    assert leads_list([]) == "Заявок пока нет."
