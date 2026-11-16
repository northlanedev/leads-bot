from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .storage import STATUSES


class ServiceCb(CallbackData, prefix="svc"):
    idx: int


class ConfirmCb(CallbackData, prefix="cf"):
    ok: bool


class StatusCb(CallbackData, prefix="st"):
    lead_id: int
    status: str


def services_kb(services: tuple[str, ...]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, name in enumerate(services):
        kb.button(text=name, callback_data=ServiceCb(idx=i))
    kb.adjust(2)
    return kb.as_markup()


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def skip_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустить")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Отправить", callback_data=ConfirmCb(ok=True))
    kb.button(text="✖️ Отменить", callback_data=ConfirmCb(ok=False))
    return kb.as_markup()


def status_kb(lead_id: int, current: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, title in STATUSES.items():
        if code != current:
            kb.button(text=title, callback_data=StatusCb(lead_id=lead_id, status=code))
    kb.adjust(3)
    return kb.as_markup()
