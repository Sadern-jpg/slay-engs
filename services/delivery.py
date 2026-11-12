from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import connect

async def deliver_material(bot, user_id: int, material_id: int):
    async with await connect() as db:
        cur = await db.execute("SELECT * FROM materials WHERE id=? AND active=1", (material_id,))
        material = await cur.fetchone()
        cur = await db.execute("SELECT value FROM settings WHERE key='ad_insert'")
        ad = await cur.fetchone()
    if not material:
        await bot.send_message(user_id, "Этот материал больше недоступен.")
        return

    caption = f"<b>{material['title']}</b>"
    if material["description"]:
        caption += f"\n{material['description']}"

    if material["url"]:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть материал", url=material["url"]) ]])
        await bot.send_message(user_id, caption, reply_markup=keyboard)
    elif material["file_id"]:
        file_id = material["file_id"]
        file_type = material["file_type"]
        if file_type == "photo":
            await bot.send_photo(user_id, file_id, caption=caption)
        elif file_type == "video":
            await bot.send_video(user_id, file_id, caption=caption)
        elif file_type == "document":
            await bot.send_document(user_id, file_id, caption=caption)
        elif file_type == "audio":
            await bot.send_audio(user_id, file_id, caption=caption)
        else:
            await bot.send_message(user_id, caption)
    else:
        await bot.send_message(user_id, caption)

    if ad and ad["value"]:
        await bot.send_message(user_id, ad["value"])
