import json
from urllib.parse import urlparse
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.db import add_item, get_items, toggle_item, delete_item, create_campaign, get_stats
from keyboards.admin import menu

router = Router()

class AdminStates(StatesGroup):
    title = State(); descr = State(); content = State(); url = State()
    campaign_content = State(); campaign_buttons = State(); campaign_interval = State(); campaign_duration = State()

def is_admin(user_id, cfg):
    return user_id in cfg.ADMIN_IDS

def valid_url(value):
    p = urlparse(value)
    return p.scheme in ("http", "https") and bool(p.netloc)

PAGE_SIZE = 8

def item_keyboard(rows, kind, page=0):
    start = page * PAGE_SIZE
    page_rows = rows[start:start + PAGE_SIZE]
    buttons = []
    for row in page_rows:
        buttons.append([
            InlineKeyboardButton(text=("🟢 " if row["active"] else "⚪ ") + row["title"][:35], callback_data=f"itemtoggle:{row['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"itemdelete:{row['id']}"),
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"itempage:{kind}:{page-1}"))
    if start + PAGE_SIZE < len(rows):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"itempage:{kind}:{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="➕ Добавить", callback_data="itemadd")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(F.text == "/cancel")
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=menu())

@router.message(F.text == "/admin")
async def admin_panel(message: Message, state: FSMContext, cfg):
    if is_admin(message.from_user.id, cfg):
        await state.clear(); await message.answer("⚙️ Админ-панель", reply_markup=menu())

@router.message(F.text.in_({"📚 Материалы", "💎 Управление курсами"}))
async def manage_items(message: Message, state: FSMContext, cfg):
    if not is_admin(message.from_user.id, cfg): return
    kind = "material" if message.text == "📚 Материалы" else "course"
    await state.update_data(item_kind=kind)
    rows = await get_items(kind)
    await message.answer("Управление записями. 🟢/⚪ — активность, 🗑 — удалить:", reply_markup=item_keyboard(rows, kind))

@router.callback_query(F.data.startswith("itemtoggle:"))
async def item_toggle(call: CallbackQuery, state: FSMContext, cfg):
    if not is_admin(call.from_user.id, cfg):
        await call.answer("Нет доступа", show_alert=True); return
    await toggle_item(int(call.data.split(":", 1)[1]))
    data = await state.get_data(); kind = data.get("item_kind", "material")
    rows = await get_items(kind)
    try:
        await call.message.edit_reply_markup(reply_markup=item_keyboard(rows, kind))
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc): raise
    await call.answer("Статус изменён")


@router.callback_query(F.data.startswith("itempage:"))
async def item_page(call: CallbackQuery, cfg):
    if not is_admin(call.from_user.id, cfg):
        await call.answer("Нет доступа", show_alert=True)
        return
    try:
        _, kind, page_raw = call.data.split(":", 2)
        page = max(0, int(page_raw))
    except ValueError:
        await call.answer("Некорректная страница", show_alert=True)
        return
    if kind not in ("material", "course"):
        await call.answer("Неизвестный раздел", show_alert=True)
        return
    rows = await get_items(kind)
    await call.message.edit_reply_markup(reply_markup=item_keyboard(rows, kind, page))
    await call.answer()


@router.callback_query(F.data.startswith("itemdelete:"))
async def item_delete(call: CallbackQuery, cfg, state: FSMContext):
    if not is_admin(call.from_user.id, cfg):
        await call.answer("Нет доступа", show_alert=True)
        return
    try:
        item_id = int(call.data.split(":", 1)[1])
    except ValueError:
        await call.answer("Некорректный ID", show_alert=True)
        return
    await delete_item(item_id)
    data = await state.get_data()
    kind = data.get("item_kind", "material")
    rows = await get_items(kind)
    await call.message.edit_reply_markup(reply_markup=item_keyboard(rows, kind))
    await call.answer("Запись удалена")

@router.callback_query(F.data == "itemadd")
async def item_add(call: CallbackQuery, state: FSMContext, cfg):
    if not is_admin(call.from_user.id, cfg):
        await call.answer("Нет доступа", show_alert=True); return
    data = await state.get_data()
    if data.get("item_kind") not in ("material", "course"):
        await call.answer("Сначала открой раздел материалов или курсов", show_alert=True); return
    await state.set_state(AdminStates.title)
    await call.message.answer("Название:"); await call.answer()

@router.message(AdminStates.title)
async def item_title(message: Message, state: FSMContext, cfg):
    if not is_admin(message.from_user.id, cfg): return
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не должно быть пустым. Напиши название:"); return
    await state.update_data(title=title[:150]); await state.set_state(AdminStates.descr)
    await message.answer("Описание (или отправь - чтобы пропустить):")

@router.message(AdminStates.descr)
async def item_descr(message: Message, state: FSMContext, cfg):
    if not is_admin(message.from_user.id, cfg): return
    await state.update_data(descr="" if (message.text or "").strip() == "-" else (message.text or message.caption or ""))
    await state.set_state(AdminStates.content)
    await message.answer("Пришли файл (документ, фото, видео, аудио, голосовое, GIF, стикер) или напиши «ссылка».")

@router.message(AdminStates.content)
async def item_content(message: Message, state: FSMContext, cfg):
    if not is_admin(message.from_user.id, cfg): return
    if (message.text or "").strip().lower() == "ссылка":
        await state.set_state(AdminStates.url); await message.answer("Пришли ссылку https://..."); return
    file_id, file_type = None, None
    for attr, typ in (("document","document"),("photo","photo"),("video","video"),("audio","audio"),("voice","voice"),("animation","animation"),("video_note","video_note"),("sticker","sticker")):
        value = getattr(message, attr, None)
        if value:
            file_id = value[-1].file_id if typ == "photo" else value.file_id
            file_type = typ; break
    if not file_id:
        await message.answer("Не вижу файл. Пришли поддерживаемый файл или напиши «ссылка»."); return
    data = await state.get_data()
    await add_item(data["item_kind"], data["title"], data["descr"], file_id, file_type)
    await state.clear(); await message.answer("Сохранено 🩷", reply_markup=menu())

