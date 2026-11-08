from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Добавить PDF",callback_data="add_pdf"),InlineKeyboardButton(text="➕ Добавить ссылку",callback_data="add_link")],
    [InlineKeyboardButton(text="💅 Добавить платный курс",callback_data="add_offer")],
    [InlineKeyboardButton(text="📚 Управление материалами",callback_data="manage_materials")],
    [InlineKeyboardButton(text="💎 Управление курсами",callback_data="manage_offers")],
    [InlineKeyboardButton(text="📣 Рассылка",callback_data="broadcast")],
    [InlineKeyboardButton(text="📊 Статистика",callback_data="stats")],
    [InlineKeyboardButton(text="⬅️ В меню бота",callback_data="home")]])

def list_kb(items,prefix):
    rows=[[InlineKeyboardButton(text=f"{'🟢' if x['active'] else '⚫'} {x['title'][:32]}",callback_data=f"{prefix}_item_{x['id']}")] for x in items]
    rows.append([InlineKeyboardButton(text="⬅️ В админку",callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def item_kb(prefix,item):
    return InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Выключить" if item["active"] else "Включить",callback_data=f"{prefix}_toggle_{item['id']}")],
    [InlineKeyboardButton(text="🗑 Удалить",callback_data=f"{prefix}_delete_{item['id']}")],
    [InlineKeyboardButton(text="⬅️ Назад",callback_data=f"manage_{'materials' if prefix=='mat' else 'offers'}")]])

def confirm_broadcast():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Отправить всем",callback_data="broadcast_send")],[InlineKeyboardButton(text="❌ Отменить",callback_data="admin")]])
