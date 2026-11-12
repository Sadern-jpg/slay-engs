from aiogram import Router,F
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from aiogram.filters import CommandStart
from database import connect
from config import settings
from keyboards import main_menu,inline,subscribe_keyboard
from services.delivery import deliver_material

router=Router()
GREETING="""Hey, girl! 💋
Welcome to Slay English!
Я собрала для тебя свои полезные материалы, бесплатные подарки и кое-что интересное для тех, кто хочет прокачать свой English ещё сильнее
выбирай, с чего начнём 👇🏻"""

async def save_user(user):
    async with await connect() as db:
        await db.execute("INSERT INTO users(user_id,username,first_name) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name",(user.id,user.username,user.first_name))
        await db.commit()

async def subscribed(bot,uid):
    try:
        m=await bot.get_chat_member(settings.channel_id,uid)
        return m.status in ("creator","administrator","member") or (m.status=="restricted" and bool(m.is_member))
    except Exception:
        return False

@router.message(CommandStart())
async def start(message:Message):
    await save_user(message.from_user)
    await message.answer(GREETING,reply_markup=main_menu(message.from_user.id in settings.admin_ids))

@router.message(F.text=="⬅️ В меню")
async def back(message:Message):
    await message.answer("Главное меню 👇",reply_markup=main_menu(message.from_user.id in settings.admin_ids))

@router.message(F.text=="🎁 Материалы")
async def materials(message:Message):
    await save_user(message.from_user)
    async with await connect() as db:
        cur=await db.execute("SELECT id,title FROM materials WHERE active=1 ORDER BY id DESC")
        rows=await cur.fetchall()
    if rows: await message.answer("Выбери материал:",reply_markup=inline([(r["title"],r["id"]) for r in rows],"material"))
    else: await message.answer("Пока материалов нет. Загляни чуть позже 💗")

@router.callback_query(F.data.startswith("material:"))
async def choose(callback:CallbackQuery,bot):
    await save_user(callback.from_user)
    try: mid=int(callback.data.split(":",1)[1])
    except ValueError:
        await callback.answer("Материал не найден",show_alert=True); return
    if not await subscribed(bot,callback.from_user.id):
        async with await connect() as db:
            await db.execute("INSERT INTO users_pending(user_id,material_id) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET material_id=excluded.material_id",(callback.from_user.id,mid)); await db.commit()
        await callback.message.answer("Чтобы получить материал, подпишись на наш канал:",reply_markup=subscribe_keyboard(settings.channel_url))
        await callback.answer(); return
    await deliver_material(bot,callback.from_user.id,mid)
    await callback.answer()

@router.callback_query(F.data=="check_sub")
async def check_sub(callback:CallbackQuery,bot):
    if not await subscribed(bot,callback.from_user.id):
        await callback.answer("Пока не вижу подписку. Подпишись и попробуй ещё раз 💗",show_alert=True); return
    async with await connect() as db:
        cur=await db.execute("SELECT material_id FROM users_pending WHERE user_id=?",(callback.from_user.id,))
        row=await cur.fetchone()
        await db.execute("DELETE FROM users_pending WHERE user_id=?",(callback.from_user.id,)); await db.commit()
    await callback.answer("Подписка подтверждена!")
    if row: await deliver_material(bot,callback.from_user.id,row["material_id"])

@router.message(F.text=="📚 Курсы")
async def courses(message:Message):
    await save_user(message.from_user)
    async with await connect() as db:
        cur=await db.execute("SELECT title,description,url FROM courses WHERE active=1 ORDER BY id DESC")
        rows=await cur.fetchall()
    if not rows: await message.answer("Скоро здесь появятся курсы 💗"); return
    for r in rows:
        await message.answer(f"<b>{r['title']}</b>\n{r['description']}",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Подробнее",url=r["url"])]]))
