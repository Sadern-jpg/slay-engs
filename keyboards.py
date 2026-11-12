from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(is_admin=False):
    rows=[[KeyboardButton(text="🎁 Материалы"),KeyboardButton(text="📚 Курсы")]]
    if is_admin: rows.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=rows,resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📦 Управление материалами"),KeyboardButton(text="🎓 Управление курсами")],
        [KeyboardButton(text="📨 Рассылка"),KeyboardButton(text="📢 Реклама")],
        [KeyboardButton(text="🧩 Рекламная вставка"),KeyboardButton(text="🛑 Кампании")],
        [KeyboardButton(text="⬅️ В меню")]],resize_keyboard=True)

def inline(items,prefix):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(label),callback_data=f"{prefix}:{value}")] for label,value in items])

def subscribe_keyboard(url):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подписаться на канал",url=url)],
        [InlineKeyboardButton(text="Проверить подписку",callback_data="check_sub")]])
