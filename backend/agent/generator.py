"""
Phase 3: Code Generator
Generates Playwright test code
"""

import json

class CodeGenerator:
    def __init__(self, llm_client, metrics):
        self.llm = llm_client
        self.metrics = metrics
    
    async def generate(self, page_knowledge: dict, test_cases: dict, websocket) -> str:
        """
        Generate executable Playwright test code
        """
        await websocket.send_json({
            "type": "progress",
            "message": "Generating Playwright test code..."
        })
        
        # Generate code using LLM
        code_result = await self._generate_code(page_knowledge, test_cases)
        
        self.metrics.add_iteration({
            "phase": "generation",
            "tokens": code_result["tokens"],
            "time": code_result["time"]
        })
        
        code = self._extract_code(code_result["text"])
        
        await websocket.send_json({
            "type": "progress",
            "message": "Test code generated successfully"
        })
        
        return code
    
    async def _generate_code(self, knowledge: dict, test_cases: dict) -> dict:
        """Use LLM to generate test code"""
        
        elements_summary = "\n".join([
            f"- {el.get('id', 'unknown')}: {el.get('locator', 'N/A')} ({el.get('type', 'unknown')})"
            for el in knowledge.get('elements', [])[:20]
        ])
        
        test_cases_summary = "\n".join([
            f"- {tc.get('id', 'N/A')}: {tc.get('name', 'Unnamed test')}"
            for tc in test_cases.get('test_cases', [])
        ])
        
        prompt = f"""
Generate a complete Playwright Python test file for these test cases.

URL: {knowledge['url']}

Available Elements:
{elements_summary}

Test Cases to Implement:
{test_cases_summary}

Detailed Test Cases:
{json.dumps(test_cases.get('test_cases', []), indent=2)}

Requirements:
1. Use Playwright with Python (pytest-playwright)
2. Use the BEST locator strategy for each element:
   - Prefer: data-testid > id > name > CSS selector
   - Use get_by_role() when possible for accessibility
   - Make locators resilient to UI changes
3. Include proper assertions for each test
4. Add comments explaining each step
5. Handle waits properly (wait_for_selector, wait_for_load_state)
6. Structure as pytest test functions

Code structure:
```python
import pytest
from playwright.sync_api import Page, expect

class TestWebPage:
    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        page.goto("{knowledge['url']}")
        page.wait_for_load_state("networkidle")
        yield page
    
    # ... test methods here
```

Generate COMPLETE, EXECUTABLE code. No placeholders.
"""
        
        return await self.llm.generate(prompt, max_tokens=3000)
    
    def _extract_code(self, text: str) -> str:
        """Extract Python code from LLM response"""
        
        # Try to extract code from markdown blocks
        if "```python" in text:
            parts = text.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
                return code.strip()
        
        if "```" in text:
            parts = text.split("```")
            if len(parts) > 1:
                return parts[1].strip()
        
        # Return as-is if no code blocks found
        return text.strip()
    
    async def refine_code(self, current_code: str, issue: str, websocket) -> str:
        """Refine code based on issues found"""
        
        await websocket.send_json({
            "type": "progress",
            "message": "Refining code to fix issues..."
        })
        
        prompt = f"""
Current test code has an issue:
{issue}

Current code:
```python
{current_code}
```

Fix the issue and return the complete corrected code.
Only return the Python code, no explanations.
"""
        
        result = await self.llm.generate(prompt, max_tokens=3000)
        
        self.metrics.add_iteration({
            "phase": "generation_refinement",
            "tokens": result["tokens"],
            "time": result["time"]
        })
        
        return self._extract_code(result["text"])

    async def verify_and_refine(self, code: str, verifier, websocket, max_rounds: int = 1) -> str:
        """
        Verify generated code using the TestVerifier. If verification fails,
        pass the failures to `refine_code` and retry up to `max_rounds` times.
        Returns the last produced code (successful or final attempt).
        """

        last_result = None
        for attempt in range(1, max_rounds + 1):
            await websocket.send_json({
                "type": "progress",
                "message": f"Verifying generated tests (attempt {attempt}/{max_rounds})..."
            })

            result = await verifier.verify(code, websocket)
            last_result = result

            # Record verification metrics
            try:
                self.metrics.add_iteration({
                    "phase": "verification_attempt",
                    "tokens": 0,
                    "time": result.get("execution_time", result.get("execution_time", 0))
                })
            except Exception:
                pass

            if result.get("success"):
                await websocket.send_json({
                    "type": "progress",
                    "message": "Generated tests passed verification."
                })
                return {"code": code, "verification": result}

            # Verification failed: prepare issue text and attempt refinement
            issue = result.get("output") or "Tests failed during execution"

            await websocket.send_json({
                "type": "progress",
                "message": f"Verification failed (attempt {attempt}). Refining code..."
            })

            # Call refine_code to get a corrected version
            code = await self.refine_code(code, issue, websocket)

        # Final verification attempt result not successful (or max rounds reached)
        await websocket.send_json({
            "type": "progress",
            "message": "Reached max refinement attempts; returning latest code." 
        })

        return {"code": code, "verification": last_result}