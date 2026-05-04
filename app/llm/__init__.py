"""LLM client factory and exports."""

from app.llm.base import BaseLLMClient, LLMResponse
from app.llm.ollama import OllamaClient
from app.llm.openai_compatible import OpenAICompatibleClient
from app.config import settings
from typing import Optional


# Global client cache
_default_llm_client: Optional[BaseLLMClient] = None


def _create_llm_client(
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None
) -> BaseLLMClient:
    """Internal factory to create a new LLM client."""
    provider = provider or settings.llm_provider
    base_url = base_url or settings.llm_base_url
    api_key = api_key or settings.llm_api_key
    model = model or settings.llm_model
    temperature = temperature if temperature is not None else settings.llm_temperature
    max_tokens = max_tokens or settings.llm_max_tokens
    timeout = timeout or settings.llm_timeout
    
    if provider.lower() == "ollama":
        return OllamaClient(
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
    elif provider.lower() in ["openai", "custom"]:
        return OpenAICompatibleClient(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_llm_client(
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None
) -> BaseLLMClient:
    """
    Factory function to get appropriate LLM client.
    Returns a singleton for default settings.
    """
    # Check if we should return the default singleton
    is_default = (
        provider is None and
        base_url is None and
        api_key is None and
        model is None and
        temperature is None and
        max_tokens is None and
        timeout is None
    )
    
    if is_default:
        global _default_llm_client
        if _default_llm_client is None:
            _default_llm_client = _create_llm_client()
        return _default_llm_client
    
    return _create_llm_client(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )


async def get_llm_client_for_account(account, db) -> BaseLLMClient:
    """
    Get LLM client configured for a specific account.
    Uses account's llm_model and llm_worker_id if set, otherwise falls back to defaults.
    """
    base_url = None
    model = account.llm_model or None
    provider = None
    
    if account.llm_worker_id:
        from sqlalchemy import select
        from app.models.worker import Worker
        result = await db.execute(select(Worker).where(Worker.id == account.llm_worker_id))
        worker = result.scalar_one_or_none()
        if worker and worker.is_online:
            base_url = worker.base_url
            provider = worker.api_type
    
    return get_llm_client(
        provider=provider,
        base_url=base_url,
        model=model,
    )


__all__ = [
    "BaseLLMClient", "LLMResponse", "OllamaClient", "OpenAICompatibleClient",
    "get_llm_client", "get_llm_client_for_account"
]
