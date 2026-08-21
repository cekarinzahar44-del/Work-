"""
Фильтрация вакансий:
1. Только удалённые
2. Исключение по НАЗВАНИЮ должности (не по всему тексту) — менеджер/руководитель отдела продаж
3. Минимальная ЗП (если указана)
4. Скоринг совпадения с резюме по ключевым словам
"""
import re

# Стоп-паттерны применяются ТОЛЬКО к заголовку вакансии.
# Упоминание "продажи" в описании другой должности не является основанием для исключения.
TITLE_STOP_PATTERNS = [
    r"менеджер[а-я\s]*по продажам",
    r"руководител[ья]\s+(отдела\s+)?продаж",
    r"начальник[а-я\s]*отдела продаж",
    r"директор по продажам",
    r"head of sales",
    r"sales manager",
    r"sales director",
    r"\bроп\b",
]

REMOTE_PATTERNS = [
    r"удал[её]нн", r"remote", r"из дома", r"дистанцион",
]

MANAGEMENT_KEYWORDS = [
    "управление персоналом", "кадровое делопроизводство", "график работы",
    "штатное расписание", "фот", "инвентаризац", "кассовая дисциплина",
    "управленческая отчетность", "внутренний контроль", "стандарты",
    "обучение персонала", "подбор персонала", "ресторанный менеджмент",
    "административно-хозяйств", "ахо", "операционное управление",
    "бюджет", "заместитель директора", "территориальный управляющий",
    "управляющий", "мотивация персонала", "руководство коллективом",
]

IT_KEYWORDS = [
    "telegram", "телеграм", "бот", "mini app", "миниапп", "aiogram",
    "python", "node.js", "postgresql", "ai агент", "чат-бот",
]


def _matches_any(text, patterns):
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def is_title_excluded(title):
    return _matches_any(title, TITLE_STOP_PATTERNS)


def is_remote(title, description, schedule_field=None):
    if schedule_field is not None:
        return schedule_field.lower() in ("remote", "удаленная работа", "удалённая работа")
    combined = f"{title} {description}"
    return _matches_any(combined, REMOTE_PATTERNS)


def passes_salary_filter(salary_from, salary_to, min_salary):
    if salary_from is None and salary_to is None:
        return True
    candidate = salary_from or salary_to
    return candidate >= min_salary


def calculate_match_score(title, description, direction):
    keywords = MANAGEMENT_KEYWORDS if direction == "management" else IT_KEYWORDS
    text = f"{title} {description}".lower()
    matched = sum(1 for kw in keywords if kw in text)
    if not keywords:
        return 0.0
    return round(matched / len(keywords), 3)


def passes_all_filters(title, description, min_salary, salary_from=None, salary_to=None, schedule_field=None):
    if is_title_excluded(title):
        return False
    if not is_remote(title, description, schedule_field):
        return False
    if not passes_salary_filter(salary_from, salary_to, min_salary):
        return False
    return True
