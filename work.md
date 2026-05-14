# Threads Automation — статус проекта

## Что реализовано и работает

### Инфраструктура
- FastAPI + async SQLAlchemy + Alembic миграции (SQLite dev / PostgreSQL prod)
- Pydantic Settings — конфиг из `.env`
- APScheduler — фоновые задачи без внешнего брокера
- HTTP Basic Auth на всех `/api/*` маршрутах (`app/auth.py`)
- Rate limiting 120 req/min по IP (`app/main.py`)
- Fernet-шифрование `api_token` в БД (`app/crypto.py`, `EncryptedString`)

### Модели данных
- `Account` — аккаунт, расписание, tone/audience/language/hashtags, OAuth-поля
- `ContentPlan` — план с топиком и статусом
- `Post` — пост с LLM-метаданными, retry-счётчиком, ошибками
- `ActivityLog` — аудит событий
- `Worker` — узлы для распределённого инференса (модель есть, раздача задач — нет)

### LLM слой
- `OllamaClient` и `OpenAICompatibleClient` (любой совместимый API)
- Per-account LLM-конфиг (`get_llm_client_for_account`)
- Синглтон-клиент, не пересоздаётся при каждом вызове

### Сервисы
- `ContentPlanner` — планы на N дней вперёд, CRON-расписание (`croniter`), учёт часового пояса
- `PostGenerator` — генерация через LLM, JSON-парсинг с regex-fallback
- `PostPublisher` — оркестрация: статусы, ActivityLog, retry-счётчик

### Планировщик (`app/scheduler/tasks.py`)
- `generate_content_plans` — ежедневно 01:00, параллельно по всем аккаунтам
- `generate_posts_for_upcoming` — каждый час, за N часов до публикации
- `publish_scheduled_posts` — каждую минуту, до 10 постов за раз
- `retry_failed_posts` — каждые 5 минут, exponential backoff
- `cleanup_old_logs` — ежедневно 03:00, логи старше 90 дней

### Паблишеры
- `MockPublisher` — для разработки и тестов
- `ThreadsAPIPublisher` — полная Meta Graph API v1.0: OAuth 2.0, container → publish, refresh токена, лимит 500 символов
- `BrowserPublisher` — Playwright с persistent profile, stealth-патчи, human-like мышь (Bezier + jitter), посимвольный ввод с опечатками
- `VisionAgent` — Qwen VL через Ollama: скриншот → координаты элемента, fallback на CSS-селекторы

### API (`app/api/`)
- CRUD аккаунтов, контентных планов, постов
- OAuth: `/oauth/url`, `/oauth/callback`, `/oauth/refresh`, `/threads/info`
- Workers: CRUD + heartbeat
- Dashboard: stats, upcoming, recent, health
- Ручной запуск: генерация плана, генерация поста, публикация, retry

### Веб-интерфейс
- 6 HTML-шаблонов (dashboard, accounts, workers, posts, logs, base)
- Inline JS в каждом шаблоне вызывает API через `fetch`
- `app/static/app.js` — хелперы (api, formatTime, escapeHtml, percent)
- Базовый функционал: просмотр данных, ручные триггеры, метрики

---

## Что осталось реализовать

### Приоритет 1 — важно для стабильной работы

**1. Авто-рефреш OAuth-токена при 401**
`ThreadsAPIPublisher` падает с ошибкой если токен истёк. Нужно в `publish()` перехватывать 401, вызывать `refresh_token()`, сохранять новый токен в БД и повторять запрос.
Файлы: `app/publishers/threads_api.py`, `app/api/accounts.py`

**2. Уведомления об ошибках**
Сейчас ошибки только в логах и ActivityLog. Когда пост не публикуется N раз подряд — никто не знает. Нужен хотя бы один канал: Telegram-бот (`httpx` POST к Bot API) или webhook.
Файлы: новый `app/services/notifier.py`, вызов из `app/scheduler/tasks.py`

**3. Хэширование пароля администратора**
В `app/auth.py` `secrets.compare_digest` сравнивает plaintext. Нужно хранить bcrypt-хеш в `.env` и при старте проверять через `passlib`.
Файлы: `app/auth.py`, `app/config.py`

---

### Приоритет 2 — расширение функциональности

**4. Публикация с изображениями**
Модель `Post` и все паблишеры принимают `media_urls`, но картинки не прикрепляются.
- `ThreadsAPIPublisher`: добавить `image_url` в контейнер (`media_type=IMAGE`)
- `BrowserPublisher`: VisionAgent найдёт кнопку прикрепления файла, загрузить через `page.set_input_files`
Файлы: `app/publishers/threads_api.py`, `app/publishers/browser_publisher.py`

**5. Docker-окружение**
`Dockerfile` + `docker-compose.yml` (app + PostgreSQL + Ollama). Сейчас деплой только вручную.

**6. Улучшения веб-интерфейса**
- Формы создания/редактирования аккаунта (сейчас нет модальных окон, только GET-запросы)
- Кнопка ручного старта каждого scheduler-джоба
- Предпросмотр сгенерированного поста перед публикацией
- Автообновление dashboard каждые 30 сек (`setInterval`)

---

### Приоритет 3 — желательно, но не срочно

**7. Базовые интеграционные тесты**
`tests/` почти пустые. Нужны тесты для:
- `ContentPlanner._parse_schedule` (CRON и fixed times)
- `PostGenerator` с mock LLM
- `ThreadsAPIPublisher` с mock httpx
- Один end-to-end тест scheduler → generator → publisher через MockPublisher

**8. Поддержка нескольких языков в LLM-промпте**
Поле `language` в Account есть, но в системный промпт `PostGenerator` не подставляется.
Файл: `app/services/post_generator.py`, метод `_build_system_prompt`

**9. Страница просмотра одного поста**
`GET /posts/{id}` в API есть, но в UI нет страницы с полным текстом, промптами и метаданными генерации.

**10. Распределённые воркеры**
Модель `Worker` и heartbeat-эндпоинт есть, но `get_llm_client_for_account` не проверяет is_online и не балансирует нагрузку. Если нужен реальный multi-GPU деплой — доделать логику выбора воркера.
Файл: `app/llm/__init__.py`, `get_llm_client_for_account`
