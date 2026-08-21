"""
Чтение публичного Telegram-канала с фриланс-заказами (например @freelansim_ru)
через Telethon (Telegram User API — требует TELEGRAM_API_ID/HASH/PHONE).

Направление IT — второстепенное, но источник простой и стабильный (нет риска
блокировки, как с HH.ru/Rabota.ru, так как это официальный Telegram API).
"""
import re
from datetime import datetime, timedelta

from telethon import TelegramClient

from db.storage import Vacancy
from filters.vacancy_filter import is_title_excluded, calculate_match_score

# Ключевые слова, по которым отбираем посты как релевантные IT-заказы
IT_ORDER_KEYWORDS = [
    "telegram", "телеграм", "бот", "mini app", "миниапп", "aiogram", "python",
]


async def fetch_telegram_vacancies(
    api_id: int,
    api_hash: str,
    phone: str,
    channel: str,
    session_name: str = "job_search_session",
    lookback_hours: int = 24,
) -> list[Vacancy]:
    results: list[Vacancy] = []

    client = TelegramClient(session_name, api_id, api_hash)
    await client.start(phone=phone)

    try:
        since = datetime.utcnow() - timedelta(hours=lookback_hours)
        async for message in client.iter_messages(channel, limit=200):
            if message.date.replace(tzinfo=None) < since:
                break
            text = message.text or ""
            if not text:
                continue

            text_lower = text.lower()
            if not any(kw in text_lower for kw in IT_ORDER_KEYWORDS):
                continue

            # Первая строка обычно содержит суть заказа — используем как заголовок
            title = text.strip().split("\n")[0][:200]

            if is_title_excluded(title):
                continue

            link = f"https://t.me/{channel}/{message.id}"
            salary_from = _extract_price(text)

            results.append(
                Vacancy(
                    source="telegram",
                    direction="it",
                    title=title,
                    company=None,
                    salary_from=salary_from,
                    salary_to=None,
                    is_remote=True,  # фриланс-заказы по определению удалённые
                    description=text[:2000],
                    url=link,
                    match_score=calculate_match_score(title, text, "it"),
                )
            )
    finally:
        await client.disconnect()

    return results


def _extract_price(text: str) -> int | None:
    """Ищет упоминание цены вида '40 000 руб.' в тексте поста."""
    match = re.search(r"(\d[\d\s]{3,})\s*(?:руб|₽)", text)
    if not match:
        return None
    digits = match.group(1).replace(" ", "")
    return int(digits) if digits.isdigit() else None
