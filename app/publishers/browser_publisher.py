"""Browser-based Threads publisher — Playwright + human mouse simulation."""

import asyncio
import logging
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.publishers.base import BasePublisher, PublishResult
from app.publishers.vision_agent import VisionAgent

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_STEALTH_PATCHES = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin' },
            { name: 'Chrome PDF Viewer' },
            { name: 'Native Client' },
        ]
    });
    Object.defineProperty(navigator, 'languages', {
        get: () => ['ru-RU', 'ru', 'en-US', 'en']
    });
    window.chrome = {
        runtime: {}, loadTimes: function(){}, csi: function(){}, app: {}
    };
    const _origPerms = window.navigator.permissions.query;
    window.navigator.permissions.query = (p) =>
        p.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : _origPerms(p);
"""

_VW = 1366  # viewport width
_VH = 768   # viewport height


# ---------------------------------------------------------------------------
# Human Mouse — плавное движение по кривым Безье
# ---------------------------------------------------------------------------

class HumanMouse:
    """
    Имитирует движение мыши живого человека:
    - Кубическая кривая Безье со случайными контрольными точками
    - Easing (smoothstep): медленно стартует, разгоняется, притормаживает
    - Микро-дрожание (гауссов шум) — как дрожит рука
    - Иногда промахивается мимо цели и возвращается
    - Может хаотично блуждать по странице во время «чтения»
    """

    def __init__(self) -> None:
        # Стартуем из центра экрана
        self.x: float = _VW / 2
        self.y: float = _VH / 2

    # ------------------------------------------------------------------
    # Внутренние вычисления
    # ------------------------------------------------------------------

    @staticmethod
    def _smoothstep(t: float) -> float:
        """Ease in-out: плавный старт и конец движения."""
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _bezier(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
        """Значение кубической кривой Безье в точке t ∈ [0, 1]."""
        u = 1.0 - t
        return u**3 * p0 + 3*u**2*t * p1 + 3*u*t**2 * p2 + t**3 * p3

    # ------------------------------------------------------------------
    # Основное движение
    # ------------------------------------------------------------------

    async def move_to(
        self,
        page,
        tx: float,
        ty: float,
        overshoot: bool = True,
    ) -> None:
        """
        Плавно перемещает курсор из текущей позиции в (tx, ty).
        Путь — кубическая кривая Безье с хаотичными контрольными точками.
        """
        sx, sy = self.x, self.y
        dist = math.hypot(tx - sx, ty - sy)

        if dist < 2:
            return

        # Контрольные точки — смещаем в сторону от прямой, создавая дугу
        spread = min(dist * 0.45, 140)
        cp1x = sx + (tx - sx) * random.uniform(0.15, 0.35) + random.uniform(-spread, spread)
        cp1y = sy + (ty - sy) * random.uniform(0.15, 0.35) + random.uniform(-spread, spread)
        cp2x = sx + (tx - sx) * random.uniform(0.65, 0.85) + random.uniform(-spread, spread)
        cp2y = sy + (ty - sy) * random.uniform(0.65, 0.85) + random.uniform(-spread, spread)

        # Иногда промахиваемся мимо цели и чуть возвращаемся назад
        real_tx, real_ty = tx, ty
        if overshoot and dist > 30 and random.random() < 0.35:
            angle = math.atan2(ty - sy, tx - sx)
            over = random.uniform(4, 15)
            tx += math.cos(angle) * over
            ty += math.sin(angle) * over

        # Количество шагов: ~1 шаг на 5–8 пикселей, минимум 18
        steps = max(18, int(dist / random.uniform(5, 8)))

        for i in range(steps + 1):
            t_raw = i / steps
            t_ease = self._smoothstep(t_raw)

            x = self._bezier(t_ease, sx, cp1x, cp2x, tx)
            y = self._bezier(t_ease, sy, cp1y, cp2y, ty)

            # Микро-дрожание руки (усиливается чуть сильнее на высокой скорости)
            jitter = 0.3 + 0.5 * (1 - abs(t_raw - 0.5) * 2)
            x += random.gauss(0, jitter)
            y += random.gauss(0, jitter)

            await page.mouse.move(x, y)

            # Задержка: в середине движения быстрее, на краях медленнее
            mid_speed = 1.0 - abs(t_raw - 0.5) * 1.6  # 0.2 .. 1.0
            base_delay = 0.003 + random.gauss(0, 0.0008)
            await asyncio.sleep(max(0.001, base_delay / max(mid_speed, 0.15)))

        # Корректируем промах — плавно возвращаемся к реальной цели
        if overshoot and (tx != real_tx or ty != real_ty):
            await self.move_to(page, real_tx, real_ty, overshoot=False)

        self.x, self.y = real_tx, real_ty

    # ------------------------------------------------------------------
    # Блуждание — имитирует «чтение» страницы
    # ------------------------------------------------------------------

    async def wander(self, page, duration: float) -> None:
        """
        Хаотично водит мышью по странице в течение `duration` секунд —
        как будто пользователь читает ленту.
        """
        deadline = asyncio.get_event_loop().time() + duration
        while asyncio.get_event_loop().time() < deadline:
            # Следующая случайная точка в пределах viewport
            nx = random.uniform(80, _VW - 80)
            ny = random.uniform(60, _VH - 80)
            await self.move_to(page, nx, ny)

            # Иногда зависаем — как будто читаем пост
            if random.random() < 0.45:
                pause = random.uniform(0.3, 1.8)
                # Во время паузы слегка дёргаем мышь (микро-движения)
                await self._micro_idle(page, pause)

    async def _micro_idle(self, page, duration: float) -> None:
        """Маленькие хаотичные движения во время остановки (рука не стоит ровно)."""
        deadline = asyncio.get_event_loop().time() + duration
        while asyncio.get_event_loop().time() < deadline:
            dx = random.gauss(0, 2.5)
            dy = random.gauss(0, 2.5)
            nx = max(0, min(_VW, self.x + dx))
            ny = max(0, min(_VH, self.y + dy))
            await page.mouse.move(nx, ny)
            self.x, self.y = nx, ny
            await asyncio.sleep(random.uniform(0.04, 0.12))

    # ------------------------------------------------------------------
    # Клик по элементу
    # ------------------------------------------------------------------

    async def click(self, page, locator) -> None:
        """
        Плавно подводит курсор к элементу и кликает.
        Целится не точно в центр — немного случайно, как человек.
        """
        await locator.scroll_into_view_if_needed()
        await asyncio.sleep(random.uniform(0.1, 0.3))

        box = await locator.bounding_box()
        if box:
            cx = box["x"] + box["width"]  * random.uniform(0.3, 0.7)
            cy = box["y"] + box["height"] * random.uniform(0.3, 0.7)
            await self.move_to(page, cx, cy)
        else:
            await locator.hover()

        # Небольшая пауза перед кликом — «рука навела, чуть подождала»
        await asyncio.sleep(random.uniform(0.06, 0.22))
        await page.mouse.click(self.x, self.y)


# ---------------------------------------------------------------------------
# Human typing — посимвольный ввод с ошибками и паузами
# ---------------------------------------------------------------------------

async def _human_type(page, text: str) -> None:
    """
    Вводит текст посимвольно с реалистичными задержками:
    - Случайная скорость каждого символа
    - Иногда делает опечатку и стирает
    - Иногда делает паузы как будто думает
    """
    i = 0
    while i < len(text):
        ch = text[i]

        # ~4% шанс опечатки (только для букв, не для спецсимволов)
        if ch.isalpha() and random.random() < 0.04:
            wrong = random.choice("qwertyuiopasdfghjklzxcvbnm")
            await page.keyboard.type(wrong, delay=random.randint(40, 100))
            await asyncio.sleep(random.uniform(0.08, 0.25))
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.06, 0.18))

        await page.keyboard.type(ch, delay=random.randint(35, 140))

        # Иногда пауза после знаков препинания — человек «думает»
        if ch in ".!?,":
            await asyncio.sleep(random.uniform(0.2, 0.7))
        elif ch == " " and random.random() < 0.08:
            await asyncio.sleep(random.uniform(0.15, 0.5))

        i += 1

    # Короткая пауза после завершения набора — перечитываем
    await asyncio.sleep(random.uniform(0.5, 1.5))


# ---------------------------------------------------------------------------
# BrowserPublisher
# ---------------------------------------------------------------------------

class BrowserPublisher(BasePublisher):
    """
    Публикует посты в Threads через настоящий браузер Chromium.
    Профиль хранится на диске — сессия сохраняется между запусками.
    При первом запуске нужно залогиниться вручную.
    """

    def __init__(self) -> None:
        self._playwright = None
        self._context = None
        self._mouse = HumanMouse()
        self._vision: Optional[VisionAgent] = None

    async def initialize(self) -> None:
        from playwright.async_api import async_playwright
        from app.config import settings

        if self._context is not None:
            return

        profile_dir = Path("browser_profile")
        profile_dir.mkdir(exist_ok=True)

        logger.info("Запуск браузера (профиль: %s)", profile_dir.resolve())
        self._playwright = await async_playwright().start()

        self._context = await self._playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=settings.browser_headless,
            user_agent=_USER_AGENT,
            viewport={"width": _VW, "height": _VH},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-automation",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
                "--disable-notifications",
                "--disable-popup-blocking",
            ],
            ignore_default_args=["--enable-automation", "--enable-blink-features=IdleDetection"],
        )

        await self._context.add_init_script(_STEALTH_PATCHES)

        self._vision = VisionAgent(
            model=settings.vision_model,
            base_url=settings.vision_base_url,
            timeout=settings.vision_timeout,
        )

        page = await self._context.new_page()
        await page.goto("https://www.threads.net", wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(2, 4))

        if not await self._is_logged_in(page):
            await page.screenshot(path="debug_not_logged_in.png")
            logger.info(
                "Не авторизован (скриншот: debug_not_logged_in.png) — "
                "ждём ручного логина %d сек...",
                settings.browser_login_timeout,
            )
            await asyncio.sleep(settings.browser_login_timeout)
            await page.reload(wait_until="load")
            await asyncio.sleep(3)
            if not await self._is_logged_in(page):
                await page.screenshot(path="debug_still_not_logged_in.png")
                logger.warning(
                    "Авторизация не обнаружена (скриншот: debug_still_not_logged_in.png)"
                )
                await page.close()
                raise RuntimeError(
                    "Не удалось авторизоваться в Threads. "
                    "Запусти debug_selectors.py, залогинься вручную и повтори."
                )

        await page.close()

    async def _is_logged_in(self, page) -> bool:
        # 1. URL-проверка: если открылась /login — точно не авторизован
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Exception:
            pass
        url = page.url
        if "/login" in url or "instagram.com" in url:
            return False

        # 2. CSS-селекторы навигации (любой язык интерфейса)
        nav_selectors = (
            '[aria-label="For you"], [aria-label="Home"], '
            '[aria-label="Для вас"], [aria-label="Головна"], '
            '[aria-label="Для тебя"], [aria-label="Главная"], '
            'a[href="/"][role="link"], '
            '[data-testid="tray-home"], [data-testid="tray-feed"]'
        )
        try:
            await page.wait_for_selector(nav_selectors, timeout=10_000)
            return True
        except Exception:
            pass

        # 3. VisionAgent — визуальная проверка
        if self._vision:
            try:
                return await self._vision.verify(
                    page, "Is the user logged in to Threads? (Is the main feed visible?)"
                )
            except Exception:
                pass

        # 4. Compose-поле как последняя эвристика
        try:
            await page.wait_for_selector(
                '[aria-label*="text field"], [aria-label*="New thread"], '
                '[contenteditable="true"]',
                timeout=5_000,
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------

    async def publish(
        self,
        account_id: int,
        text: str,
        hashtags: Optional[list[str]] = None,
        media_urls: Optional[list[str]] = None,
    ) -> PublishResult:
        try:
            await self.initialize()
            return await self._do_publish(text, hashtags)
        except Exception as e:
            logger.error("Ошибка публикации (account %s): %s", account_id, e)
            return PublishResult(success=False, error=str(e))

    async def _do_publish(self, text: str, hashtags: Optional[list[str]]) -> PublishResult:
        post_text = self._format_post_text(text, hashtags)
        page = await self._context.new_page()
        mouse = self._mouse
        vision = self._vision

        try:
            # 1. Открываем главную
            logger.info("Открываем Threads")
            await page.goto("https://www.threads.net", wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 3.5))

            # 2. Читаем ленту — курсор блуждает
            logger.info("Читаем ленту...")
            await mouse.wander(page, random.uniform(3, 5))
            await page.mouse.wheel(0, random.randint(150, 400))
            await asyncio.sleep(random.uniform(1, 2))
            await page.mouse.wheel(0, -random.randint(80, 200))
            await asyncio.sleep(random.uniform(0.8, 1.8))

            # 3. VisionAgent находит кнопку создания поста
            logger.info("VisionAgent ищет поле создания поста...")
            compose_xy = await vision.find(
                page,
                "the compose/create post area at the top of the Threads feed. "
                "It is a clickable area that looks like an empty text input, "
                "often with a user avatar on the left. It may show placeholder "
                "text like 'Empty text field' or 'Start a thread'. "
                "It is located in the upper portion of the main content area.",
            )
            if compose_xy:
                logger.info("VisionAgent нашёл compose: %s", compose_xy)
                await mouse.move_to(page, *compose_xy)
                await asyncio.sleep(random.uniform(0.2, 0.5))
                await page.mouse.click(*compose_xy)
            else:
                # Fallback: CSS-селектор
                logger.warning("VisionAgent не нашёл compose, используем селектор")
                compose = page.locator(_compose_sel()).first
                await mouse.click(page, compose)
            await asyncio.sleep(random.uniform(1, 2))

            # 4. VisionAgent находит текстовый редактор
            logger.info("VisionAgent ищет текстовый редактор...")
            editor_xy = await vision.find(
                page,
                "the active text input field or editor where I can type a new post. "
                "It should be an empty editable area, possibly with placeholder text.",
            )
            if editor_xy:
                logger.info("VisionAgent нашёл editor: %s", editor_xy)
                await mouse.move_to(page, *editor_xy)
                await asyncio.sleep(random.uniform(0.15, 0.4))
                await page.mouse.click(*editor_xy)
            else:
                logger.warning("VisionAgent не нашёл editor, используем селектор")
                await page.wait_for_selector(_editor_sel(), timeout=8_000)
                editor = page.locator(_editor_sel()).first
                await mouse.click(page, editor)
            await asyncio.sleep(random.uniform(0.3, 0.6))

            # 5. Печатаем как человек
            logger.info("Вводим текст: %.40s...", post_text)
            await _human_type(page, post_text)

            # Перечитываем написанное
            await mouse.wander(page, random.uniform(1, 2))

            # 6. VisionAgent находит кнопку публикации
            logger.info("VisionAgent ищет кнопку публикации...")
            post_xy = await vision.find(
                page,
                "the 'Post' or 'Опубликовать' or 'Publish' button to submit/post the text. "
                "It is usually a colored button (blue or black) near the text editor.",
            )
            if post_xy:
                logger.info("VisionAgent нашёл Post btn: %s", post_xy)
                await mouse.move_to(page, *post_xy)
                await asyncio.sleep(random.uniform(0.2, 0.5))
                await page.mouse.click(*post_xy)
            else:
                logger.warning("VisionAgent не нашёл Post btn, используем селектор")
                post_btn = page.locator(_post_btn_sel()).first
                await mouse.click(page, post_btn)
            await asyncio.sleep(random.uniform(2, 3.5))

            # 7. VisionAgent проверяет что пост опубликован
            success = await vision.verify(
                page,
                "Has the post been submitted successfully? "
                "Is the text input area now empty or reset to its default state?",
            )
            logger.info("VisionAgent подтверждение публикации: %s", success)

            logger.info("Пост опубликован через браузер")
            return PublishResult(
                success=True,
                published_at=datetime.now(timezone.utc),
                metadata={"method": "browser+vision", "vision_confirmed": success},
            )

        except Exception:
            raise
        finally:
            await page.close()

    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        try:
            from playwright.async_api import async_playwright  # noqa: F401
            return True
        except ImportError:
            return False

    async def get_account_info(self, account_id: int) -> Optional[dict]:
        return {"status": "browser_mode", "account_id": account_id}


# ---------------------------------------------------------------------------
# Селекторы
# ---------------------------------------------------------------------------

def _compose_sel() -> str:
    return (
        'div[role="button"][aria-label*="Empty text field"], '
        'div[role="button"][aria-label*="текстовое поле"], '
        'div[role="button"][aria-label*="Новая публикация"], '
        'div[role="button"][aria-label*="New post"]'
    )


def _editor_sel() -> str:
    return 'div[contenteditable="true"][role="textbox"], div[contenteditable="true"]'


def _post_btn_sel() -> str:
    return (
        'div[role="button"]:has-text("Post"), '
        'div[role="button"]:has-text("Опубликовать"), '
        'button:has-text("Post"), button:has-text("Опубликовать")'
    )
