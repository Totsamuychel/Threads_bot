"""Ollama LLM client implementation."""

import httpx
import time
from typing import Optional
from app.llm.base import BaseLLMClient, LLMResponse


class OllamaClient(BaseLLMClient):
    """Client for Ollama local LLM server."""
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                      temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> LLMResponse:
        """Generate text using Ollama API."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Build request payload
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self._get_temperature(temperature),
                        "num_predict": self._get_max_tokens(max_tokens),
                    }
                }
                
                # Add system prompt if provided
                if system_prompt:
                    payload["system"] = system_prompt
                
                # Make request
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                generation_time = time.time() - start_time
                
                return LLMResponse(
                    text=data.get("response", ""),
                    model=self.model,
                    tokens_used=data.get("eval_count"),
                    generation_time=generation_time,
                    raw_response=data
                )
                
        except httpx.TimeoutException:
            return LLMResponse(
                text="",
                model=self.model,
                generation_time=time.time() - start_time,
                error=f"Request timeout after {self.timeout} seconds"
            )
        except httpx.HTTPStatusError as e:
            return LLMResponse(
                text="",
                model=self.model,
                generation_time=time.time() - start_time,
                error=f"HTTP error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            return LLMResponse(
                text="",
                model=self.model,
                generation_time=time.time() - start_time,
                error=f"Unexpected error: {str(e)}"
            )
    
    async def health_check(self) -> bool:
        """Check if Ollama server is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
