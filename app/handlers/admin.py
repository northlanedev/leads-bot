"""Admin commands: /leads, /new, /export and status buttons under each lead."""
from datetime import datetime

from aiogram import Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from .. import texts
from ..config import Config
from ..keyboards import StatusCb, status_kb
from ..storage import STATUSES, LeadStore

router = Router(name="admin")


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, config: Config) -> bool:
        return event.from_user is not None and event.from_user.id in config.admin_ids


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("leads"))
async def last_leads(message: Message, store: LeadStore) -> None:
    await message.answer(texts.leads_list(store.latest(15)))


@router.message(Command("new"))
async def new_leads(message: Message, store: LeadStore) -> None:
    await message.answer(texts.leads_list(store.latest(15, status="new")))


@router.message(Command("export"))
async def export(message: Message, store: LeadStore) -> None:
    name = f"leads_{datetime.now():%Y-%m-%d}.csv"
    await message.answer_document(BufferedInputFile(store.export_csv(), filename=name), caption="Все заявки")


@router.callback_query(StatusCb.filter())
async def change_status(cb: CallbackQuery, callback_data: StatusCb, store: LeadStore) -> None:
    if not store.set_status(callback_data.lead_id, callback_data.status):
        await cb.answer("Заявка не найдена", show_alert=True)
        return
    lead = store.get(callback_data.lead_id)
    await cb.message.edit_text(
        texts.lead_card(lead, for_admin=True),
        reply_markup=status_kb(lead.id, lead.status),
    )
    await cb.answer(f"Статус: {STATUSES[lead.status]}")
