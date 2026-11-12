from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✨ Забрать бесплатные материалы")],
        [KeyboardButton(text="💅 Буст твоего английского")]
    ], resize_keyboard=True)

def item_choices(rows, kind):
    buttons = [[InlineKeyboardButton(text=str(row["title"])[:60], callback_data=f"item:{kind}:{row['id']}")]
               for row in rows if row["active"]]
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

def subscription_keyboard(url):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подписаться на канал", url=url)],
        [InlineKeyboardButton(text="Проверить подписку", callback_data="subscription:check")]
    ])
