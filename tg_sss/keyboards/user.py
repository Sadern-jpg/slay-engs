from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(admin=False):
    rows=[[InlineKeyboardButton(text="✨ Забрать бесплатные материалы",callback_data="materials")],[InlineKeyboardButton(text="💅 Буст твоего английского",callback_data="offers")]]
    if admin: rows.append([InlineKeyboardButton(text="⚙️ Админ-панель",callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_home():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню",callback_data="home")]])

def subscribe_keyboard(url):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📢 Подписаться на канал",url=url)],[InlineKeyboardButton(text="🔄 Проверить подписку",callback_data="check_sub")],[InlineKeyboardButton(text="⬅️ К материалам",callback_data="materials")]])

def material_keyboard(items):
    rows=[[InlineKeyboardButton(text=f"🎁 {x['title'][:45]}",callback_data=f"getmat_{x['id']}")] for x in items]
    rows.append([InlineKeyboardButton(text="⬅️ В меню",callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def offer_keyboard(items):
    rows=[[InlineKeyboardButton(text=f"💅 {x['title'][:40]}",url=x["url"])] for x in items]
    rows.append([InlineKeyboardButton(text="⬅️ В меню",callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def reminder_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Записаться 💋",url="https://t.me/kot_begemot3")],[InlineKeyboardButton(text="Отзывы учениц ❣️",url="https://t.me/slaytalks")],[InlineKeyboardButton(text="Понятно, спасибо 🩷",callback_data="reminder_ack")]])
