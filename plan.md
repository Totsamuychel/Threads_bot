Ты опытный Python-разработчик. Твоя задача — добавить новый publisher в 
существующий проект Threads_bot.

## Структура проекта

Проект уже имеет:
- app/publishers/base.py — абстрактный класс BasePublisher с методами:
  - async publish(account_id, text, hashtags, media_urls) -> PublishResult
  - async health_check() -> bool
  - async get_account_info(account_id) -> Optional[dict]
- app/publishers/mock.py — мок-реализация для тестов
- app/publishers/threads_api.py — реализация через официальный API
- app/publishers/__init__.py — фабрика, создаёт паблишер по THREADS_PUBLISHER из .env
- app/config.py — настройки через pydantic-settings
- .env.example — там уже есть THREADS_PUBLISHER=browser как вариант

## Задача

Создай файл app/publishers/browser_publisher.py — реализацию BasePublisher 
через browser-use + Playwright, которая:

1. Наследует BasePublisher и реализует все три абстрактных метода
2. В методе publish():
   - Запускает Playwright в headless=False (видимый браузер)
   - Использует уже существующую сессию/куки из файла threads_cookies.json 
     (если файл существует), чтобы не логиниться каждый раз
   - Если куки нет — открывает https://www.threads.net и ждёт 60 секунд 
     для ручного логина пользователя, затем сохраняет куки в threads_cookies.json
   - После авторизации:
     a. Переходит на https://www.threads.net
     b. Ищет кнопку создания поста (aria-label содержит "New thread" или "Новая нить")
     c. Кликает по ней
     d. Вводит текст поста через _format_post_text(text, hashtags) — метод уже 
        есть в BasePublisher
     e. Нажимает кнопку публикации (aria-label "Post" или "Опубликовать")
     f. Ждёт подтверждения (URL меняется или появляется toast-уведомление)
   - Возвращает PublishResult(success=True, published_at=datetime.now())
   - При любой ошибке возвращает PublishResult(success=False, error=str(e))

3. В методе health_check() — просто проверяет что playwright установлен 
   (попытка импорта), возвращает bool

4. В методе get_account_info() — возвращает {"status": "browser_mode", 
   "account_id": account_id}

5. Добавь в app/publishers/__init__.py поддержку нового паблишера:
   когда THREADS_PUBLISHER=browser — создаётся BrowserPublisher

6. Добавь в requirements.txt зависимости:
   - browser-use>=1.0.0
   - playwright>=1.40.0

7. Создай конфиг в app/config.py (если нет):
   - THREADS_COOKIES_PATH: str = "threads_cookies.json"
   - BROWSER_HEADLESS: bool = False
   - BROWSER_LOGIN_TIMEOUT: int = 60  # секунды ожидания ручного логина

## Технические детали

- Используй async/await везде (проект уже async — FastAPI)
- Playwright запускай через async_playwright context manager
- Храни browser instance как атрибут класса чтобы не пересоздавать при 
  каждом вызове publish() — инициализируй в отдельном async def initialize()
- Логируй все шаги через стандартный logging (logger = logging.getLogger(__name__))
- Добавь задержки между действиями: asyncio.sleep(1-2 сек) после каждого клика 
  чтобы не триггерить анти-бот защиту Threads

## Что НЕ нужно делать

- Не трогай другие файлы кроме указанных
- Не используй browser-use Agent (только чистый Playwright — надёжнее 
  для конкретного сайта)
- Не добавляй авторизацию через username/password в код (только через куки)

## Пример использования (для понимания контекста)

publisher = BrowserPublisher()
result = await publisher.publish(
    account_id=1,
    text="Привет мир!",
    hashtags=["python", "ai"]
)
print(result.success)  # True

Напиши полный рабочий код для всех изменяемых файлов.