"""Tests for LLM clients."""

import pytest
from unittest.mock import AsyncMock, patch
from app.llm import get_llm_client, OllamaClient, OpenAICompatibleClient
from app.llm.base import LLMResponse


@pytest.mark.asyncio
async def test_ollama_client_success():
    """Test successful Ollama generation."""
    client = OllamaClient(
        base_url="http://localhost:11434",
        model="llama2",
        temperature=0.7,
        max_tokens=500,
        timeout=60
    )
    
    # Mock the HTTP response
    mock_response = {
        "response": "This is a test post about AI and coding.",
        "eval_count": 50
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response
        )
        mock_post.return_value.raise_for_status = lambda: None
        
        response = await client.generate(
            prompt="Create a post about AI",
            system_prompt="You are a content creator"
        )
        
        assert response.success
        assert response.text == "This is a test post about AI and coding."
        assert response.tokens_used == 50
        assert response.model == "llama2"


@pytest.mark.asyncio
async def test_ollama_client_timeout():
    """Test Ollama timeout handling."""
    client = OllamaClient(
        base_url="http://localhost:11434",
        model="llama2",
        timeout=1
    )
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = Exception("Timeout")
        
        response = await client.generate(prompt="Test")
        
        assert not response.success
        assert response.error is not None


@pytest.mark.asyncio
async def test_openai_client_success():
    """Test successful OpenAI-compatible generation."""
    client = OpenAICompatibleClient(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=500
    )
    
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": "This is a test post."
                }
            }
        ],
        "usage": {
            "total_tokens": 30
        }
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response
        )
        mock_post.return_value.raise_for_status = lambda: None
        
        response = await client.generate(
            prompt="Create a post",
            system_prompt="You are helpful"
        )
        
        assert response.success
        assert response.text == "This is a test post."
        assert response.tokens_used == 30


def test_get_llm_client_ollama():
    """Test LLM client factory for Ollama."""
    client = get_llm_client(provider="ollama")
    assert isinstance(client, OllamaClient)


def test_get_llm_client_openai():
    """Test LLM client factory for OpenAI."""
    client = get_llm_client(provider="openai")
    assert isinstance(client, OpenAICompatibleClient)


def test_get_llm_client_invalid():
    """Test LLM client factory with invalid provider."""
    with pytest.raises(ValueError):
        get_llm_client(provider="invalid")
