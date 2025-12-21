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
from openai import OpenAI

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


class CopilotClient:
        """
        Lightweight GitHub Copilot-compatible client using the OpenAI-compatible
        Python package interface as shown in the provided screenshot. This class
        wraps synchronous SDK calls so it can be awaited from async code.
        """
        def __init__(self, api_key: str | None = None, base_url: str = "https://api.githubcopilot.com", model: str = "grok-code-fast-1"):
            self.api_key = api_key or os.getenv("COPILOT_API_KEY")
            if not self.api_key:
                raise ValueError("API_KEY or COPILOT_API_KEY not found in environment")

            self.base_url = base_url
            self.model = model
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        async def generate(self, prompt: str, system_prompt: str = "You are a helpful assistant.", max_tokens: int | None = None) -> dict:
            """Generate a chat completion and return a small result dict.

            The underlying OpenAI/OpenAI-compatible client is synchronous, so
            we run it in a thread to avoid blocking the event loop.
            """
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]

            import asyncio

            start_time = time.time()

            def _call():
                params = {"model": self.model, "messages": messages}
                if max_tokens is not None:
                    params["max_tokens"] = max_tokens
                return self.client.chat.completions.create(**params)

            resp = await asyncio.to_thread(_call)
            elapsed = time.time() - start_time

            # Extract text safely
            text = None
            try:
                text = resp.choices[0].message.content
            except Exception:
                try:
                    text = resp.choices[0]["message"]["content"]
                except Exception:
                    text = str(resp)

            # Try to get usage if available
            tokens = None
            try:
                if hasattr(resp, "usage") and getattr(resp.usage, "total_tokens", None) is not None:
                    tokens = resp.usage.total_tokens
                elif isinstance(resp, dict) and "usage" in resp and "total_tokens" in resp["usage"]:
                    tokens = resp["usage"]["total_tokens"]
            except Exception:
                tokens = None

            return {"text": text, "tokens": tokens, "raw": resp, "time": elapsed}

        async def generate_json(self, prompt: str) -> dict:
            """
            Generate and parse JSON response from Copilot-compatible client.
            More robust extraction: handles markdown code fences, trailing text,
            and attempts balanced-brace extraction with a few simple fixes.
            """
            start_time = time.time()
            json_prompt = prompt + "\n\nIMPORTANT: Return ONLY a valid JSON object."

            try:
                result = await self.generate(json_prompt)
            except Exception as e:
                print(f"Copilot JSON Generation Error: {e}")
                return {"text": f"Error: {e}", "tokens": None, "time": time.time() - start_time, "json": None}

            elapsed = time.time() - start_time
            result.setdefault("time", elapsed)

            text = (result.get("text") or "").strip()

            # Prefer explicit JSON code fence extraction
            if "```json" in text:
                snippet = text.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in text:
                snippet = text.split("```", 1)[1].split("```", 1)[0]
            else:
                snippet = text

            snippet = snippet.strip()

            import re

            # Find first JSON-like start
            m = re.search(r"[\{\[]", snippet)
            if m:
                snippet = snippet[m.start():]

            def try_load(s: str):
                try:
                    return json.loads(s)
                except Exception:
                    return None

            # If snippet starts with { or [, try to find balanced end
            parsed = None
            if snippet and snippet[0] in "{[":
                open_ch = snippet[0]
                close_ch = '}' if open_ch == '{' else ']'
                depth = 0
                end_idx = None
                for i, ch in enumerate(snippet):
                    if ch == open_ch:
                        depth += 1
                    elif ch == close_ch:
                        depth -= 1
                        if depth == 0:
                            end_idx = i
                            break

                if end_idx is not None:
                    candidate = snippet[: end_idx + 1]
                    parsed = try_load(candidate)

            # Fallback: try to trim after last closing brace/bracket
            if parsed is None:
                last_pos = max(snippet.rfind('}'), snippet.rfind(']'))
                if last_pos != -1:
                    candidate = snippet[: last_pos + 1]
                    parsed = try_load(candidate)

            # Fallback heuristic: fix common issues (single quotes, trailing commas)
            if parsed is None and snippet:
                candidate = snippet
                # replace smart quotes and single quotes only when it looks JSON-like
                candidate = candidate.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
                # convert single-quoted keys/strings to double quotes (simple heuristic)
                if "'" in candidate and '"' not in candidate:
                    candidate = candidate.replace("'", '"')
                # remove trailing commas before closing braces/brackets
                candidate = re.sub(r",\s*([\}\]])", r"\1", candidate)
                parsed = try_load(candidate)

            if parsed is not None:
                result["json"] = parsed
                return result

            # If all attempts fail, attach raw snippet for debugging and return json=None
            preview = snippet[:1000]
            print(f"Copilot JSON Parsing Error: unable to parse JSON. Preview: {preview!r}")
            result["json"] = None
            result["raw_text_preview"] = preview
            return result
