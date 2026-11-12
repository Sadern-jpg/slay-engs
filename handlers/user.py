from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from database import connect
from config import settings
from keyboards import main_menu, inline, subscribe_keyboard
from services.delivery import deliver_material

router = Router()
GREETING = """Hey, girl! 💋
Welcome to Slay English!
Я собрала для тебя свои полезные материалы, бесплатные подарки и кое-что интересное для тех, кто хочет прокачать свой English ещё сильнее
выбирай, с чего начнём 👇🏻"""

async def save_user(user):
    async with await connect() as db:
        await db.execute("INSERT INTO users(user_id,username,first_name) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name",
                         (user.id, user.username, user.first_name))
        await db.commit()

async def subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(settings.channel_id, user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return False

@router.message(CommandStart())
async def start(message: Message):
    await save_user(message.from_user)
    await message.answer(GREETING, reply_markup=main_menu(message.from_user.id in settings.admin_ids))

@router.message(F.text == "⬅️ В меню")
async def back_menu(message: Message):
    await message.answer("Главное меню 👇", reply_markup=main_menu(message.from_user.id in settings.admin_ids))

@router.message(F.text == "🎁 Материалы")
async def materials(message: Message):
    async with await connect() as db:
        cur = await db.execute("SELECT id,title FROM materials WHERE active=1 ORDER BY id DESC")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Пока материалов нет. Загляни чуть позже 💗")
        return
    await message.answer("Выбери материал:", reply_markup=inline([(r["title"], r["id"]) for r in rows], "material"))

@router.callback_query(F.data.startswith("material:"))
async def choose_material(callback: CallbackQuery, bot):
    material_id = int(callback.data.split(":")[1])
    if not await subscribed(bot, callback.from_user.id):
        async with await connect() as db:
            await db.execute("INSERT INTO users_pending(user_id,material_id) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET material_id=excluded.material_id",
                             (callback.from_user.id, material_id))
            await db.commit()
        await callback.message.answer("Чтобы получить материал, подпишись на наш канал:", reply_markup=subscribe_keyboard(settings.channel_url))
        await callback.answer()
        return
    await deliver_material(bot, callback.from_user.id, material_id)
    await callback.answer()

@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery, bot):
    if not await subscribed(bot, callback.from_user.id):
        await callback.answer("Пока не вижу подписку. Подпишись и попробуй ещё раз 💗", show_alert=True)
        return
    async with await connect() as db:
        cur = await db.execute("SELECT material_id FROM users_pending WHERE user_id=?", (callback.from_user.id,))
        row = await cur.fetchone()
        await db.execute("DELETE FROM users_pending WHERE user_id=?", (callback.from_user.id,))
        await db.commit()
    await callback.answer("Подписка подтверждена!")
    if row:
        await deliver_material(bot, callback.from_user.id, row["material_id"])

@router.message(F.text == "📚 Курсы")
async def courses(message: Message):
    async with await connect() as db:
        cur = await db.execute("SELECT title,description,url FROM courses WHERE active=1 ORDER BY id DESC")
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Скоро здесь появятся курсы 💗")
        return
    for row in rows:
        text = f"<b>{row['title']}</b>\n{row['description']}\n<a href=\"{row['url']}\">Подробнее</a>"
        await message.answer(text)
