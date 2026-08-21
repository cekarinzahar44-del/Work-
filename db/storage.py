"""
Работа с PostgreSQL: сохранение вакансий, проверка дублей, выборка неотправленных.
"""
import hashlib
from dataclasses import dataclass
from datetime import datetime

import asyncpg


@dataclass
class Vacancy:
    source: str            # trudvsem | habr | hh | rabota | telegram
    direction: str          # management | it
    title: str
    company: str | None
    salary_from: int | None
    salary_to: int | None
    is_remote: bool
    description: str
    url: str
    match_score: float = 0.0

    @property
    def unique_hash(self) -> str:
        # Хэш по источнику и ссылке — защита от повторной отправки одной и той же вакансии
        raw = f"{self.source}:{self.url}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Storage:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def init_schema(self, schema_path: str):
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        async with self.pool.acquire() as conn:
            await conn.execute(sql)

    async def save_vacancy(self, vacancy: Vacancy) -> bool:
        """
        Сохраняет вакансию, если её ещё нет в базе.
        Возвращает True, если вакансия новая (сохранена), False — если уже была (дубль).
        """
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO vacancies
                        (unique_hash, source, direction, title, company,
                         salary_from, salary_to, is_remote, description, url, match_score)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    vacancy.unique_hash,
                    vacancy.source,
                    vacancy.direction,
                    vacancy.title,
                    vacancy.company,
                    vacancy.salary_from,
                    vacancy.salary_to,
                    vacancy.is_remote,
                    vacancy.description,
                    vacancy.url,
                    vacancy.match_score,
                )
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def get_unsent(self, direction: str, limit: int = 20):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM vacancies
                WHERE direction = $1 AND sent_at IS NULL
                ORDER BY match_score DESC, created_at ASC
                LIMIT $2
                """,
                direction,
                limit,
            )
            return rows

    async def mark_sent(self, vacancy_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE vacancies SET sent_at = $1 WHERE id = $2",
                datetime.utcnow(),
                vacancy_id,
            )
