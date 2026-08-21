"""
Главный файл бота. Запускает:
1. aiogram-бота (отправка вакансий в чат по топикам)
2. Планировщик, который каждые N минут запускает все парсеры
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import load_config
from db.storage import Storage
from parsers.trudvsem_parser import fetch_trudvsem_vacancies
from parsers.hh_parser import fetch_hh_vacancies
from parsers.rabota_parser import fetch_rabota_vacancies
from parsers.habr_parser import fetch_habr_vacancies
from parsers.telegram_parser import fetch_telegram_vacancies

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("job_search_bot")

config = load_config()
storage = Storage(config.db_dsn)
bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


def format_vacancy_message(row) -> str:
    salary = ""
    if row["salary_from"] or row["salary_to"]:
        parts = []
        if row["salary_from"]:
            parts.append(f"от {row['salary_from']:,}".replace(",", " "))
        if row["salary_to"]:
            parts.append(f"до {row['salary_to']:,}".replace(",", " "))
        salary = " ".join(parts) + " ₽"

    company = f"\n🏢 {row['company']}" if row["company"] else ""
    salary_line = f"\n💰 {salary}" if salary else ""

    return (
        f"<b>{row['title']}</b>{company}{salary_line}\n"
        f"📍 Источник: {row['source']}\n"
        f"🔗 {row['url']}"
    )


async def send_pending_vacancies():
    """Достаёт неотправленные вакансии из БД и рассылает по нужным топикам."""
    for direction, topic_id in (
        ("management", config.management_topic_id),
        ("it", config.it_topic_id),
    ):
        rows = await storage.get_unsent(direction, limit=20)
        for row in rows:
            try:
                await bot.send_message(
                    chat_id=config.target_chat_id,
                    message_thread_id=topic_id,
                    text=format_vacancy_message(row),
                )
                await storage.mark_sent(row["id"])
            except Exception as e:
                logger.error(f"Не удалось отправить вакансию {row['id']}: {e}")


async def run_all_parsers():
    """Запускает все источники и сохраняет новые вакансии в БД."""
    logger.info("Запуск цикла парсинга...")

    # Управленческое направление (основной фокус)
    try:
        for vac in await fetch_trudvsem_vacancies(config.trudvsem_api_url, config.min_salary):
            await storage.save_vacancy(vac)
    except Exception as e:
        logger.error(f"Ошибка trudvsem_parser: {e}")

    try:
        for vac in await fetch_habr_vacancies(config.min_salary):
            await storage.save_vacancy(vac)
    except Exception as e:
        logger.error(f"Ошибка habr_parser: {e}")

    try:
        for vac in await fetch_hh_vacancies(config.min_salary, config.proxy_url):
            await storage.save_vacancy(vac)
    except Exception as e:
        logger.error(f"Ошибка hh_parser: {e}")

    try:
        for vac in await fetch_rabota_vacancies(config.min_salary, config.proxy_url):
            await storage.save_vacancy(vac)
    except Exception as e:
        logger.error(f"Ошибка rabota_parser: {e}")

    # IT-направление (второстепенное) — включится автоматически, как только
    # будут заданы TELEGRAM_API_ID / TELEGRAM_API_HASH / TELEGRAM_PHONE.
    # Пока эти переменные не заданы — блок просто пропускается.
    if config.telegram_api_id and config.telegram_api_hash and config.telegram_phone:
        try:
            for vac in await fetch_telegram_vacancies(
                config.telegram_api_id,
                config.telegram_api_hash,
                config.telegram_phone,
                config.freelance_channel,
            ):
                await storage.save_vacancy(vac)
        except Exception as e:
            logger.error(f"Ошибка telegram_parser: {e}")
    else:
        logger.info("Telegram parser пропущен: TELEGRAM_API_ID/HASH/PHONE не заданы")

    logger.info("Цикл парсинга завершён, рассылаю новые вакансии...")
    await send_pending_vacancies()


async def main():
    await storage.connect()
    await storage.init_schema("db/schema.sql")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_all_parsers,
        "interval",
        minutes=config.check_interval_minutes,
        next_run_time=None,  # запустится по первому интервалу; можно поставить datetime.now() для мгновенного старта
    )
    scheduler.start()

    logger.info("Бот запущен, планировщик активен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
