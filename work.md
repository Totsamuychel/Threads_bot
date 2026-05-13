# Статус проекта: Threads Automation

## Что реализовано

### Инфраструктура
- FastAPI приложение с полной async поддержкой
- SQLAlchemy async ORM + Alembic миграции
- PostgreSQL (prod) / SQLite (dev) через единый интерфейс
- Pydantic Settings — конфигурация из .env
- APScheduler (AsyncIOScheduler) — фоновые задачи без внешнего брокера
- Docker + docker-compose

### Модели данных
- `Account` — конфигурация аккаунта, расписание, tone/audience/language/hashtags
- `ContentPlan` — план публикации с топиком и статусом
- `Post` — сгенерированный пост с LLM-метаданными
- `ActivityLog` — полный аудит всех событий системы
- `Worker` — воркер-ноды для распределённого LLM-инференса

### LLM слой (`app/llm/`)
- `BaseLLMClient` — абстракция с методом `generate()`
- `OllamaClient` — локальный Ollama сервер
- `OpenAICompatibleClient` — OpenAI / Azure / любой совместимый API
- `get_llm_client()` — синглтон для дефолтных настроек, новый клиент для per-account конфигов
- `get_llm_client_for_account()` — выбирает воркер-ноду если назначена аккаунту

### Паблишеры (`app/publishers/`)
- `BasePublisher` — абстракция с методами `publish()`, `health_check()`, `get_account_info()`
- `MockPublisher` — логирует в консоль, хранит в памяти (для разработки и тестов)
- `ThreadsAPIPublisher` — структура есть, реальная логика не реализована (см. "Не реализовано")

### Сервисы (`app/services/`)
- `ContentPlanner` — генерирует ContentPlan записи на N дней вперёд по расписанию аккаунта
- `PostGenerator` — вызывает LLM, парсит JSON-ответ (с regex fallback для markdown-блоков), сохраняет Post
- `PostPublisher` — оркестрирует публикацию, пишет ActivityLog, обновляет статусы

### Планировщик (`app/scheduler/tasks.py`)
- `generate_content_plans` — ежедневно в 1:00, параллельно по всем аккаунтам через `asyncio.gather`
- `generate_posts_for_upcoming` — каждый час, генерирует посты за N часов до публикации
- `publish_scheduled_posts` — каждую минуту, публикует до 10 постов за раз (`.limit(10)`)
- `retry_failed_posts` — каждые 5 минут, exponential backoff (300s × 2^retry_count)
- `cleanup_old_logs` — ежедневно в 3:00, удаляет логи старше 90 дней

### API (`app/api/`)
- CRUD аккаунтов: создание, редактирование, активация/деактивация
- Контент: список планов и постов, ручной запуск генерации и публикации
- Dashboard: статистика (success rate, pending, recent activity, upcoming posts)
- Workers: управление воркер-нодами
- Pages: веб-страницы для admin UI

### Веб-интерфейс
- HTML шаблоны + CSS/JS в `app/templates/` и `app/static/`
- Административный UI: просмотр постов, ручные триггеры, метрики

---

## Что не реализовано / требует доработки

### Критично (блокирует production)

~~**1. Реальная интеграция с Threads API**~~ ✅ реализовано  
`app/publishers/threads_api.py` — полная реализация на Meta Graph API v1.0:
- OAuth 2.0: генерация URL, обмен кода на short-lived → long-lived токен, refresh
- Публикация в два шага: создание контейнера → `threads_publish`
- Автоматическое получение credentials из БД по `account_id`
- Поддержка текстовых и image-постов, форматирование с хэштегами (лимит 500 символов)
- Модель `Account` расширена: `threads_user_id`, `token_expires_at`
- Новые API эндпоинты: `GET /{id}/oauth/url`, `GET /oauth/callback`, `POST /{id}/oauth/refresh`, `GET /{id}/threads/info`
- Миграция `002_add_threads_oauth_fields.py`

~~**2. Небезопасные дефолты в `app/config.py`**~~ ✅ исправлено

### Важно

~~**3. CRON-расписание в ContentPlanner**~~ ✅ исправлено  
Поддержка формата `{"cron": "0 9,18 * * 1-5"}` через библиотеку `croniter`. Разные дни могут иметь разное количество постов (например, только будни).

~~**4. Аутентификация API**~~ ✅ исправлено  
HTTP Basic Auth через `app/auth.py`, применена ко всем `/api/*` маршрутам через `dependencies=[Depends(require_auth)]` в `app/api/__init__.py`.

~~**5. Rate limiting**~~ ✅ исправлено  
In-memory middleware в `app/main.py`: 120 запросов/минуту на IP для `/api/*` маршрутов (429 при превышении).

~~**6. Шифрование credentials в БД**~~ ✅ исправлено  
`app/crypto.py` — Fernet-шифрование через SQLAlchemy `TypeDecorator` (`EncryptedString`). Поле `api_token` в модели `Account` шифруется/дешифруется прозрачно при чтении/записи. Старые незашифрованные записи возвращаются как есть.

### Желательно

**7. Тест-покрытие**  
Файлы `tests/test_llm.py`, `tests/test_publisher.py`, `tests/test_scheduler.py` существуют, но покрытие минимальное. Нет интеграционных тестов с реальной БД.

**8. Поддержка медиа в постах**  
Модель `Post` и паблишер принимают `media_urls`, но реальная загрузка не реализована ни в одном паблишере.

**9. Multi-user RBAC**  
Система рассчитана на одного admin-пользователя. Поддержка ролей и нескольких пользователей не реализована.

**10. Горизонтальное масштабирование**  
Redis как кэш и брокер упоминается в архитектурной документации для multi-instance деплоя, не реализовано.

---

## Уже исправленные проблемы

- ✅ JSON парсинг через regex с поддержкой markdown code blocks (`post_generator.py:164`)
- ✅ Timezone-aware datetime в retry логике (`datetime.now(timezone.utc)` в моделях и tasks.py)
- ✅ `ActivityLog` импортируется на уровне модуля, не внутри функции
- ✅ Параллельная обработка аккаунтов через `asyncio.gather` в `generate_content_plans`
- ✅ Лимит 10 постов за один запуск публикатора (`.limit(10)` в `publish_scheduled_posts`)
- ✅ LLM клиент — синглтон, не создаётся заново при каждом вызове `PostGenerator`
- ✅ CRON-расписание в `ContentPlanner` (`croniter`, формат `{"cron": "..."}`)
- ✅ HTTP Basic Auth на всех `/api/*` маршрутах (`app/auth.py`)
- ✅ Rate limiting: 120 req/min на IP для `/api/*` (middleware в `app/main.py`)
- ✅ Шифрование `api_token` в БД — Fernet через `EncryptedString` TypeDecorator (`app/crypto.py`)
