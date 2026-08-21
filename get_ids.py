"""
Разовый вспомогательный скрипт: запусти его, напиши любое сообщение в теме
"Управление" и в теме "IT" внутри группы (бот должен уже быть добавлен в группу) —
скрипт выведет chat_id группы и message_thread_id каждой темы в консоль.

Запуск: BOT_TOKEN=твой_токен python get_ids.py
После получения всех ID — этот скрипт больше не нужен, используется только один раз.
"""
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise SystemExit("Укажи BOT_TOKEN: BOT_TOKEN=твой_токен python get_ids.py")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message()
async def handle_any_message(message: Message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    thread_name = None

    if message.reply_to_message and message.reply_to_message.forum_topic_created:
        thread_name = message.reply_to_message.forum_topic_created.name

    print("=" * 50)
    print(f"Chat ID (TARGET_CHAT_ID): {chat_id}")
    print(f"Thread ID (для этой темы): {thread_id}")
    if thread_name:
        print(f"Название темы: {thread_name}")
    print("Текст сообщения:", message.text)
    print("=" * 50)


async def main():
    print("Скрипт запущен. Напиши сообщение в теме 'Управление', затем в теме 'IT'.")
    print("Каждый раз тут будет печататься chat_id и thread_id.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
