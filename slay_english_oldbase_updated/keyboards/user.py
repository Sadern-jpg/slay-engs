from aiogram.types import ReplyKeyboardMarkup,KeyboardButton,InlineKeyboardMarkup,InlineKeyboardButton
def menu():
 return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✨ Забрать бесплатные материалы")],[KeyboardButton(text="💅 Буст твоего английского")]],resize_keyboard=True)
def choices(kind,rows):
 return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=r["title"],callback_data=f"item:{kind}:{r['id']}")] for r in rows if r["active"]]) if rows else None
def subscribe(url):
 return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Подписаться",url=url)],[InlineKeyboardButton(text="Проверить подписку",callback_data="subcheck")]])
