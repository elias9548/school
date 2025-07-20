from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Message
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# === Настройки ===
BOT_TOKEN = "8126347474:AAHsBWmNaABMOq3MxOVYd2LLfab6b5OYW6E"  # ← замени
ADMIN_ID = 7573577333      # ← замени
CHANNEL_ID = "@sch962"  # ← замени

# Хранилище заявок
pending = {}  # user_id: Message
awaiting_reason = {}  # admin_id: rejected_user_id

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришлите свою новость для публикации в канал.")

# === Обработка входящих новостей от пользователей ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg: Message = update.message
    user_id = msg.from_user.id

    # Сохраняем сообщение
    pending[user_id] = msg

    await msg.reply_text("Спасибо! Заявка отправлена на рассмотрение.")

    # Отправляем админу с кнопками
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"accept|{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject|{user_id}")
        ]
    ])

    # Пересылаем новость админу
    await msg.forward(chat_id=ADMIN_ID)
    await context.bot.send_message(chat_id=ADMIN_ID,
        text=f"Заявка от @{msg.from_user.username or 'пользователя'} (ID: {user_id})",
        reply_markup=keyboard
    )

# === Обработка нажатий на кнопки ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, target_id = query.data.split("|")
    target_id = int(target_id)

    if action == "accept":
        msg = pending.get(target_id)
        if msg:
            await forward_original(msg, context)
            await context.bot.send_message(chat_id=target_id, text="✅ Ваша новость опубликована.")
            await query.edit_message_text("Новость принята и отправлена в канал.")
            del pending[target_id]
    elif action == "reject":
        awaiting_reason[query.from_user.id] = target_id
        await query.edit_message_text("Введите причину отклонения.")

# === Отправка причины отклонения ===
async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.message.from_user.id
    if admin_id in awaiting_reason:
        target_id = awaiting_reason.pop(admin_id)
        reason = update.message.text

        await context.bot.send_message(chat_id=target_id,
            text=f"❌ Ваша новость отклонена.\nПричина: {reason}")
        await update.message.reply_text("Причина отправлена пользователю.")
        if target_id in pending:
            del pending[target_id]

# === Пересылка сообщения в канал в оригинальном формате ===
async def forward_original(msg: Message, context: ContextTypes.DEFAULT_TYPE):
    if msg.text:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg.text)
    elif msg.caption and msg.photo:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=msg.photo[-1].file_id, caption=msg.caption)
    elif msg.photo:
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=msg.photo[-1].file_id)
    elif msg.video:
        await context.bot.send_video(chat_id=CHANNEL_ID, video=msg.video.file_id, caption=msg.caption or "")
    elif msg.voice:
        await context.bot.send_voice(chat_id=CHANNEL_ID, voice=msg.voice.file_id, caption=msg.caption or "")
    elif msg.audio:
        await context.bot.send_audio(chat_id=CHANNEL_ID, audio=msg.audio.file_id, caption=msg.caption or "")
    else:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="(Неизвестный тип сообщения)")

# === Запуск ===
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=ADMIN_ID), handle_admin_text))
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

app.run_polling()