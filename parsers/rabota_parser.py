"""
Парсер Rabota.ru через Playwright, БЕЗ АВТОРИЗАЦИИ — только публичные страницы поиска.
Та же логика рисков, что и у hh_parser.py: вёрстка может меняться, возможны капчи,
обязательны задержки между запросами.
"""
import asyncio
import random

from playwright.async_api import async_playwright

from db.storage import Vacancy
from filters.vacancy_filter import passes_all_filters, calculate_match_score
from parsers.hh_parser import _parse_salary  # переиспользуем парсинг строки ЗП

SEARCH_QUERIES = [
    "управляющий",
    "заместитель директора",
    "административно-хозяйственный отдел",
]

BASE_URL = "https://www.rabota.ru/vacancy"


async def _random_delay(min_sec: float = 3.0, max_sec: float = 8.0):
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def fetch_rabota_vacancies(min_salary: int, proxy_url: str | None = None) -> list[Vacancy]:
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
            url = f"{BASE_URL}?query={query}&remote=true"
            try:
                await page.goto(url, timeout=20000)
                # ПРИМЕЧАНИЕ: селектор ниже примерный — перед первым запуском нужно
                # свериться с актуальной вёрсткой rabota.ru через devtools
                await page.wait_for_selector(".vacancy-preview-card", timeout=10000)
            except Exception:
                await _random_delay()
                continue

            cards = await page.query_selector_all(".vacancy-preview-card")
            for card in cards:
                try:
                    title_el = await card.query_selector(".vacancy-preview-card__title")
                    title = (await title_el.inner_text()) if title_el else ""
                    link = (await title_el.get_attribute("href")) if title_el else ""
                    if link and link.startswith("/"):
                        link = f"https://www.rabota.ru{link}"

                    company_el = await card.query_selector(".vacancy-preview-card__company")
                    company = (await company_el.inner_text()) if company_el else None

                    salary_el = await card.query_selector(".vacancy-preview-card__salary")
                    salary_text = (await salary_el.inner_text()) if salary_el else ""

                    description_el = await card.query_selector(".vacancy-preview-card__description")
                    description = (await description_el.inner_text()) if description_el else ""

                    if not title or not link:
                        continue

                    salary_from, salary_to = _parse_salary(salary_text)

                    if not passes_all_filters(
                        title=title,
                        description=description,
                        min_salary=min_salary,
                        salary_from=salary_from,
                        salary_to=salary_to,
                        schedule_field="remote",
                    ):
                        continue

                    results.append(
                        Vacancy(
                            source="rabota",
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

            await _random_delay()

        await browser.close()

    return results
