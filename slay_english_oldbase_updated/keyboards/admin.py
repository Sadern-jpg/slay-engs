from aiogram.types import ReplyKeyboardMarkup,KeyboardButton
def menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📚 Материалы")],
        [KeyboardButton(text="💎 Управление курсами")],
        [KeyboardButton(text="📣 Рассылка")],
        [KeyboardButton(text="📢 Реклама")],
        [KeyboardButton(text="🩷 Рекламная вставка")],
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="⬅️ В меню бота")]],resize_keyboard=True)
