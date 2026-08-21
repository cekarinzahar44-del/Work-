"""
Парсер вакансий с trudvsem.ru ("Работа России") — официальное открытое API,
без авторизации. Документация: https://trudvsem.ru/opendata/api
"""
import httpx

from db.storage import Vacancy
from filters.vacancy_filter import passes_all_filters, calculate_match_score

# Поисковые запросы для управленческого направления (основной фокус)
MANAGEMENT_QUERIES = [
    "управляющий",
    "заместитель директора",
    "административно-хозяйственный отдел",
    "операционный менеджер",
    "управление персоналом",
]


async def fetch_trudvsem_vacancies(api_url: str, min_salary: int) -> list[Vacancy]:
    results: list[Vacancy] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for query in MANAGEMENT_QUERIES:
            params = {
                "text": query,
                "limit": 50,
                # API поддерживает фильтр по региону/типу занятости через доп. параметры,
                # но фильтр "удалённо" на стороне API нестабилен — дублируем проверку локально.
            }
            try:
                resp = await client.get(api_url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, ValueError):
                continue

            items = data.get("results", {}).get("vacancies", [])
            for item in items:
                vac = item.get("vacancy", {})
                title = vac.get("job-name", "")
                description = vac.get("duty", "") or ""
                company = (vac.get("company") or {}).get("name")

                salary_from = vac.get("salary_min")
                salary_to = vac.get("salary_max")
                schedule = (vac.get("schedule") or "")
                url = vac.get("vac_url") or vac.get("source", "")

                if not title or not url:
                    continue

                if not passes_all_filters(
                    title=title,
                    description=description,
                    min_salary=min_salary,
                    salary_from=salary_from,
                    salary_to=salary_to,
                    schedule_field=schedule,
                ):
                    continue

                results.append(
                    Vacancy(
                        source="trudvsem",
                        direction="management",
                        title=title,
                        company=company,
                        salary_from=salary_from,
                        salary_to=salary_to,
                        is_remote=True,
                        description=description[:2000],
                        url=url,
                        match_score=calculate_match_score(title, description, "management"),
                    )
                )

    return results
