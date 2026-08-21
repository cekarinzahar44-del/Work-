"""
Парсер Habr Career — статические страницы, без JS-рендеринга, поэтому
достаточно httpx + BeautifulSoup (без Playwright).
"""
import httpx
from bs4 import BeautifulSoup

from db.storage import Vacancy
from filters.vacancy_filter import passes_all_filters, calculate_match_score

BASE_URL = "https://career.habr.com/vacancies"


async def fetch_habr_vacancies(min_salary: int) -> list[Vacancy]:
    results: list[Vacancy] = []

    params = {"type": "remote", "q": "управляющий OR административный"}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        try:
            resp = await client.get(BASE_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPError:
            return results

        soup = BeautifulSoup(resp.text, "html.parser")
        # Примечание: селекторы ориентировочные, перед запуском стоит сверить
        # с актуальной вёрсткой career.habr.com
        cards = soup.select("div.vacancy-card")

        for card in cards:
            title_el = card.select_one("a.vacancy-card__title-link")
            title = title_el.get_text(strip=True) if title_el else ""
            link = title_el.get("href", "") if title_el else ""
            if link and link.startswith("/"):
                link = f"https://career.habr.com{link}"

            company_el = card.select_one("a.vacancy-card__company-title")
            company = company_el.get_text(strip=True) if company_el else None

            salary_el = card.select_one("div.basic-salary")
            salary_text = salary_el.get_text(strip=True) if salary_el else ""

            description_el = card.select_one("div.vacancy-card__skills")
            description = description_el.get_text(" ", strip=True) if description_el else ""

            if not title or not link:
                continue

            salary_from, salary_to = _parse_salary(salary_text)

            if not passes_all_filters(
                title=title,
                description=description,
                min_salary=min_salary,
                salary_from=salary_from,
                salary_to=salary_to,
                schedule_field=None,  # Habr не отдаёт отдельное поле, проверяем по тексту
            ):
                continue

            results.append(
                Vacancy(
                    source="habr",
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

    return results


def _parse_salary(text: str) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    digits = "".join(c if c.isdigit() or c == " " else " " for c in text)
    numbers = [int(n) for n in digits.split() if n.isdigit()]
    if not numbers:
        return None, None
    if len(numbers) == 1:
        return numbers[0], None
    return numbers[0], numbers[1]
