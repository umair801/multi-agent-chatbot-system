import logging
import os
from typing import Optional
from openai import AsyncOpenAI
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class LLMProvider:
    """
    Abstraction layer for LLM calls with fallback strategy
    Primary: GPT-4o
    Fallback: Claude API
    """
    
    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o')
        
        self.openai_client = AsyncOpenAI(api_key=self.openai_key) if self.openai_key else None
        self.anthropic_client = Anthropic(api_key=self.anthropic_key) if self.anthropic_key else None
    
    async def plan_execution(self, goal: str, context: str = '') -> dict:
        """
        Use GPT-4o to create a step-by-step execution plan for the goal
        Returns: {'steps': [...], 'reasoning': '...'}
        """
        prompt = f"""You are an autonomous AI agent planning system. A user has provided a goal.
Your task is to break down this goal into concrete, executable steps.

For each step, specify:
1. step_number (1, 2, 3, ...)
2. agent_type (one of: web_search, browser_use, rag, file_generation, code_execution, summarization)
3. action (what the agent should do)
4. inputs (what data/context it needs)

Goal: {goal}
Context: {context if context else 'None provided'}

Return your response as JSON in this format:
{{
  "steps": [
    {{"step_number": 1, "agent_type": "...", "action": "...", "inputs": {{}}}},
    ...
  ],
  "reasoning": "Why this plan makes sense"
}}

Be concise. Use exactly the agent types listed. No extra fields."""
        
        try:
            if not self.openai_client:
                logger.warning('OpenAI client not initialized, using Claude fallback')
                return await self._plan_with_claude(prompt)
            
            response = await self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {'role': 'system', 'content': 'You are a planning agent that creates execution plans. Return only valid JSON.'},
                    {'role': 'user', 'content': prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            logger.info(f'Plan generated with GPT-4o')
            
            import json
            plan_data = json.loads(content)
            return plan_data
        
        except Exception as e:
            logger.error(f'GPT-4o planning failed: {str(e)}, falling back to Claude')
            return await self._plan_with_claude(prompt)
    
    async def _plan_with_claude(self, prompt: str) -> dict:
        """
        Fallback: Use Claude API for planning
        """
        try:
            if not self.anthropic_client:
                logger.error('Claude client not initialized')
                return {'steps': [], 'reasoning': 'No LLM available'}
            
            response = self.anthropic_client.messages.create(
                model='claude-3-5-sonnet-20241022',
                max_tokens=1000,
                messages=[
                    {'role': 'user', 'content': prompt}
                ]
            )
            
            content = response.content[0].text
            logger.info('Plan generated with Claude (fallback)')
            
            import json
            plan_data = json.loads(content)
            return plan_data
        
        except Exception as e:
            logger.error(f'Claude planning also failed: {str(e)}')
            return {'steps': [], 'reasoning': 'LLM planning failed'}
    
    async def summarize(self, text: str, max_length: int = 500) -> str:
        """
        Use Claude for summarization (it's better at this)
        """
        try:
            if not self.anthropic_client:
                logger.warning('Claude not available for summarization')
                return text[:max_length]
            
            response = self.anthropic_client.messages.create(
                model='claude-3-5-sonnet-20241022',
                max_tokens=max_length,
                messages=[
                    {
                        'role': 'user',
                        'content': f'Summarize this text concisely:\n\n{text}'
                    }
                ]
            )
            
            summary = response.content[0].text
            logger.info('Text summarized with Claude')
            return summary
        
        except Exception as e:
            logger.error(f'Summarization failed: {str(e)}')
            return text[:max_length]

# Global LLM provider instance
llm_provider = LLMProvider()
