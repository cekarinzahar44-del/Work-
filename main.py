"""
Единая точка входа для BotHost (там поле "Главный файл" задаётся один раз
при создании и не меняется потом).

Логика:
- Если задана переменная окружения RUN_MODE=get_ids -> запускается вспомогательный
  скрипт получения chat_id/thread_id (get_ids.py)
- Иначе (по умолчанию) -> запускается основной бот (bot/main.py)

Как использовать:
1. На первом шаге (получение ID тем) добавь в переменные окружения BotHost:
   RUN_MODE=get_ids
   BOT_TOKEN=... (только он нужен на этом шаге)
2. После получения ID — просто удали переменную RUN_MODE (или поставь RUN_MODE=bot)
   и добавь остальные переменные (TARGET_CHAT_ID, MANAGEMENT_TOPIC_ID, IT_TOPIC_ID и т.д.)
3. Перезапусти бота на BotHost — переключение произойдёт без пересоздания проекта
"""
import os
import runpy

run_mode = os.getenv("RUN_MODE", "bot")

if run_mode == "get_ids":
    print("=== Режим получения ID (RUN_MODE=get_ids) ===")
    runpy.run_path("get_ids.py", run_name="__main__")
else:
    print("=== Режим основного бота (RUN_MODE=bot) ===")
    runpy.run_path("bot/main.py", run_name="__main__")
