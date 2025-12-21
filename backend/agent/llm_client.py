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
