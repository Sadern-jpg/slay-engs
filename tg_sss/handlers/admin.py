import asyncio
from aiogram import Router,F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State,StatesGroup
from aiogram.types import Message,CallbackQuery
from aiogram.exceptions import TelegramForbiddenError
from config import settings
from database.db import *
from keyboards.admin import admin_menu,list_kb,item_kb,confirm_broadcast

router=Router()
def is_admin(uid): return uid in settings.ADMIN_IDS
async def no_access(c): await c.answer("Нет доступа",show_alert=True)

class Material(StatesGroup):
    title=State(); description=State(); payload=State()
class Offer(StatesGroup):
    title=State(); description=State(); url=State()
class Broadcast(StatesGroup):
    content=State()

@router.message(Command("admin"))
async def admin_cmd(m:Message):
    if not is_admin(m.from_user.id): await m.answer("Нет доступа"); return
    await m.answer("⚙️ <b>Админ-панель</b>",reply_markup=admin_menu())

@router.callback_query(F.data=="admin")
async def admin(c:CallbackQuery):
    if not is_admin(c.from_user.id): await no_access(c); return
    await c.message.edit_text("⚙️ <b>Админ-панель</b>",reply_markup=admin_menu()); await c.answer()

@router.callback_query(F.data.in_({"add_pdf","add_link"}))
async def material_begin(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): await no_access(c); return
    await state.update_data(kind="pdf" if c.data=="add_pdf" else "link"); await state.set_state(Material.title)
    await c.message.answer("Напиши название материала:"); await c.answer()

