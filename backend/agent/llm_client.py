"""
LLM Client - 2025 Gemini Free Tier Integration
Using the official Google Gen AI SDK (google-genai)
"""

import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class NoTokensError(Exception):
    """Raised when the LLM provider reports zero available tokens."""
    pass

class LLMClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        # New SDK Client
        self.client = genai.Client(api_key=api_key)
        # Gemini 3 Flash is the recommended fast model for 2025
        self.model_id = "gemini-3-flash-preview"
        
    async def generate(self, prompt: str, max_tokens: int = 2048) -> dict:
        """
        Generate response from LLM using current SDK methods.
        """
        start_time = time.time()
        
        try:
            # Note: client.models.generate_content is the new standard
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                )
            )
            
            elapsed = time.time() - start_time
            
            # The new SDK provides real token counts in usage_metadata (no more estimation!)
            tokens = response.usage_metadata.total_token_count

            # If the provider reports zero tokens, treat as token exhaustion and stop
            if tokens == 0:
                raise NoTokensError("No tokens available from LLM provider")

            return {
                "text": response.text,
                "tokens": tokens,
                "time": elapsed
            }
            
        except Exception as e:
            # Detect quota / resource exhausted errors and escalate as NoTokensError
            err_str = str(e)
            print(f"LLM Error: {err_str}")
            if "RESOURCE_EXHAUSTED" in err_str or "exceeded your current quota" in err_str or "quota" in err_str.lower():
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
        
        try:
            text = result["text"]
            # Robust JSON extraction from markdown blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            data = json.loads(text.strip())
            result["json"] = data
            return result
        except Exception as e:
            print(f"JSON Parsing Error: {e}")
            result["json"] = None
            return result