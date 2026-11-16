"""User-facing texts and message formatting (no Telegram imports)."""
from __future__ import annotations

from html import escape

from .storage import STATUSES, Lead

START = (
    "Здравствуйте! 👋\n"
    "Я помогу записаться на услугу за минуту.\n\n"
    "Выберите, что вас интересует:"
)
ASK_NAME = "Как к вам обращаться? Напишите имя."
BAD_NAME = "Пожалуйста, напишите имя буквами (2–60 символов)."
ASK_PHONE = "Оставьте номер телефона — нажмите кнопку ниже или напишите номер."
BAD_PHONE = "Не получилось распознать номер. Пример: +7 777 123 45 67"
ASK_SLOT = (
    "Когда вам удобно? Напишите дату и время, например:\n"
    "<code>25.11 14:00</code> или <code>завтра 15:30</code>\n"
    "Работаем с {start}:00 до {end}:00."
)
BAD_SLOT = "Не подходит: нужна будущая дата в рабочее время, например <code>завтра 15:00</code>."
SLOT_TAKEN = "Это время уже занято 😔 Выберите, пожалуйста, другое."
ASK_COMMENT = "Есть пожелания или вопросы? Напишите их или нажмите «Пропустить»."
CONFIRM = "Проверьте заявку:\n\n{card}\n\nВсё верно?"
DONE = "✅ Заявка №{id} принята! Мы свяжемся с вами для подтверждения."
CANCELLED = "Заявка отменена. Чтобы начать заново — /start"


def lead_card(lead: Lead, *, for_admin: bool = False) -> str:
    lines = [
        f"<b>Услуга:</b> {escape(lead.service)}",
        f"<b>Имя:</b> {escape(lead.name)}",
        f"<b>Телефон:</b> {escape(lead.phone)}",
        f"<b>Время:</b> {lead.slot.strftime('%d.%m.%Y %H:%M')}",
    ]
    if lead.comment:
        lines.append(f"<b>Комментарий:</b> {escape(lead.comment)}")
    if for_admin:
        who = f"@{escape(lead.username)}" if lead.username else f"id {lead.user_id}"
        header = f"🆕 <b>Заявка №{lead.id}</b> · {STATUSES.get(lead.status, lead.status)}"
        lines = [header, *lines, f"<b>Telegram:</b> {who}"]
    return "\n".join(lines)


def leads_list(leads: list[Lead]) -> str:
    if not leads:
        return "Заявок пока нет."
    rows = [
        f"№{l.id} · {l.slot.strftime('%d.%m %H:%M')} · {escape(l.service)} · "
        f"{escape(l.name)} · {STATUSES.get(l.status, l.status)}"
        for l in leads
    ]
    return "<b>Последние заявки:</b>\n" + "\n".join(rows)