@router.message(Material.title)
async def material_title(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    await state.update_data(title=m.text or "Материал"); await state.set_state(Material.description)
    await m.answer("Описание или точка (.) если без описания:")

@router.message(Material.description)
async def material_desc(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    await state.update_data(description="" if (m.text or "").strip()=="." else (m.text or "")); d=await state.get_data(); await state.set_state(Material.payload)
    await m.answer("Отправь PDF документом:" if d["kind"]=="pdf" else "Отправь ссылку https://...")

@router.message(Material.payload)
async def material_payload(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    d=await state.get_data()
    if d["kind"]=="pdf":
        if not m.document or not (m.document.file_name or "").lower().endswith(".pdf"): await m.answer("Пришли PDF-файл документом."); return
        await add_material(d["title"],d["description"],"pdf",file_id=m.document.file_id)
    else:
        url=(m.text or "").strip()
        if not url.startswith(("https://","http://")): await m.answer("Нужна ссылка с https://"); return
        await add_material(d["title"],d["description"],"link",url=url)
    await state.clear(); await m.answer("Материал добавлен ✨",reply_markup=admin_menu())

@router.callback_query(F.data=="add_offer")
async def offer_begin(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): await no_access(c); return
    await state.set_state(Offer.title); await c.message.answer("Название курса:"); await c.answer()
@router.message(Offer.title)
async def offer_title(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    await state.update_data(title=m.text or "Курс"); await state.set_state(Offer.description); await m.answer("Описание курса:")
@router.message(Offer.description)
async def offer_desc(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    await state.update_data(description=m.text or ""); await state.set_state(Offer.url); await m.answer("Ссылка на курс:")
@router.message(Offer.url)
async def offer_url(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    url=(m.text or "").strip()
    if not url.startswith(("https://","http://")): await m.answer("Пришли ссылку с https://"); return
    d=await state.get_data(); await add_offer(d["title"],d["description"],url); await state.clear(); await m.answer("Курс добавлен 💅",reply_markup=admin_menu())

@router.callback_query(F.data=="manage_materials")
async def materials(c:CallbackQuery):
    if not is_admin(c.from_user.id): await no_access(c); return
    xs=await get_all_materials(); await c.message.edit_text("Управление материалами:",reply_markup=list_kb(xs,"mat") if xs else admin_menu()); await c.answer()
@router.callback_query(F.data=="manage_offers")
async def offers(c:CallbackQuery):
    if not is_admin(c.from_user.id): await no_access(c); return
    xs=await get_all_offers(); await c.message.edit_text("Управление курсами:",reply_markup=list_kb(xs,"offer") if xs else admin_menu()); await c.answer()

@router.callback_query(F.data.startswith(("mat_item_","offer_item_")))
async def item_show(c:CallbackQuery):
    if not is_admin(c.from_user.id): await no_access(c); return
    prefix="mat" if c.data.startswith("mat_") else "offer"; iid=int(c.data.rsplit("_",1)[1])
    xs=await (get_all_materials() if prefix=="mat" else get_all_offers()); item=next((x for x in xs if x["id"]==iid),None)
    if not item: await c.answer("Не найдено",show_alert=True); return
    await c.message.edit_text(f"<b>{item['title']}</b>\nСтатус: {'включён' if item['active'] else 'выключен'}",reply_markup=item_kb(prefix,item)); await c.answer()

@router.callback_query(F.data.startswith(("mat_toggle_","offer_toggle_")))
async def item_toggle(c:CallbackQuery):
    if not is_admin(c.from_user.id): await no_access(c); return
    prefix="mat" if c.data.startswith("mat_") else "offer"; iid=int(c.data.rsplit("_",1)[1])
    await (toggle_material(iid) if prefix=="mat" else toggle_offer(iid))
    xs=await (get_all_materials() if prefix=="mat" else get_all_offers()); await c.message.edit_text("Выбери запись:",reply_markup=list_kb(xs,prefix)); await c.answer("Статус изменён")

@router.callback_query(F.data.startswith(("mat_delete_","offer_delete_")))
async def item_delete(c:CallbackQuery):
    if not is_admin(c.from_user.id): await no_access(c); return
    prefix="mat" if c.data.startswith("mat_") else "offer"; iid=int(c.data.rsplit("_",1)[1])
    await (delete_material(iid) if prefix=="mat" else delete_offer(iid))
    xs=await (get_all_materials() if prefix=="mat" else get_all_offers()); await c.message.edit_text("Запись удалена. Выбери следующую:",reply_markup=list_kb(xs,prefix) if xs else admin_menu()); await c.answer()

@router.callback_query(F.data=="stats")
async def stats(c:CallbackQuery):
    if not is_admin(c.from_user.id): await no_access(c); return
    u,m,o=await get_stats(); await c.message.edit_text(f"📊 Статистика\nПользователей: {u}\nМатериалов: {m}\nКурсов: {o}",reply_markup=admin_menu()); await c.answer()

@router.callback_query(F.data=="broadcast")
async def broadcast_begin(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): await no_access(c); return
    await state.set_state(Broadcast.content); await c.message.answer("Пришли одним сообщением текст, фото, видео или документ для рассылки."); await c.answer()
@router.message(Broadcast.content)
async def broadcast_preview(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    if not (m.text or m.photo or m.video or m.document): await m.answer("Поддерживаются текст, фото, видео и документы."); return
    await state.update_data(chat_id=m.chat.id,message_id=m.message_id)
    await m.answer("Проверь сообщение выше. Отправить всем?",reply_markup=confirm_broadcast())
@router.callback_query(F.data=="broadcast_send")
async def broadcast_send(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): await no_access(c); return
    d=await state.get_data()
    if not d.get("message_id"): await c.answer("Сначала подготовь сообщение",show_alert=True); return
    ids=await get_user_ids(); sent=failed=0
    await c.message.edit_text("Рассылка выполняется…")
    for uid in ids:
        try: await c.bot.copy_message(uid,d["chat_id"],d["message_id"]); sent+=1
        except TelegramForbiddenError: failed+=1
        except Exception: failed+=1
        await asyncio.sleep(0.06)
    await state.clear(); await c.message.answer(f"Рассылка завершена. Успешно: {sent}; не доставлено: {failed}.",reply_markup=admin_menu()); await c.answer()
