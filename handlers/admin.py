
import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from config import settings
from database.db import *
from keyboards.admin import (
    admin_menu,
    list_kb,
    item_kb,
    confirm_broadcast,
)

router = Router()


def is_admin(uid):
    return uid in settings.ADMIN_IDS


async def no_access(c):
    await c.answer("Нет доступа", show_alert=True)


# Безопасное редактирование сообщений.
# Если текст и кнопки не изменились, Telegram не будет выдавать ошибку.
async def safe_edit_text(message, text, reply_markup=None):
    try:
        await message.edit_text(
            text,
            reply_markup=reply_markup
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise


class Material(StatesGroup):
    title = State()
    description = State()
    payload = State()


class Offer(StatesGroup):
    title = State()
    description = State()
    url = State()


class Broadcast(StatesGroup):
    content = State()


# =========================
# АДМИН-ПАНЕЛЬ
# =========================

@router.message(Command("admin"))
async def admin_cmd(m: Message):
    if not is_admin(m.from_user.id):
        await m.answer("Нет доступа")
        return

    await m.answer(
        "⚙️ <b>Админ-панель</b>",
        reply_markup=admin_menu()
    )


@router.callback_query(F.data == "admin")
async def admin(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    await safe_edit_text(
        c.message,
        "⚙️ <b>Админ-панель</b>",
        reply_markup=admin_menu()
    )
    await c.answer()


# =========================
# ДОБАВЛЕНИЕ МАТЕРИАЛОВ
# =========================

@router.callback_query(F.data.in_({"add_pdf", "add_link"}))
async def material_begin(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    await state.update_data(
        kind="pdf" if c.data == "add_pdf" else "link"
    )
    await state.set_state(Material.title)

    await c.message.answer("Напиши название материала:")
    await c.answer()


@router.message(Material.title)
async def material_title(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.update_data(title=m.text or "Материал")
    await state.set_state(Material.description)

    await m.answer(
        "Описание или точка (.) если без описания:"
    )


@router.message(Material.description)
async def material_desc(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    description = (
        ""
        if (m.text or "").strip() == "."
        else (m.text or "")
    )

    await state.update_data(description=description)

    d = await state.get_data()
    await state.set_state(Material.payload)

    if d["kind"] == "pdf":
        await m.answer("Отправь PDF документом:")
    else:
        await m.answer("Отправь ссылку https://...")


@router.message(Material.payload)
async def material_payload(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    d = await state.get_data()

    if d["kind"] == "pdf":
        if (
            not m.document
            or not (m.document.file_name or "").lower().endswith(".pdf")
        ):
            await m.answer("Пришли PDF-файл документом.")
            return

        await add_material(
            d["title"],
            d["description"],
            "pdf",
            file_id=m.document.file_id
        )

    else:
        url = (m.text or "").strip()

        if not url.startswith(("https://", "http://")):
            await m.answer("Нужна ссылка с https://")
            return

        await add_material(
            d["title"],
            d["description"],
            "link",
            url=url
        )

    await state.clear()

    await m.answer(
        "Материал добавлен ✨",
        reply_markup=admin_menu()
    )


# =========================
# ДОБАВЛЕНИЕ КУРСОВ
# =========================

@router.callback_query(F.data == "add_offer")
async def offer_begin(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    await state.set_state(Offer.title)
    await c.message.answer("Название курса:")
    await c.answer()


@router.message(Offer.title)
async def offer_title(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.update_data(title=m.text or "Курс")
    await state.set_state(Offer.description)

    await m.answer("Описание курса:")


@router.message(Offer.description)
async def offer_desc(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.update_data(description=m.text or "")
    await state.set_state(Offer.url)

    await m.answer("Ссылка на курс:")


@router.message(Offer.url)
async def offer_url(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    url = (m.text or "").strip()

    if not url.startswith(("https://", "http://")):
        await m.answer("Пришли ссылку с https://")
        return

    d = await state.get_data()

    await add_offer(
        d["title"],
        d["description"],
        url
    )

    await state.clear()

    await m.answer(
        "Курс добавлен 💅",
        reply_markup=admin_menu()
    )


# =========================
# УПРАВЛЕНИЕ МАТЕРИАЛАМИ
# =========================

@router.callback_query(F.data == "manage_materials")
async def materials(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    xs = await get_all_materials()

    await safe_edit_text(
        c.message,
        "Управление материалами:",
        reply_markup=list_kb(xs, "mat") if xs else admin_menu()
    )

    await c.answer()


# =========================
# УПРАВЛЕНИЕ КУРСАМИ
# =========================

@router.callback_query(F.data == "manage_offers")
async def offers(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    xs = await get_all_offers()

    await safe_edit_text(
        c.message,
        "Управление курсами:",
        reply_markup=list_kb(xs, "offer") if xs else admin_menu()
    )

    await c.answer()


# =========================
# ПРОСМОТР ЗАПИСИ
# =========================

@router.callback_query(
    F.data.startswith(("mat_item_", "offer_item_"))
)
async def item_show(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    prefix = "mat" if c.data.startswith("mat_") else "offer"
    iid = int(c.data.rsplit("_", 1)[1])

    xs = await (
        get_all_materials()
        if prefix == "mat"
        else get_all_offers()
    )

    item = next(
        (x for x in xs if x["id"] == iid),
        None
    )

    if not item:
        await c.answer("Не найдено", show_alert=True)
        return

    status = "включён" if item["active"] else "выключен"

    await safe_edit_text(
        c.message,
        f"<b>{item['title']}</b>\nСтатус: {status}",
        reply_markup=item_kb(prefix, item)
    )

    await c.answer()


# =========================
# ВКЛЮЧЕНИЕ И ВЫКЛЮЧЕНИЕ
# =========================

@router.callback_query(
    F.data.startswith(("mat_toggle_", "offer_toggle_"))
)
async def item_toggle(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    prefix = "mat" if c.data.startswith("mat_") else "offer"
    iid = int(c.data.rsplit("_", 1)[1])

    if prefix == "mat":
        await toggle_material(iid)
        xs = await get_all_materials()
    else:
        await toggle_offer(iid)
        xs = await get_all_offers()

    await safe_edit_text(
        c.message,
        "Выбери запись:",
        reply_markup=list_kb(xs, prefix)
    )

    await c.answer("Статус изменён")


# =========================
# УДАЛЕНИЕ
# =========================

@router.callback_query(
    F.data.startswith(("mat_delete_", "offer_delete_"))
)
async def item_delete(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    prefix = "mat" if c.data.startswith("mat_") else "offer"
    iid = int(c.data.rsplit("_", 1)[1])

    if prefix == "mat":
        await delete_material(iid)
        xs = await get_all_materials()
    else:
        await delete_offer(iid)
        xs = await get_all_offers()

    await safe_edit_text(
        c.message,
        "Запись удалена. Выбери следующую:",
        reply_markup=list_kb(xs, prefix) if xs else admin_menu()
    )

    await c.answer()


# =========================
# СТАТИСТИКА
# =========================

@router.callback_query(F.data == "stats")
async def stats(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    u, m, o = await get_stats()

    await safe_edit_text(
        c.message,
        f"📊 Статистика\n"
        f"Пользователей: {u}\n"
        f"Материалов: {m}\n"
        f"Курсов: {o}",
        reply_markup=admin_menu()
    )

    await c.answer()


# =========================
# РАССЫЛКА
# =========================

@router.callback_query(F.data == "broadcast")
async def broadcast_begin(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    await state.set_state(Broadcast.content)

    await c.message.answer(
        "Пришли одним сообщением текст, фото, видео или документ для рассылки."
    )

    await c.answer()


@router.message(Broadcast.content)
async def broadcast_preview(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    if not (m.text or m.photo or m.video or m.document):
        await m.answer(
            "Поддерживаются текст, фото, видео и документы."
        )
        return

    await state.update_data(
        chat_id=m.chat.id,
        message_id=m.message_id
    )

    await m.answer(
        "Проверь сообщение выше. Отправить всем?",
        reply_markup=confirm_broadcast()
    )


@router.callback_query(F.data == "broadcast_send")
async def broadcast_send(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await no_access(c)
        return

    d = await state.get_data()

    if not d.get("message_id"):
        await c.answer(
            "Сначала подготовь сообщение",
            show_alert=True
        )
        return

    ids = await get_user_ids()
    sent = 0
    failed = 0

    await safe_edit_text(
        c.message,
        "Рассылка выполняется…"
    )

    for uid in ids:
        try:
            await c.bot.copy_message(
                uid,
                d["chat_id"],
                d["message_id"]
            )
            sent += 1

        except TelegramForbiddenError:
            failed += 1

        except Exception:
            failed += 1

        await asyncio.sleep(0.06)

    await state.clear()

    await c.message.answer(
        f"Рассылка завершена.\n"
        f"Успешно: {sent}; не доставлено: {failed}.",
        reply_markup=admin_menu()
    )

    await c.answer()
