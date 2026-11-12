import logging
from html import escape
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from config import CHANNEL_ID, CHANNEL_URL
from database.db import add_user, get_items, get_item
from keyboards.user import menu, item_choices, subscription_keyboard
from services.campaigns import send_insert_ad

router = Router()
log = logging.getLogger(__name__)
WELCOME = ("Hey, girl! 💋\nWelcome to Slay English!\n"
"Я собрала для тебя свои полезные материалы, бесплатные подарки и кое-что интересное "
"для тех, кто хочет прокачать свой English ещё сильнее\nвыбирай, с чего начнём 👇🏻")

class UserStates(StatesGroup):
    waiting_subscription = State()

async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator") or (
            member.status == "restricted" and bool(getattr(member, "is_member", False))
        )
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        log.warning("Subscription check failed for %s: %s", user_id, exc)
        return False
    except Exception:
        log.exception("Unexpected subscription check error for %s", user_id)
        return False

async def send_item(message: Message, item):
    title = item["title"]
    descr = item["descr"] or ""
    if descr:
        await message.answer(f"<b>{escape(title)}</b>\n{escape(descr)}", parse_mode="HTML")
    fid, typ = item["file_id"], item["file_type"]
    if fid:
        methods = {
            "photo": message.answer_photo, "video": message.answer_video,
            "document": message.answer_document, "audio": message.answer_audio,
            "voice": message.answer_voice, "animation": message.answer_animation,
            "video_note": message.answer_video_note, "sticker": message.answer_sticker,
        }
        method = methods.get(typ, message.answer_document)
        kwargs = {"caption": title} if typ in {"photo", "video", "document", "audio", "animation"} else {}
        await method(fid, **kwargs)
    elif item["url"]:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть материал", url=item["url"])]])
        await message.answer(title, reply_markup=kb)

@router.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    await add_user(message.from_user)
    await message.answer(WELCOME, reply_markup=menu())

@router.message(F.text == "✨ Забрать бесплатные материалы")
async def materials(message: Message):
    rows = await get_items("material", True)
    await message.answer("Выбирай материал 🩷", reply_markup=item_choices(rows, "material"))
    if not rows:
        await message.answer("Скоро здесь появятся новые бесплатные материалы 🩷")

@router.message(F.text == "💅 Буст твоего английского")
async def courses(message: Message):
    rows = await get_items("course", True)
    await message.answer("Выбирай курс 💅", reply_markup=item_choices(rows, "course"))
    if not rows:
        await message.answer("Скоро здесь появятся новые курсы 💅")

@router.callback_query(F.data.startswith("item:"))
async def deliver_item(call: CallbackQuery, bot, state: FSMContext):
    try:
        _, kind, raw_id = call.data.split(":", 2)
        item = await get_item(int(raw_id))
    except (ValueError, AttributeError):
        await call.answer("Не удалось найти материал", show_alert=True)
        return
    if not item or item["kind"] != kind:
        await call.answer("Материал уже недоступен", show_alert=True)
        return
    if kind == "material" and not await is_subscribed(bot, call.from_user.id):
        await state.update_data(pending_item_id=int(raw_id))
        await state.set_state(UserStates.waiting_subscription)
        await call.message.answer("Подпишись на канал, чтобы получить материал 🩷", reply_markup=subscription_keyboard(CHANNEL_URL))
        await call.answer()
        return
    await call.answer()
    await send_item(call.message, item)
    if kind == "material":
        await send_insert_ad(bot, call.from_user.id)

@router.callback_query(F.data == "subscription:check")
async def check_subscription(call: CallbackQuery, bot, state: FSMContext):
    if await is_subscribed(bot, call.from_user.id):
        data = await state.get_data()
        pending_id = data.get("pending_item_id")
        await state.clear()
        await call.answer("Подписка подтверждена 🩷")
        if pending_id:
            item = await get_item(int(pending_id))
            if item and item["kind"] == "material":
                await send_item(call.message, item)
                await send_insert_ad(bot, call.from_user.id)
                return
        await call.message.answer("Отлично! Теперь выбери материал в меню 🩷", reply_markup=menu())
    else:
        await call.answer("Подписку пока не вижу. Подпишись и проверь ещё раз.", show_alert=True)
