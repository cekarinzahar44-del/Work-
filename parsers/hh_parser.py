"""
Парсер HH.ru через Playwright (публичный API закрыт с апреля 2026).
Работает БЕЗ АВТОРИЗАЦИИ — читает только публичные страницы поиска вакансий.

ВАЖНО: это самый хрупкий источник в системе.
- HH.ru может менять вёрстку — селекторы придётся обновлять
- Возможны капчи — при их появлении воркер просто пропускает цикл
- Между запросами обязательны случайные задержки, иначе риск блокировки IP
"""
import asyncio
import random

from playwright.async_api import async_playwright

from db.storage import Vacancy
from filters.vacancy_filter import passes_all_filters, calculate_match_score

SEARCH_QUERIES = [
    "управляющий",
    "заместитель директора",
    "административно-хозяйственный отдел",
]

BASE_URL = "https://hh.ru/search/vacancy"


async def _random_delay(min_sec: float = 3.0, max_sec: float = 8.0):
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def fetch_hh_vacancies(min_salary: int, proxy_url: str | None = None) -> list[Vacancy]:
    results: list[Vacancy] = []

    async with async_playwright() as p:
        launch_kwargs = {"headless": True}
        if proxy_url:
            launch_kwargs["proxy"] = {"server": proxy_url}

        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        for query in SEARCH_QUERIES:
            url = f"{BASE_URL}?text={query}&schedule=remote&order_by=publication_time"
            try:
                await page.goto(url, timeout=20000)
                await page.wait_for_selector(
                    '[data-qa="vacancy-serp__vacancy"]', timeout=10000
                )
            except Exception:
                # Капча, таймаут или изменившаяся вёрстка — пропускаем этот запрос
                await _random_delay()
                continue

            cards = await page.query_selector_all('[data-qa="vacancy-serp__vacancy"]')
            for card in cards:
                try:
                    title_el = await card.query_selector('[data-qa="serp-item__title"]')
                    title = (await title_el.inner_text()) if title_el else ""
                    link = (await title_el.get_attribute("href")) if title_el else ""

                    company_el = await card.query_selector('[data-qa="vacancy-serp__vacancy-employer"]')
                    company = (await company_el.inner_text()) if company_el else None

                    salary_el = await card.query_selector('[data-qa="vacancy-serp__vacancy-compensation"]')
                    salary_text = (await salary_el.inner_text()) if salary_el else ""

                    snippet_el = await card.query_selector('[data-qa="vacancy-serp__vacancy_snippet_responsibility"]')
                    description = (await snippet_el.inner_text()) if snippet_el else ""

                    if not title or not link:
                        continue

                    salary_from, salary_to = _parse_salary(salary_text)

                    if not passes_all_filters(
                        title=title,
                        description=description,
                        min_salary=min_salary,
                        salary_from=salary_from,
                        salary_to=salary_to,
                        schedule_field="remote",  # уже отфильтровано в query, но подтверждаем
                    ):
                        continue

                    results.append(
                        Vacancy(
                            source="hh",
                            direction="management",
                            title=title,
                            company=company,
                            salary_from=salary_from,
                            salary_to=salary_to,
                            is_remote=True,
                            description=description[:2000],
                            url=link,
                            match_score=calculate_match_score(title, description, "management"),
                        )
                    )
                except Exception:
                    continue

            await _random_delay()  # задержка между запросами — снижает риск блокировки

        await browser.close()

    return results


def _parse_salary(text: str) -> tuple[int | None, int | None]:
    """Грубый парсинг строки вида '150 000 - 200 000 руб.' -> (150000, 200000)."""
    if not text:
        return None, None
    digits = "".join(c if c.isdigit() or c == " " else " " for c in text)
    numbers = [int(n) for n in digits.split() if n.isdigit()]
    if not numbers:
        return None, None
    if len(numbers) == 1:
        return numbers[0], None
    return numbers[0], numbers[1]
