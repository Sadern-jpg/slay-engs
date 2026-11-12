
import json

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import ADMIN_IDS
from database.db import (
    add_item, items, toggle, delete_item,
    create_campaign, stats
)
from keyboards.admin import menu as admin_menu
from keyboards.user import menu as user_menu

router = Router()


class A(StatesGroup):
    title = State()
    descr = State()
    content = State()
    url = State()
    camp = State()
    buttons = State()
    interval = State()
    duration = State()


def admin(uid, c):
    return uid in c.ADMIN_IDS


def main_menu(uid):
    return user_menu(is_admin=uid in ADMIN_IDS)


def item_kb(rows):
    buttons = []

    for r in rows:
        buttons.append([
            InlineKeyboardButton(
                text=("🟢 " if r["active"] else "⚪ ") + r["title"],
                callback_data=f"toggle:{r['id']}"
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"delete:{r['id']}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="➕ Добавить",
            callback_data="newitem"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(F.text == "/admin")
async def panel(m: Message, state: FSMContext, c):
    if admin(m.from_user.id, c):
        await state.clear()
        await m.answer(
            "⚙️ Админ-панель",
            reply_markup=admin_menu()
        )


@router.message(F.text.in_({"📚 Материалы", "💎 Управление курсами"}))
async def manage(m: Message, state: FSMContext, c):
    if not admin(m.from_user.id, c):
        return

    kind = "material" if m.text == "📚 Материалы" else "course"
    await state.update_data(kind=kind)

    await m.answer(
        "Нажми на название, чтобы включить/выключить. 🗑 — удалить.",
        reply_markup=item_kb(await items(kind))
    )


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_cb(call: CallbackQuery, c):
    if not admin(call.from_user.id, c):
        return await call.answer("Нет доступа", show_alert=True)

    await toggle(int(call.data.split(":")[1]))
    await call.answer("Статус изменён")
    await call.message.answer(
        "Обнови список через кнопку раздела в админ-меню."
    )


@router.callback_query(F.data.startswith("delete:"))
async def delete_cb(call: CallbackQuery, c):
    if not admin(call.from_user.id, c):
        return await call.answer("Нет доступа", show_alert=True)

    await delete_item(int(call.data.split(":")[1]))
    await call.answer("Удалено")
    await call.message.edit_text(
        "Запись удалена. Открой раздел заново, чтобы обновить список."
    )


@router.callback_query(F.data == "newitem")
async def newitem(c: CallbackQuery, state: FSMContext):
    await state.set_state(A.title)
    await c.message.answer("Название материала/курса:")
    await c.answer()


@router.message(A.title)
async def title(m: Message, state: FSMContext):
    await state.update_data(title=m.text or "Без названия")
    await state.set_state(A.descr)
    await m.answer("Описание (или - чтобы пропустить):")


@router.message(A.descr)
async def descr(m: Message, state: FSMContext):
    await state.update_data(
        descr="" if m.text == "-" else (m.text or "")
    )
    await state.set_state(A.content)
    await m.answer(
        "Пришли файл (фото, видео, документ, аудио, голосовое, GIF) "
        "или напиши «ссылка»."
    )


@router.message(A.content)
async def content(m: Message, state: FSMContext):
    if m.text and m.text.lower() == "ссылка":
        await state.set_state(A.url)
        return await m.answer(
            "Пришли полный URL, начинающийся с https://"
        )

    fields = [
        ("document", m.document),
        ("photo", m.photo[-1] if m.photo else None),
        ("video", m.video),
        ("audio", m.audio),
        ("voice", m.voice),
        ("animation", m.animation),
        ("video_note", m.video_note)
    ]

    found = next(
        ((t, obj.file_id) for t, obj in fields if obj),
        None
    )

    if not found:
        return await m.answer(
            "Не вижу файл. Пришли файл или напиши «ссылка»."
        )

    d = await state.get_data()

    await add_item(
        d["kind"], d["title"], d["descr"],
        found[1], found[0], None
    )

    await state.clear()
    await m.answer(
        "Сохранено 🩷",
        reply_markup=main_menu(m.from_user.id)
    )


@router.message(A.url)
async def url(m: Message, state: FSMContext):
    link = (m.text or "").strip()

    if not link.startswith(("https://", "http://")):
        return await m.answer(
            "Ссылка должна начинаться с https:// или http://"
        )

    d = await state.get_data()

    await add_item(
        d["kind"], d["title"], d["descr"],
        None, None, link
    )

    await state.clear()
    await m.answer(
        "Ссылка сохранена 🩷",
        reply_markup=main_menu(m.from_user.id)
    )


def parse_buttons(s):
    out = []

    for line in (s or "").splitlines():
        if "|" in line:
            a, b = line.split("|", 1)
            a = a.strip()
            b = b.strip()

            if a and b.startswith(("https://", "http://")):
                out.append({"text": a, "url": b})

    return json.dumps(out, ensure_ascii=False)


@router.message(F.text.in_({
    "📣 Рассылка",
    "📢 Реклама",
    "🩷 Рекламная вставка"
}))
async def campaign_start(m: Message, state: FSMContext, c):
    if not admin(m.from_user.id, c):
        return

    kind = {
        "📣 Рассылка": "broadcast",
        "📢 Реклама": "ad",
        "🩷 Рекламная вставка": "insert"
    }[m.text]

    await state.update_data(kind=kind)
    await state.set_state(A.camp)

    await m.answer(
        "Отправь текст, фото, видео или документ для публикации:"
    )


@router.message(A.camp)
async def campaign_content(m: Message, state: FSMContext):
    typ = "text"
    fid = None
    body = m.text or m.caption or ""

    if m.photo:
        typ = "photo"
        fid = m.photo[-1].file_id
    elif m.video:
        typ = "video"
        fid = m.video.file_id
    elif m.document:
        typ = "document"
        fid = m.document.file_id
    elif m.animation:
        typ = "animation"
        fid = m.animation.file_id
    elif m.audio:
        typ = "audio"
        fid = m.audio.file_id
    elif m.voice:
        typ = "voice"
        fid = m.voice.file_id

    await state.update_data(ctype=typ, fid=fid, body=body)
    await state.set_state(A.buttons)

    await m.answer(
        "Кнопки-ссылки: Название | https://ссылка "
        "(каждая с новой строки). Или отправь -"
    )


@router.message(A.buttons)
async def buttons(m: Message, state: FSMContext):
    await state.update_data(
        buttons=parse_buttons("" if m.text == "-" else m.text)
    )
    await state.set_state(A.interval)

    d = await state.get_data()

    if d["kind"] == "insert":
        return await finish(m, state, None, 1)

    await m.answer(
        "Интервал в часах: " +
        ("1, 6, 12 или 24" if d["kind"] == "broadcast"
         else "1, 3, 6 или 12")
    )


@router.message(A.interval)
async def interval(m: Message, state: FSMContext):
    d = await state.get_data()

    try:
        v = int(m.text)
    except (ValueError, TypeError):
        v = 0

    allowed = (
        [1, 6, 12, 24]
        if d["kind"] == "broadcast"
        else [1, 3, 6, 12]
    )

    if v not in allowed:
        return await m.answer(
            "Выбери: " + ", ".join(map(str, allowed))
        )

    await state.update_data(interval=v)

    if d["kind"] == "broadcast":
        await state.set_state(A.duration)
        await m.answer(
            "Срок действия: 1, 6, 12, 24 часа или навсегда."
        )
    else:
        await finish(m, state, None, v)


@router.message(A.duration)
async def duration(m: Message, state: FSMContext):
    s = (m.text or "").strip().lower()

    v = (
        None if s == "навсегда"
        else int(s) if s.isdigit() and int(s) in [1, 6, 12, 24]
        else -1
    )

    if v == -1:
        return await m.answer(
            "Укажи 1, 6, 12, 24 или навсегда."
        )

    await finish(m, state, v)


async def finish(m, state, duration, interval=None):
    d = await state.get_data()

    await create_campaign(
        d["kind"], d["ctype"], d["body"], d["fid"],
        d["buttons"],
        interval or d.get("interval", 1),
        duration
    )

    await state.clear()
    await m.answer(
        "Настройка сохранена 🩷",
        reply_markup=main_menu(m.from_user.id)
    )


@router.message(F.text == "📊 Статистика")
async def stat(m: Message, c):
    if admin(m.from_user.id, c):
        a, b, d = await stats()
        await m.answer(
            f"Пользователей: {a}\nМатериалов: {b}\nКурсов: {d}"
        )


@router.message(F.text == "⬅️ В меню бота")
async def back(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "Главное меню",
        reply_markup=main_menu(m.from_user.id)
    )