@router.message(AdminStates.url)
async def item_url(message: Message, state: FSMContext, cfg):
    if not is_admin(message.from_user.id, cfg): return
    url = (message.text or "").strip()
    if not valid_url(url):
        await message.answer("Нужна полная ссылка, начинающаяся с https://"); return
    data = await state.get_data()
    await add_item(data["item_kind"], data["title"], data["descr"], url=url)
    await state.clear(); await message.answer("Ссылка сохранена 🩷", reply_markup=menu())

def parse_links(text):
    links = []
    if not text or text.strip() == "-": return "[]"
    for line in text.splitlines():
        if "|" not in line: continue
        label, url = (x.strip() for x in line.split("|", 1))
        if label and valid_url(url): links.append({"text": label[:60], "url": url})
    return json.dumps(links, ensure_ascii=False)

def extract_campaign(message):
    body = message.text or message.caption or ""
    for attr, typ in (("photo","photo"),("video","video"),("document","document"),("audio","audio"),("animation","animation")):
        value = getattr(message, attr, None)
        if value:
            return typ, value[-1].file_id if typ == "photo" else value.file_id, body
    if body.strip(): return "text", None, body
    return None, None, None

@router.message(F.text.in_({"📣 Рассылка", "📢 Реклама", "🧩 Рекламная вставка"}))
async def start_campaign(message: Message, state: FSMContext, cfg):
    if not is_admin(message.from_user.id, cfg): return
    kind = {"📣 Рассылка":"broadcast", "📢 Реклама":"ad", "🧩 Рекламная вставка":"insert"}[message.text]
    await state.update_data(campaign_kind=kind); await state.set_state(AdminStates.campaign_content)
    await message.answer("Пришли текст, фото, видео или документ для сообщения:")

@router.message(AdminStates.campaign_content)
async def campaign_content(message: Message, state: FSMContext, cfg):
    if not is_admin(message.from_user.id, cfg): return
    ctype, file_id, body = extract_campaign(message)
    if not ctype:
        await message.answer("Пришли текст, фото, видео, документ, аудио или GIF."); return
    await state.update_data(ctype=ctype, file_id=file_id, body=body)
    await state.set_state(AdminStates.campaign_buttons)
    await message.answer("Ссылки-кнопки: по одной на строку в формате Название | https://ссылка. Если не нужны — отправь -")

@router.message(AdminStates.campaign_buttons)
async def campaign_buttons(message: Message, state: FSMContext, cfg):
    if not is_admin(message.from_user.id, cfg): return
    await state.update_data(buttons=parse_links(message.text or "-")); data = await state.get_data(); kind = data["campaign_kind"]
    if kind == "insert":
        await create_campaign("insert", data["ctype"], data["body"], data["file_id"], data["buttons"], 24, None)
        await state.clear(); await message.answer("Рекламная вставка сохранена 🩷", reply_markup=menu()); return
    await state.set_state(AdminStates.campaign_interval)
    await message.answer("Интервал в часах: " + ("1, 6, 12 или 24" if kind == "broadcast" else "1, 3, 6 или 12"))

@router.message(AdminStates.campaign_interval)
async def campaign_interval(message: Message, state: FSMContext, cfg):
    if not is_admin(message.from_user.id, cfg): return
    data = await state.get_data()
    try: interval = int((message.text or "").strip())
    except ValueError: interval = 0
    allowed = (1, 6, 12, 24) if data["campaign_kind"] == "broadcast" else (1, 3, 6, 12)
    if interval not in allowed:
        await message.answer("Допустимые варианты: " + ", ".join(map(str, allowed))); return
    await state.update_data(interval=interval)
    if data["campaign_kind"] == "broadcast":
        await state.set_state(AdminStates.campaign_duration); await message.answer("Срок: 1, 6, 12, 24 часа или «навсегда».")
    else:
        await create_campaign("ad", data["ctype"], data["body"], data["file_id"], data["buttons"], interval, None)
        await state.clear(); await message.answer("Реклама запущена 🩷", reply_markup=menu())

@router.message(AdminStates.campaign_duration)
async def campaign_duration(message: Message, state: FSMContext, cfg):
    if not is_admin(message.from_user.id, cfg): return
    raw = (message.text or "").strip().lower()
    duration = None if raw == "навсегда" else int(raw) if raw.isdigit() and int(raw) in (1, 6, 12, 24) else -1
    if duration == -1:
        await message.answer("Укажи 1, 6, 12, 24 или «навсегда»."); return
    data = await state.get_data()
    await create_campaign("broadcast", data["ctype"], data["body"], data["file_id"], data["buttons"], data["interval"], duration)
    await state.clear(); await message.answer("Рассылка запущена 🩷", reply_markup=menu())

@router.message(F.text == "📊 Статистика")
async def statistics(message: Message, cfg):
    if is_admin(message.from_user.id, cfg):
        users, materials, courses = await get_stats()
        await message.answer(f"Пользователей: {users}\nАктивных материалов: {materials}\nАктивных курсов: {courses}")

@router.message(F.text == "⬅️ В меню бота")
async def back_to_user(message: Message, state: FSMContext):
    from keyboards.user import menu as user_menu
    await state.clear(); await message.answer("Главное меню", reply_markup=user_menu())

