"""
VisionAgent — использует Qwen VL через Ollama чтобы «видеть» браузер
и возвращать координаты нужных элементов по текстовому описанию.
"""

import base64
import json
import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_FIND_PROMPT = """\
This is a screenshot of a web browser showing the Threads social network.
The image resolution is {w}x{h} pixels.

Your task: find the UI element described below and return its CENTER coordinates.

Element to find: {description}

Rules:
- Respond with ONLY a valid JSON object, nothing else.
- Format: {{"x": <integer>, "y": <integer>}}
- x must be between 0 and {w}, y must be between 0 and {h}.
- If the element is not visible, respond: {{"x": null, "y": null}}
"""

_VERIFY_PROMPT = """\
This is a screenshot of a web browser showing the Threads social network.

Question: {question}
Answer with ONLY "yes" or "no".
"""


class VisionAgent:
    """
    Смотрит на скриншот браузера через Qwen VL и возвращает координаты элементов.
    Не зависит от CSS-селекторов, aria-label или языка интерфейса.
    """

    def __init__(self, model: str, base_url: str, timeout: int = 60) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    async def find(
        self,
        page,
        description: str,
        viewport_w: int = 1366,
        viewport_h: int = 768,
    ) -> Optional[tuple[float, float]]:
        """
        Делает скриншот страницы, спрашивает у Qwen VL координаты элемента.
        Возвращает (x, y) или None если элемент не найден.
        """
        screenshot_b64 = await self._screenshot_b64(page)
        prompt = _FIND_PROMPT.format(
            w=viewport_w, h=viewport_h, description=description
        )

        for attempt in range(2):
            try:
                raw = await self._ask(prompt, screenshot_b64)
                coords = self._parse_coords(raw)
                if coords:
                    x, y = coords
                    # Убеждаемся что координаты в пределах экрана
                    if 0 <= x <= viewport_w and 0 <= y <= viewport_h:
                        logger.debug(
                            "VisionAgent нашёл '%s' → (%d, %d)", description, x, y
                        )
                        return x, y
                    logger.warning(
                        "VisionAgent вернул координаты вне экрана: %s", raw
                    )
                else:
                    logger.warning(
                        "VisionAgent не распознал координаты (attempt %d): %s",
                        attempt + 1, raw[:120],
                    )
            except Exception as e:
                logger.error("VisionAgent ошибка (attempt %d): %s", attempt + 1, e)

        return None

    async def verify(self, page, question: str) -> bool:
        """
        Делает скриншот и задаёт yes/no вопрос.
        Например: "Is the post published successfully?"
        """
        screenshot_b64 = await self._screenshot_b64(page)
        prompt = _VERIFY_PROMPT.format(question=question)
        try:
            raw = await self._ask(prompt, screenshot_b64)
            return raw.strip().lower().startswith("yes")
        except Exception as e:
            logger.error("VisionAgent verify ошибка: %s", e)
            return False

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    @staticmethod
    async def _screenshot_b64(page) -> str:
        data = await page.screenshot(type="png")
        return base64.b64encode(data).decode()

    async def _ask(self, prompt: str, image_b64: str) -> str:
        """Отправляет запрос в Ollama chat API с изображением."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [image_b64],
                        }
                    ],
                },
            )
            r.raise_for_status()
            return r.json()["message"]["content"].strip()

    @staticmethod
    def _parse_coords(text: str) -> Optional[tuple[float, float]]:
        """Извлекает {"x": ..., "y": ...} из ответа модели."""
        # Убираем markdown-блоки если есть
        text = re.sub(r"```[a-z]*\s*", "", text).strip()

        # Ищем JSON-объект
        match = re.search(r'\{[^}]+\}', text)
        if not match:
            return None
        try:
            data = json.loads(match.group())
            x = data.get("x")
            y = data.get("y")
            if x is None or y is None:
                return None
            return float(x), float(y)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
