"""
Конфигурация проекта. Все значения берутся из переменных окружения (.env).
Скопируй .env.example в .env и заполни своими значениями.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int | None = None) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        if default is None:
            raise ValueError(f"Переменная окружения {name} обязательна, но не задана")
        return default
    return int(value)


def _get_str(name: str, required: bool = True, default: str = "") -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Переменная окружения {name} обязательна, но не задана")
    return value


@dataclass
class Config:
    # Telegram Bot
    bot_token: str
    target_chat_id: int
    management_topic_id: int
    it_topic_id: int

    # PostgreSQL
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # Telegram User API (для чтения канала) — опционально, нужно только если включён telegram_parser
    telegram_api_id: int | None
    telegram_api_hash: str | None
    telegram_phone: str | None
    freelance_channel: str

    # Параметры поиска
    min_salary: int
    check_interval_minutes: int

    # Источники
    trudvsem_api_url: str
    proxy_url: str | None

    resume_path: str

    @property
    def db_dsn(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


def load_config() -> Config:
    return Config(
        bot_token=_get_str("BOT_TOKEN"),
        target_chat_id=_get_int("TARGET_CHAT_ID"),
        management_topic_id=_get_int("MANAGEMENT_TOPIC_ID"),
        it_topic_id=_get_int("IT_TOPIC_ID"),
        db_host=_get_str("DB_HOST", default="localhost"),
        db_port=_get_int("DB_PORT", default=5432),
        db_name=_get_str("DB_NAME", default="job_search_bot"),
        db_user=_get_str("DB_USER", default="postgres"),
        db_password=_get_str("DB_PASSWORD"),
        telegram_api_id=_get_int("TELEGRAM_API_ID", default=0) or None,
        telegram_api_hash=_get_str("TELEGRAM_API_HASH", required=False) or None,
        telegram_phone=_get_str("TELEGRAM_PHONE", required=False) or None,
        freelance_channel=_get_str("FREELANCE_CHANNEL", default="freelansim_ru"),
        min_salary=_get_int("MIN_SALARY", default=100000),
        check_interval_minutes=_get_int("CHECK_INTERVAL_MINUTES", default=10),
        trudvsem_api_url=_get_str(
            "TRUDVSEM_API_URL",
            default="http://opendata.trudvsem.ru/api/v1/vacancies",
        ),
        proxy_url=_get_str("PROXY_URL", required=False) or None,
        resume_path=_get_str("RESUME_PATH", default="./resume.txt"),
    )
