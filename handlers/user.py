
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import CHANNEL_ID, CHANNEL_URL
from database.db import add_user, items, item
from keyboards.user import menu, choices, subscribe
from services.campaigns import insert_ad

router = Router()


class U(StatesGroup):
    waiting = State()


WELCOME = (
    "Hey, girl! 💋\n"
    "Welcome to Slay English!\n"
    "Я собрала для тебя свои полезные материалы, бесплатные подарки и кое-что интересное для тех, кто хочет прокачать свой English ещё сильнее\n"
    "выбирай, с чего начнём 👇🏻"
)


async def is_sub(bot, uid):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, uid)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


async def deliver_item(message, it, kind, bot):
    if it["descr"]:
        await message.answer(
            f"<b>{it['title']}</b>\n{it['descr']}",
            parse_mode="HTML"
        )

    if it["file_id"]:
        typ = it["file_type"]
        fid = it["file_id"]

        methods = {
            "photo": message.answer_photo,
            "video": message.answer_video,
            "audio": message.answer_audio,
            "voice": message.answer_voice,
            "animation": message.answer_animation,
            "video_note": message.answer_video_note
        }

        if typ in methods:
            await methods[typ](
                fid,
                caption=it["title"] if typ not in ("voice", "video_note") else None
            )
        else:
            await message.answer_document(fid, caption=it["title"])

    elif it["url"]:
        await message.answer(
            it["title"],
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="Открыть", url=it["url"])
                ]]
            )
        )

    if kind == "material":
        await insert_ad(bot, message.chat.id)


@router.message(F.text == "/start")
async def start(m: Message, state: FSMContext):
    from config import ADMIN_IDS
    from keyboards.admin import menu as admin_menu

    await state.clear()
    await add_user(m.from_user)

    if m.from_user.id in ADMIN_IDS:
        await m.answer(WELCOME, reply_markup=admin_menu())
    else:
        await m.answer(WELCOME, reply_markup=menu())


@router.message(F.text == "✨ Забрать бесплатные материалы")
async def mats(m):
    await m.answer(
        "Выбирай материал 🩷",
        reply_markup=choices("material", await items("material"))
    )


@router.message(F.text == "💅 Буст твоего английского")
async def courses(m):
    await m.answer(
        "Выбирай курс 💅",
        reply_markup=choices("course", await items("course"))
    )


@router.callback_query(F.data.startswith("item:"))
async def get(call: CallbackQuery, bot, state: FSMContext):
    _, kind, i = call.data.split(":")
    it = await item(int(i))

    if not it:
        await call.answer("Уже недоступно", show_alert=True)
        return

    if kind == "material" and not await is_sub(bot, call.from_user.id):
        await state.set_state(U.waiting)
        await state.update_data(pending_item=int(i), pending_kind=kind)

        await call.message.answer(
            "Подпишись на канал, чтобы получить выбранный материал 🩷",
            reply_markup=subscribe(CHANNEL_URL)
        )
        await call.answer()
        return

    await deliver_item(call.message, it, kind, bot)
    await call.answer("Готово 🩷")


@router.callback_query(F.data == "subcheck")
async def subcheck(c: CallbackQuery, bot, state: FSMContext):
    if await is_sub(bot, c.from_user.id):
        data = await state.get_data()
        it = await item(data.get("pending_item", 0))

        await c.answer("Подписка подтверждена 🩷")

        if it:
            await deliver_item(
                c.message,
                it,
                data.get("pending_kind", "material"),
                bot
            )
        else:
            await c.message.answer(
                "Подписка подтверждена! Теперь выбери материал 🩷",
                reply_markup=menu()
            )

        await state.clear()
    else:
        await c.answer("Подписку пока не вижу", show_alert=True)
