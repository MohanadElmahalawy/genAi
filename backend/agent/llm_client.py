"""
LLM Client - Groq API Integration (Free Tier)
Using OpenAI SDK with Groq endpoint - 14,400 requests/day FREE
"""

import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
from utils.langfuse_tracker import LangFuseTracker

load_dotenv()


class NoTokensError(Exception):
    """Raised when the LLM provider reports zero available tokens."""
    pass

class LLMClient:
    def __init__(self, langfuse_tracker=None):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key
        )
        # llama-3.3-70b-versatile is fast and powerful (free tier: 14,400 req/day)
        self.model_id = "llama-3.3-70b-versatile"
        self.langfuse = langfuse_tracker
        
    async def generate(self, prompt: str, max_tokens: int = 2048) -> dict:
        """
        Generate response from LLM using GitHub Copilot API.
        """
        start_time = time.time()
        if self.langfuse:
            self.langfuse.start_span("llm_generation", {"prompt": prompt[:200]})
        
        try:
            # GitHub Copilot uses OpenAI's chat completion format
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            
            elapsed = time.time() - start_time
            
            # Extract token usage from response
            tokens = response.usage.total_tokens if response.usage else 0

            # If the provider reports zero tokens, treat as token exhaustion and stop
            if tokens == 0:
                raise NoTokensError("No tokens available from LLM provider")

            result = {
                "text": response.choices[0].message.content,
                "tokens": tokens,
                "time": elapsed
            }
            
            # Log to LangFuse
            if self.langfuse:
                self.langfuse.log_generation(
                    name="groq_generation",
                    prompt=prompt,
                    completion=response.choices[0].message.content,
                    model=self.model_id,
                    tokens=tokens,
                    time=elapsed
                )
                self.langfuse.end_span(output_data=result)
            
            return result
            
        except Exception as e:
            # Detect quota / resource exhausted errors and escalate as NoTokensError
            err_str = str(e)
            print(f"LLM Error: {err_str}")
            if self.langfuse:
                self.langfuse.end_span(metadata={"error": err_str})
            if "RESOURCE_EXHAUSTED" in err_str or "exceeded your current quota" in err_str or "quota" in err_str.lower() or "rate_limit" in err_str.lower():
                raise NoTokensError(err_str)

            return {
                "text": f"Error: {err_str}",
                "tokens": 0,
                "time": time.time() - start_time
            }
    
    async def generate_json(self, prompt: str) -> dict:
        """
        Generate and parse JSON response using native Response Schema if needed,
        or cleaned markdown extraction.
        """
        # We add a specific instruction for JSON
        json_prompt = prompt + "\n\nIMPORTANT: Return ONLY a valid JSON object."
        result = await self.generate(json_prompt)
        if self.langfuse:
            self.langfuse.start_span("json_generation", {"prompt": prompt[:200]})
        
        try:
            text = result["text"]
            # Robust JSON extraction from markdown blocks
            if "json" in text:
                text = text.split("json")[1].split("")[0]
            elif "" in text:
                text = text.split("")[1].split("")[0]
            
            data = json.loads(text.strip())
            result["json"] = data
            # End LangFuse span
            if self.langfuse:
                self.langfuse.end_span(output_data={"json_parsed": True})
            return result
        
        except Exception as e:
            print(f"JSON Parsing Error: {e}")
            result["json"] = None
            # End LangFuse span with error
            if self.langfuse:
                self.langfuse.end_span(metadata={"error": str(e), "json_parsed": False})
            return result