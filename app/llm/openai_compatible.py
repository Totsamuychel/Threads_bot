"""OpenAI-compatible API client implementation."""

import httpx
import time
from typing import Optional
from app.llm.base import BaseLLMClient, LLMResponse


class OpenAICompatibleClient(BaseLLMClient):
    """Client for OpenAI-compatible APIs (OpenAI, Azure, local servers, etc.)."""
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                      temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> LLMResponse:
        """Generate text using OpenAI-compatible API."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Build messages
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # Build request payload
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self._get_temperature(temperature),
                    "max_tokens": self._get_max_tokens(max_tokens),
                }
                
                # Build headers
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                # Make request
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                generation_time = time.time() - start_time
                
                # Extract text from response
                text = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens")
                
                return LLMResponse(
                    text=text,
                    model=self.model,
                    tokens_used=tokens_used,
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
        """Check if API is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                return response.status_code == 200
        except Exception:
            return False
