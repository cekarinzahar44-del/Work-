-- Таблица вакансий. unique_hash защищает от дублей (источник + ссылка)
CREATE TABLE IF NOT EXISTS vacancies (
    id SERIAL PRIMARY KEY,
    unique_hash VARCHAR(64) UNIQUE NOT NULL,
    source VARCHAR(32) NOT NULL,          -- trudvsem, habr, hh, rabota, telegram
    direction VARCHAR(16) NOT NULL,       -- management, it
    title TEXT NOT NULL,
    company TEXT,
    salary_from INTEGER,
    salary_to INTEGER,
    is_remote BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    url TEXT NOT NULL,
    match_score REAL DEFAULT 0,           -- совпадение с резюме, 0..1
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMP                     -- когда отправлено в бот (NULL = ещё не отправлено)
);

CREATE INDEX IF NOT EXISTS idx_vacancies_sent_at ON vacancies (sent_at);
CREATE INDEX IF NOT EXISTS idx_vacancies_direction ON vacancies (direction);
CREATE INDEX IF NOT EXISTS idx_vacancies_source ON vacancies (source);
