"""Client-side flow: service -> name -> phone -> time slot -> comment -> confirm."""
from datetime import datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from .. import texts
from ..config import Config
from ..keyboards import ConfirmCb, ServiceCb, confirm_kb, phone_kb, services_kb, skip_kb, status_kb
from ..storage import Lead, LeadStore
from ..validators import normalize_phone, parse_slot, validate_name

router = Router(name="user")


class Form(StatesGroup):
    service = State()
    name = State()
    phone = State()
    slot = State()
    comment = State()
    confirm = State()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, config: Config) -> None:
    await state.clear()
    await state.set_state(Form.service)
    await message.answer(texts.START, reply_markup=services_kb(config.services))


@router.callback_query(Form.service, ServiceCb.filter())
async def pick_service(cb: CallbackQuery, callback_data: ServiceCb, state: FSMContext, config: Config) -> None:
    service = config.services[callback_data.idx]
    await state.update_data(service=service)
    await state.set_state(Form.name)
    await cb.message.edit_text(f"Вы выбрали: <b>{service}</b>")
    await cb.message.answer(texts.ASK_NAME)
    await cb.answer()


@router.message(Form.name, F.text)
async def got_name(message: Message, state: FSMContext) -> None:
    name = validate_name(message.text)
    if not name:
        await message.answer(texts.BAD_NAME)
        return
    await state.update_data(name=name)
    await state.set_state(Form.phone)
    await message.answer(texts.ASK_PHONE, reply_markup=phone_kb())


@router.message(Form.phone, F.contact)
@router.message(Form.phone, F.text)
async def got_phone(message: Message, state: FSMContext, config: Config) -> None:
    raw = message.contact.phone_number if message.contact else message.text
    phone = normalize_phone(raw)
    if not phone:
        await message.answer(texts.BAD_PHONE, reply_markup=phone_kb())
        return
    await state.update_data(phone=phone)
    await state.set_state(Form.slot)
    await message.answer(
        texts.ASK_SLOT.format(start=config.work_start, end=config.work_end),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Form.slot, F.text)
async def got_slot(message: Message, state: FSMContext, config: Config, store: LeadStore) -> None:
    slot = parse_slot(message.text, datetime.now(), config.work_start, config.work_end)
    if not slot:
        await message.answer(texts.BAD_SLOT)
        return
    day = slot.replace(hour=0, minute=0)
    if slot in store.busy_slots(day, day + timedelta(days=1)):
        await message.answer(texts.SLOT_TAKEN)
        return
    await state.update_data(slot=slot.isoformat())
    await state.set_state(Form.comment)
    await message.answer(texts.ASK_COMMENT, reply_markup=skip_kb())


@router.message(Form.comment, F.text)
async def got_comment(message: Message, state: FSMContext) -> None:
    comment = "" if message.text == "Пропустить" else message.text.strip()[:500]
    await state.update_data(comment=comment)
    await state.set_state(Form.confirm)
    lead = _lead_from_state(await state.get_data(), message)
    await message.answer("👌", reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.CONFIRM.format(card=texts.lead_card(lead)), reply_markup=confirm_kb())


@router.callback_query(Form.confirm, ConfirmCb.filter())
async def confirm(
    cb: CallbackQuery, callback_data: ConfirmCb, state: FSMContext,
    store: LeadStore, config: Config, bot: Bot,
) -> None:
    if not callback_data.ok:
        await state.clear()
        await cb.message.edit_text(texts.CANCELLED)
        await cb.answer()
        return
    lead = _lead_from_state(await state.get_data(), cb)
    lead.id = store.add(lead)
    await state.clear()
    await cb.message.edit_text(texts.DONE.format(id=lead.id))
    await cb.answer("Готово!")
    for admin_id in config.admin_ids:
        await bot.send_message(
            admin_id,
            texts.lead_card(lead, for_admin=True),
            reply_markup=status_kb(lead.id, lead.status),
        )


def _lead_from_state(data: dict, event: Message | CallbackQuery) -> Lead:
    user = event.from_user
    return Lead(
        id=None,
        user_id=user.id,
        username=user.username,
        service=data["service"],
        name=data["name"],
        phone=data["phone"],
        slot=datetime.fromisoformat(data["slot"]),
        comment=data.get("comment", ""),
    )
