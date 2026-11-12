import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from config import settings
from database import connect, set_value
from keyboards import admin_menu, main_menu, inline

router = Router()

class MaterialFlow(StatesGroup):
    title = State()
    description = State()
    content = State()

class CourseFlow(StatesGroup):
    title = State()
    description = State()
    url = State()

class InsertFlow(StatesGroup):
    content = State()

class CampaignFlow(StatesGroup):
    content = State()
    interval = State()
    duration = State()

class AdFlow(StatesGroup):
    content = State()
    interval = State()


def is_admin(user_id):
    return user_id in settings.admin_ids


def message_has_payload(message: Message):
    return bool(message.text or message.photo or message.video or message.document or
                message.audio or message.animation or message.voice or message.video_note or
                message.sticker)


@router.message(F.text == "⚙️ Админ-панель")
async def admin_home(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Панель управления:", reply_markup=admin_menu())


# MATERIALS
@router.message(F.text == "📦 Управление материалами")
async def material_admin(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Управление материалами:", reply_markup=inline([("➕ Добавить материал", "add"), ("📋 Список материалов", "list")], "matadm"))


@router.callback_query(F.data == "matadm:add")
async def add_material(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await state.set_state(MaterialFlow.title)
    await callback.message.answer("Напиши название материала:")
    await callback.answer()


@router.message(MaterialFlow.title)
async def material_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if not message.text or not message.text.strip():
        await message.answer("Нужно текстовое название. Попробуй ещё раз."); return
    await state.update_data(title=message.text.strip())
    await state.set_state(MaterialFlow.description)
    await message.answer("Напиши описание материала (или отправь точку, если без описания):")


@router.message(MaterialFlow.description)
async def material_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if message.text is None:
        await message.answer("Пришли описание текстом или точку."); return
    await state.update_data(description="" if message.text.strip() == "." else message.html_text)
    await state.set_state(MaterialFlow.content)
    await message.answer("Отправь файл (фото, видео, документ, аудио) или ссылку https://")


@router.message(MaterialFlow.content)
async def material_content(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    file_id = file_type = url = None
    if message.photo:
        file_id, file_type = message.photo[-1].file_id, "photo"
    elif message.video:
        file_id, file_type = message.video.file_id, "video"
    elif message.document:
        file_id, file_type = message.document.file_id, "document"
    elif message.audio:
        file_id, file_type = message.audio.file_id, "audio"
    elif message.text and message.text.strip().startswith("https://"):
        url = message.text.strip()
    else:
        await message.answer("Пришли фото, видео, документ, аудио или ссылку https://"); return
    async with await connect() as db:
        await db.execute("INSERT INTO materials(title,description,file_id,file_type,url) VALUES(?,?,?,?,?)",
                         (data["title"], data["description"], file_id, file_type, url))
        await db.commit()
    await state.clear()
    await message.answer("Материал добавлен 💗", reply_markup=admin_menu())


@router.callback_query(F.data == "matadm:list")
async def list_materials(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    async with await connect() as db:
        cur = await db.execute("SELECT id,title,active FROM materials ORDER BY id DESC")
        rows = await cur.fetchall()
    if not rows:
        await callback.message.answer("Материалов пока нет.")
    for row in rows:
        status = "включён" if row["active"] else "выключен"
        await callback.message.answer(f"{row['id']}. {row['title']} — {status}",
            reply_markup=inline([("Вкл/выкл", f"toggle:{row['id']}"), ("Удалить", f"delete:{row['id']}")], "mat"))
    await callback.answer()


@router.callback_query(F.data.startswith("mat:toggle:"))
async def toggle_material(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    mid = int(callback.data.rsplit(":", 1)[1])
    async with await connect() as db:
        await db.execute("UPDATE materials SET active=1-active WHERE id=?", (mid,)); await db.commit()
    await callback.answer("Статус изменён")


@router.callback_query(F.data.startswith("mat:delete:"))
async def delete_material(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    mid = int(callback.data.rsplit(":", 1)[1])
    async with await connect() as db:
        await db.execute("DELETE FROM materials WHERE id=?", (mid,)); await db.commit()
    await callback.answer("Материал удалён")


# COURSES
@router.message(F.text == "🎓 Управление курсами")
async def course_admin(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Управление курсами:", reply_markup=inline([("➕ Добавить курс", "add"), ("📋 Список курсов", "list")], "courseadm"))


@router.callback_query(F.data == "courseadm:add")
async def add_course(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await state.set_state(CourseFlow.title)
    await callback.message.answer("Название курса:")
    await callback.answer()


@router.message(CourseFlow.title)
async def course_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if not message.text or not message.text.strip():
        await message.answer("Пришли название текстом."); return
    await state.update_data(title=message.text.strip())
    await state.set_state(CourseFlow.description)
    await message.answer("Описание курса (или точка):")


@router.message(CourseFlow.description)
async def course_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if message.text is None:
        await message.answer("Пришли описание текстом или точку."); return
    await state.update_data(description="" if message.text.strip() == "." else message.html_text)
    await state.set_state(CourseFlow.url)
    await message.answer("Пришли ссылку https://")


@router.message(CourseFlow.url)
async def course_url(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if not message.text or not message.text.strip().startswith("https://"):
        await message.answer("Нужна ссылка, начинающаяся с https://"); return
    data = await state.get_data()
    async with await connect() as db:
        await db.execute("INSERT INTO courses(title,description,url) VALUES(?,?,?)", (data["title"], data["description"], message.text.strip()))
        await db.commit()
    await state.clear()
    await message.answer("Курс добавлен 💗", reply_markup=admin_menu())


@router.callback_query(F.data == "courseadm:list")
async def list_courses(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    async with await connect() as db:
        cur = await db.execute("SELECT id,title,active FROM courses ORDER BY id DESC")
        rows = await cur.fetchall()
    if not rows:
        await callback.message.answer("Курсов пока нет.")
    for row in rows:
        await callback.message.answer(f"{row['id']}. {row['title']} — {'включён' if row['active'] else 'выключен'}",
            reply_markup=inline([("Вкл/выкл", f"ctoggle:{row['id']}"), ("Удалить", f"cdelete:{row['id']}")], "course"))
    await callback.answer()


@router.callback_query(F.data.startswith("course:ctoggle:"))
async def toggle_course(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    cid = int(callback.data.rsplit(":", 1)[1])
    async with await connect() as db:
        await db.execute("UPDATE courses SET active=1-active WHERE id=?", (cid,)); await db.commit()
    await callback.answer("Статус изменён")


@router.callback_query(F.data.startswith("course:cdelete:"))
async def delete_course(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    cid = int(callback.data.rsplit(":", 1)[1])
    async with await connect() as db:
        await db.execute("DELETE FROM courses WHERE id=?", (cid,)); await db.commit()
    await callback.answer("Курс удалён")


# INSERT AD AFTER MATERIAL
@router.message(F.text == "🧩 Рекламная вставка")
async def insert_ad_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(InsertFlow.content)
    await message.answer("Отправь текст рекламной вставки. Чтобы отключить её, отправь /disable_insert.")


@router.message(InsertFlow.content, F.text == "/disable_insert")
async def disable_insert(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await set_value("ad_insert", "")
    await state.clear()
    await message.answer("Рекламная вставка отключена.", reply_markup=admin_menu())


@router.message(InsertFlow.content)
async def save_insert(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if not message.text:
        await message.answer("Рекламная вставка пока поддерживает только текст. Пришли текст."); return
    await set_value("ad_insert", message.html_text)
    await state.clear()
    await message.answer("Рекламная вставка сохранена 💗", reply_markup=admin_menu())


# RECURRING BROADCAST
@router.message(F.text == "📨 Рассылка")
async def campaign_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(CampaignFlow.content)
    await message.answer("Отправь сообщение для рассылки (текст, фото, видео, документ, аудио и другие типы сообщений).")


@router.message(CampaignFlow.content)
async def campaign_content(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if not message_has_payload(message):
        await message.answer("Пришли сообщение с содержимым."); return
    await state.update_data(source_chat=message.chat.id, source_message=message.message_id)
    await state.set_state(CampaignFlow.interval)
    await message.answer("Выбери интервал:", reply_markup=inline([("1 час", 60), ("6 часов", 360), ("12 часов", 720), ("24 часа", 1440)], "campint"))


@router.callback_query(F.data.startswith("campint:"))
async def campaign_interval(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    if await state.get_state() != CampaignFlow.interval.state:
        await callback.answer("Этот шаг уже завершён", show_alert=True); return
    await state.update_data(interval=int(callback.data.split(":", 1)[1]))
    await state.set_state(CampaignFlow.duration)
    await callback.message.answer("На какой срок запустить рассылку?", reply_markup=inline([("1 час", 60), ("6 часов", 360), ("12 часов", 720), ("24 часа", 1440), ("Бессрочно", "forever")], "campdur"))
    await callback.answer()


@router.callback_query(F.data.startswith("campdur:"))
async def campaign_duration(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    if await state.get_state() != CampaignFlow.duration.state:
        await callback.answer("Этот шаг уже завершён", show_alert=True); return
    data = await state.get_data()
    duration = callback.data.split(":", 1)[1]
    duration_minutes = None if duration == "forever" else int(duration)
    now = time.time()
    expires = None if duration_minutes is None else now + duration_minutes * 60
    async with await connect() as db:
        await db.execute("INSERT INTO campaigns(kind,chat_id,message_id,interval_minutes,duration_minutes,started_at,next_at,expires_at) VALUES('broadcast',?,?,?,?,?,?,?)",
            (data["source_chat"], data["source_message"], data["interval"], duration_minutes, now, now, expires))
        await db.commit()
    await state.clear()
    await callback.message.answer("Рассылка запущена 💗", reply_markup=admin_menu())
    await callback.answer()


# RECURRING ADS
@router.message(F.text == "📢 Реклама")
async def ad_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdFlow.content)
    await message.answer("Отправь рекламное сообщение (текст, фото, видео, документ и т.д.).")


@router.message(AdFlow.content)
async def ad_content(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if not message_has_payload(message):
        await message.answer("Пришли сообщение с содержимым."); return
    await state.update_data(source_chat=message.chat.id, source_message=message.message_id)
    await state.set_state(AdFlow.interval)
    await message.answer("Выбери интервал показа рекламы:", reply_markup=inline([("1 час", 60), ("3 часа", 180), ("6 часов", 360), ("12 часов", 720)], "adint"))


@router.callback_query(F.data.startswith("adint:"))
async def ad_interval(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    if await state.get_state() != AdFlow.interval.state:
        await callback.answer("Этот шаг уже завершён", show_alert=True); return
    data = await state.get_data()
    now = time.time()
    async with await connect() as db:
        await db.execute("INSERT INTO campaigns(kind,chat_id,message_id,interval_minutes,duration_minutes,started_at,next_at,expires_at) VALUES('ad',?,?,?,?,?,?,NULL)",
            (data["source_chat"], data["source_message"], int(callback.data.split(":", 1)[1]), None, now, now))
        await db.commit()
    await state.clear()
    await callback.message.answer("Реклама запущена 💗", reply_markup=admin_menu())
    await callback.answer()


# CAMPAIGN MANAGEMENT
@router.message(F.text == "🛑 Кампании")
async def campaigns_menu(message: Message):
    if not is_admin(message.from_user.id): return
    async with await connect() as db:
        cur = await db.execute("SELECT id,kind,interval_minutes,expires_at FROM campaigns WHERE active=1 ORDER BY id DESC")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Активных кампаний нет.", reply_markup=admin_menu()); return
    for row in rows:
        kind = "Рассылка" if row["kind"] == "broadcast" else "Реклама"
        interval = row["interval_minutes"]
        expiry = "бессрочно" if row["expires_at"] is None else "по таймеру"
        await message.answer(f"Кампания #{row['id']} · {kind} · каждые {interval // 60} ч. · {expiry}",
            reply_markup=inline([("Остановить", row["id"])], "campstop"))


@router.callback_query(F.data.startswith("campstop:"))
async def stop_campaign(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    campaign_id = int(callback.data.split(":", 1)[1])
    async with await connect() as db:
        await db.execute("UPDATE campaigns SET active=0 WHERE id=?", (campaign_id,)); await db.commit()
    await callback.answer("Кампания остановлена")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
