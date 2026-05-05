✅ КРИТИЧНО — app/config.py: Небезопасные дефолты в production
python
secret_key: str = "change-me-in-production"  # в production пойдёт этот ключ!
debug: bool = True                            # трассировки стека видны пользователям
admin_password: str = "changeme"             # захардкоженный пароль
Все три значения — это defaults, которые будут использованы если .env не задан. При деплое без настройки — immediate security breach.

Решение: сделать их обязательными полями без default:

python
secret_key: str  # обязателен, упадёт при запуске если не задан
debug: bool = False  # безопасный дефолт
admin_password: str  # обязателен
✅ ВАЖНО — app/services/post_generator.py: Новый LLM-клиент на каждый инстанс
python
class PostGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_client = get_llm_client()  # ← создаётся при каждом вызове PostGenerator(db)
PostGenerator создаётся в каждой задаче планировщика. Если get_llm_client() создаёт новое HTTP-соединение или устанавливает сессию — это накладно. LLM-клиент должен быть синглтоном или инжектироваться через DI.

python
# Лучше: внедрить через FastAPI Depends или как синглтон
_llm_client: Optional[BaseLLMClient] = None

def get_llm_client() -> BaseLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = _create_client()
    return _llm_client
✅ ВАЖНО — app/services/post_generator.py: Ненадёжный парсинг JSON из LLM
python
def _parse_llm_response(self, response_text: str, account) -> dict:
    start_idx = response_text.find("{")
    end_idx = response_text.rfind("}") + 1
    json_str = response_text[start_idx:end_idx]
    data = json.loads(json_str)
Проблема: если LLM вернёт текст вида {"text": "Check {this} out", "hashtags": []}, rfind("}") найдёт закрывающую скобку строки "Check {this} out", а не JSON-объекта. Также если LLM оборачивает ответ в markdown-блок ````json ... ` `` `` `, `find("{")` пропустит его.

Лучший подход:

python
import re
# Сначала попробовать markdown code block
match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
json_str = match.group(1) if match else response_text
try:
    return json.loads(json_str)
except json.JSONDecodeError:
    # fallback к сырому тексту
✅ ВАЖНО — app/scheduler/tasks.py: Нет лимита на количество постов за один запуск
python
result = await db.execute(
    select(Post).where(
        and_(Post.status.in_([PostStatus.GENERATED, PostStatus.SCHEDULED]),
             Post.scheduled_time <= now)
    ).order_by(Post.scheduled_time)
)
posts = result.scalars().all()  # ← берёт ВСЕ посты сразу
Если накопится 100+ просроченных постов (например, после простоя), все 100 будут отправлены сразу, что может привести к rate limit со стороны Threads API.

Решение: добавить .limit(10) и обрабатывать батчами.

✅ ВАЖНО — app/scheduler/tasks.py: Последовательная обработка аккаунтов
python
for account in accounts:
    plans = await planner.generate_plan_for_account(account.id)
При 10+ аккаунтах это занимает время пропорционально количеству аккаунтов × время LLM-генерации. Можно параллелизировать:

python
tasks = [planner.generate_plan_for_account(a.id) for a in accounts]
results = await asyncio.gather(*tasks, return_exceptions=True)
✅ ВАЖНО — app/scheduler/tasks.py: from app.models import ActivityLog внутри функции
python
async def cleanup_old_logs():
    async with AsyncSessionLocal() as db:
        try:
            from app.models import ActivityLog  # ← импорт внутри функции
Импорт должен быть в начале файла. Это не вызывает ошибку, но нарушает конвенцию и усложняет читабельность.

✅ ВАЖНО — Timezone-inconsistency в retry логике
В tasks.py используется datetime.now(timezone.utc), но post.updated_at может быть naive datetime если модель не настроена с timezone-aware. Тогда вычитание datetime.now(timezone.utc) - post.updated_at выбросит TypeError.

Убедиться, что в модели Post.updated_at использует onupdate=lambda: datetime.now(timezone.utc) с timezone-aware datetime.
Устаревший API Mixed Precision :

python
# УСТАРЕЛО (deprecated в PyTorch 2.4):
from torch.cuda.amp import GradScaler, autocast

# ПРАВИЛЬНО для современного PyTorch:
from torch.amp import GradScaler, autocast
scaler = GradScaler("cuda")
with autocast("cuda", enabled=use_amp):
    ...
import shutil внутри метода :

python
# ПЛОХО — в CheckpointManager.save():
import shutil
shutil.copy2(best_checkpoint[1], best_path)

# ЛУЧШЕ — вынести вверх файла
early_stop.counter = 0 и early_stop.should_stop = False при сбросе между стадиями — прямой доступ к внутренним атрибутам. Лучше добавить метод:

python
def reset(self):
    """Сброс счётчика между стадиями обучения."""
    self.counter = 0
    self.should_stop = False
    self.best_value = None
Архитектурное нарушение — функции train_one_epoch и validate принимают architecture: str и меняют поведение через if architecture == "geoclip" . Это нарушает принцип Open/Closed. Лучше использовать полиморфизм: общий интерфейс модели с методом compute_loss(batch).

Нет тестовой выборки — только train и val. После обучения нет финальной оценки на test set. По правилам ML: val используется для выбора гиперпараметров, test — для финального отчёта.

Использование Tuple из typing — устарело в Python 3.9+:

python
# УСТАРЕЛО:
from typing import Tuple
def get_train_transforms(random_crop_scale: Tuple[float, float]):

# СОВРЕМЕННЫЙ СТИЛЬ (Python 3.9+):
def get_train_transforms(random_crop_scale: tuple[float, float]):
get_tta_transforms может молча вернуть меньше трансформаций чем запрошено :

python
# Если n_augmentations=1, список scales не заполняется
# и возвращается только base transform — без предупреждения
Добавить явную проверку или assertion:

python
assert len(tta_list) == n_augmentations, f"TTA: expected {n_augmentations}, got {len(tta_list)}"
RandomHorizontalFlip(p=1.0) в TTA — технически работает, но семантически это не RandomHorizontalFlip, а HorizontalFlip. Можно использовать transforms.functional.hflip для ясности.
