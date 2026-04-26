"""Post generation service using LLM."""

import logging
import json
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Account, ContentPlan, Post
from app.models.content import PostStatus
from app.llm import get_llm_client
from app.config import settings

logger = logging.getLogger(__name__)


class PostGenerator:
    """Service for generating posts using LLM."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_client = get_llm_client()
    
    async def generate_post_for_plan(self, plan_id: int) -> Optional[Post]:
        """
        Generate a post for a content plan.
        
        Args:
            plan_id: ContentPlan ID
            
        Returns:
            Created Post object or None if failed
        """
        # Get content plan
        result = await self.db.execute(
            select(ContentPlan).where(ContentPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            logger.error(f"Content plan {plan_id} not found")
            return None
        
        # Get account
        result = await self.db.execute(
            select(Account).where(Account.id == plan.account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            logger.error(f"Account {plan.account_id} not found")
            return None
        
        # Update plan status
        plan.status = PostStatus.GENERATING
        await self.db.commit()
        
        try:
            # Build prompts
            system_prompt = self._build_system_prompt(account)
            user_prompt = self._build_user_prompt(account, plan)
            
            logger.info(f"Generating post for plan {plan_id}: {plan.topic}")
            
            # Generate with LLM
            response = await self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=plan.llm_temperature,
                max_tokens=plan.llm_max_tokens
            )
            
            if not response.success:
                logger.error(f"LLM generation failed: {response.error}")
                plan.status = PostStatus.FAILED
                await self.db.commit()
                return None
            
            # Parse response
            post_data = self._parse_llm_response(response.text, account)
            
            # Create post
            post = Post(
                account_id=account.id,
                content_plan_id=plan.id,
                text=post_data["text"],
                hashtags=post_data["hashtags"],
                llm_prompt=user_prompt,
                llm_system_prompt=system_prompt,
                llm_raw_response=response.text,
                llm_model_used=response.model,
                generation_time_seconds=int(response.generation_time) if response.generation_time else None,
                scheduled_time=plan.scheduled_time,
                status=PostStatus.GENERATED
            )
            
            self.db.add(post)
            
            # Update plan status
            plan.status = PostStatus.GENERATED
            
            await self.db.commit()
            
            logger.info(f"Successfully generated post {post.id} for plan {plan_id}")
            return post
            
        except Exception as e:
            logger.error(f"Error generating post: {str(e)}")
            plan.status = PostStatus.FAILED
            await self.db.commit()
            return None
    
    def _build_system_prompt(self, account: Account) -> str:
        """Build system prompt from account configuration."""
        return f"""You are a social media content creator for Threads.

Target Audience: {account.target_audience or 'general audience'}
Tone of Voice: {account.tone or 'friendly and engaging'}
Language: {account.language or 'en'}

Guidelines:
- Keep posts short and engaging ({account.min_length}-{account.max_length} characters)
- Mobile-friendly formatting
- Be authentic and conversational
- Focus on providing value to the audience
- Use line breaks for readability
- Avoid overly promotional language

You will be given a topic and should create an engaging post about it."""
    
    def _build_user_prompt(self, account: Account, plan: ContentPlan) -> str:
        """Build user prompt for specific content plan."""
        prompt = f"""Create a Threads post about: {plan.topic}

Requirements:
- Length: {account.min_length}-{account.max_length} characters
- Tone: {account.tone or 'engaging and authentic'}
- Target audience: {account.target_audience or 'general'}
- Language: {account.language or 'en'}"""
        
        if plan.specific_idea:
            prompt += f"\n- Specific angle: {plan.specific_idea}"
        
        if account.auto_generate_hashtags:
            prompt += f"\n- Include {account.max_hashtags or '3-5'} relevant hashtags"
        
        prompt += """

Return your response in JSON format:
{
  "text": "your post content here",
  "hashtags": ["tag1", "tag2", "tag3"]
}

Make the post engaging, valuable, and authentic. Focus on quality over quantity."""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str, account: Account) -> dict:
        """Parse LLM response to extract post data."""
        try:
            # Try to parse as JSON first
            # Look for JSON in the response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                data = json.loads(json_str)
                
                text = data.get("text", "")
                hashtags = data.get("hashtags", [])
                
                # Add base hashtags
                if account.base_hashtags:
                    hashtags.extend(account.base_hashtags)
                
                # Remove duplicates and limit
                hashtags = list(dict.fromkeys(hashtags))[:account.max_hashtags or 10]
                
                return {
                    "text": text,
                    "hashtags": hashtags
                }
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from LLM response, using raw text")
        
        # Fallback: use raw text
        return {
            "text": response_text,
            "hashtags": account.base_hashtags or []
        }
