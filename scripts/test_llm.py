#!/usr/bin/env python
"""Script to test LLM connection and generation."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.llm import get_llm_client
from app.config import settings


async def test_llm():
    """Test LLM connection and generation."""
    
    print(f"Testing LLM connection...")
    print(f"Provider: {settings.llm_provider}")
    print(f"Base URL: {settings.llm_base_url}")
    print(f"Model: {settings.llm_model}")
    print("-" * 80)
    
    # Get client
    client = get_llm_client()
    
    # Health check
    print("\n1. Health Check...")
    is_healthy = await client.health_check()
    
    if is_healthy:
        print("✅ LLM service is reachable")
    else:
        print("❌ LLM service is not reachable")
        print("\nTroubleshooting:")
        print("- Check if Ollama is running: ollama serve")
        print("- Verify LLM_BASE_URL in .env")
        print("- Try: curl http://localhost:11434/api/tags")
        return
    
    # Test generation
    print("\n2. Testing Generation...")
    
    system_prompt = """You are a social media content creator for Threads.
Target Audience: developers and tech enthusiasts
Tone: casual, witty, educational
Language: en

Create engaging, valuable content."""
    
    user_prompt = """Create a short Threads post about: Python coding tips

Requirements:
- Length: 150-300 characters
- Include 3 relevant hashtags
- Be engaging and practical

Return JSON format:
{
  "text": "your post here",
  "hashtags": ["tag1", "tag2", "tag3"]
}"""
    
    print(f"\nGenerating post...")
    response = await client.generate(
        prompt=user_prompt,
        system_prompt=system_prompt
    )
    
    if response.success:
        print("✅ Generation successful!")
        print(f"\nGenerated Content:")
        print("-" * 80)
        print(response.text)
        print("-" * 80)
        print(f"\nMetadata:")
        print(f"  Model: {response.model}")
        print(f"  Tokens: {response.tokens_used}")
        print(f"  Time: {response.generation_time:.2f}s")
    else:
        print(f"❌ Generation failed: {response.error}")
        print("\nTroubleshooting:")
        print("- Check if model is installed: ollama list")
        print(f"- Pull model: ollama pull {settings.llm_model}")
        print("- Try a different model in .env")


if __name__ == "__main__":
    asyncio.run(test_llm())
