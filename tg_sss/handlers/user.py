from aiogram import Router,F
from aiogram.filters import CommandStart
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from config import settings
from database.db import add_user,get_materials,get_material,get_offers,schedule_reminder,acknowledge_reminder
from keyboards.user import main_menu,back_home,subscribe_keyboard,material_keyboard,offer_keyboard

router=Router()
WELCOME="<b>Hey, girl! 💋\nWelcome to Slay English!</b>\n\nЯ собрала для тебя свои полезные материалы, бесплатные подарки и кое-что интересное для тех, кто хочет прокачать свой English ещё сильнее\n\n<b>выбирай, с чего начнём 👇🏻</b>"

async def subscribed(bot,uid):
    try:
        m=await bot.get_chat_member(settings.CHANNEL_ID,uid)
        return m.status in ("member","administrator","creator")
    except Exception: return False

async def home_show(target):
    admin=target.from_user.id in settings.ADMIN_IDS
    if isinstance(target,CallbackQuery):
        try: await target.message.edit_text(WELCOME,reply_markup=main_menu(admin))
        except TelegramBadRequest: await target.message.answer(WELCOME,reply_markup=main_menu(admin))
        await target.answer()
    else: await target.answer(WELCOME,reply_markup=main_menu(admin))

@router.message(CommandStart())
async def start(m:Message):
    await add_user(m.from_user); await home_show(m)

@router.callback_query(F.data=="home")
async def home(c:CallbackQuery): await home_show(c)

@router.callback_query(F.data=="materials")
async def materials(c:CallbackQuery):
    items=await get_materials()
    await c.message.edit_text("✨ <b>Забирай свои бесплатные материалы!</b>\n\nВыбери материал. Подписку проверю перед каждой выдачей 💗" if items else "Пока бесплатных материалов нет 🩷",reply_markup=material_keyboard(items) if items else back_home())
    await c.answer()

@router.callback_query(F.data.startswith("getmat_"))
async def getmat(c:CallbackQuery):
    item=await get_material(int(c.data.split("_",1)[1]))
    if not item: await c.answer("Материал недоступен",show_alert=True); return
    if not await subscribed(c.bot,c.from_user.id):
        await c.message.edit_text("Чтобы получить этот материал, подпишись на канал и нажми проверку 💗",reply_markup=subscribe_keyboard(settings.CHANNEL_URL)); await c.answer(); return
    if item["material_type"]=="link":
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть материал ✨",url=item["url"])],[InlineKeyboardButton(text="⬅️ К материалам",callback_data="materials")]])
        await c.message.edit_text(f"<b>{item['title']}</b>\n\n{item['description'] or ''}",reply_markup=kb)
    else:
        await c.bot.send_document(c.from_user.id,item["file_id"],caption=f"<b>{item['title']}</b>\n{item['description'] or ''}")
        await c.message.edit_text("Материал отправлен тебе в чат 💗",reply_markup=back_home())
    await schedule_reminder(c.from_user.id); await c.answer("Лови свой подарок! 💋")

@router.callback_query(F.data=="check_sub")
async def check(c:CallbackQuery):
    if await subscribed(c.bot,c.from_user.id):
        items=await get_materials()
        await c.message.edit_text("Подписка найдена! Теперь выбери материал ✨",reply_markup=material_keyboard(items) if items else back_home())
    else: await c.message.edit_text("Пока не вижу подписку 😔",reply_markup=subscribe_keyboard(settings.CHANNEL_URL))
    await c.answer()

@router.callback_query(F.data=="offers")
async def offers(c:CallbackQuery):
    items=await get_offers()
    await c.message.edit_text("💅 <b>Буст твоего английского</b>\n\nВыбирай программу:" if items else "💅 <b>Буст твоего английского</b>\n\nСкоро здесь появятся программы 🩷",reply_markup=offer_keyboard(items) if items else back_home())
    await c.answer()

@router.callback_query(F.data=="reminder_ack")
async def ack(c:CallbackQuery):
    await acknowledge_reminder(c.from_user.id)
    await c.answer("Хорошо, больше не буду напоминать 🩷",show_alert=True)
    try: await c.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest: pass
