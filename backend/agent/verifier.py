"""
Phase 4: Test Verifier
Executes and verifies generated tests
"""

import asyncio
import tempfile
import os
import subprocess
import time
import re
import base64
import json
import pathlib

class TestVerifier:
    def __init__(self, browser_manager, metrics):
        self.browser = browser_manager
        self.metrics = metrics
    
    async def verify(self, code: str, websocket) -> dict:
        """
        Execute generated test code and verify results
        """
        await websocket.send_json({
            "type": "progress",
            "message": "Setting up test environment..."
        })
        # If a BrowserManager was provided, ensure a page exists so we can
        # capture screenshots as part of evidence.
        if self.browser:
            try:
                page = self.browser.get_page()
                if not page:
                    await self.browser.launch(headless=True)
            except Exception:
                # Don't fail verification just because screenshots can't be taken
                pass
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(
            mode='w', 
            prefix='test_',  # <--- CRITICAL: pytest needs this prefix
            suffix='.py', 
            delete=False, 
            encoding='utf-8'
        ) as f:
            f.write(code)
            test_file = f.name
        
        try:
            await websocket.send_json({
                "type": "progress",
                "message": "Running tests..."
            })
            
            # Execute tests
            result = await self._run_pytest(test_file, websocket)

            # Attempt to capture a screenshot of the current page (if available)
            screenshots = []
            try:
                if self.browser and self.browser.get_page():
                    shot = await self.browser.screenshot()
                    if shot:
                        b64 = base64.b64encode(shot).decode('utf-8')
                        url = None
                        try:
                            url = self.browser.get_page().url
                        except Exception:
                            url = None
                        screenshots.append({
                            "image_base64": b64,
                            "url": url,
                            "timestamp": time.time()
                        })
            except Exception:
                # Swallow screenshot errors; verification should still return results
                pass

            # Attach screenshots to result and record metrics
            try:
                result["screenshots"] = screenshots
            except Exception:
                result["screenshots"] = []

            self.metrics.add_iteration({
                "phase": "verification",
                "tokens": 0,  # No LLM calls
                "time": result.get("execution_time", 0)
            })

            # Persist the verification report to backend/verification_with_screenshots.json
            try:
                # Write report to backend root so the main API can serve it at
                # `/reports/verification`. `__file__.parents[1]` points to backend/.
                report_path = pathlib.Path(__file__).resolve().parents[1] / "verification_with_screenshots.json"
                tmp_path = report_path.with_suffix('.json.tmp')
                with open(tmp_path, 'w', encoding='utf-8') as rf:
                    json.dump({
                        "result": result,
                        "timestamp": time.time()
                    }, rf, indent=2)
                # atomic replace
                os.replace(str(tmp_path), str(report_path))
            except Exception:
                # File write failures should not break verification flow
                pass

            return result
            
        finally:
            # Cleanup
            try:
                os.unlink(test_file)
            except:
                pass
    
    async def _run_pytest(self, test_file: str, websocket) -> dict:
        """Run pytest on the test file"""
        start_time = time.time()

        try:
            # Run pytest in-process so generated tests can access the same
            # BrowserManager via the `verifier_shared` module. Running pytest
            # in a subprocess isolates the process and prevents tests from
            # using our browser instance for taking screenshots.
            import io
            import sys
            import contextlib

            # Try to set the shared browser reference for tests
            try:
                from . import verifier_shared
                verifier_shared.set_browser(self.browser)
            except Exception:
                try:
                    import verifier_shared
                    verifier_shared.set_browser(self.browser)
                except Exception:
                    pass

            loop = asyncio.get_event_loop()

            def run_pytest_sync():
                # Import pytest here to avoid importing it in the event loop
                import pytest
                out_buf = io.StringIO()
                err_buf = io.StringIO()
                with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
                    rc = pytest.main([test_file, '-v', '--tb=short'])
                return rc, out_buf.getvalue(), err_buf.getvalue()

            rc, stdout_text, stderr_text = await loop.run_in_executor(None, run_pytest_sync)

            execution_time = time.time() - start_time

            raw_output = (stdout_text or "") + (stderr_text or "")
            lines = [l.rstrip() for l in raw_output.splitlines()]

            pattern_test = re.compile(r"\b(PASSED|FAILED|ERROR)\b", re.I)
            pattern_summary = re.compile(r"=+.*\b(passed|failed|errors?|skipped|xfailed)\b.*in\s*[\d\.]+s.*=+", re.I)

            result_lines = [l for l in lines if pattern_test.search(l) or pattern_summary.search(l)]

            summary_line = None
            for l in reversed(lines):
                if re.search(r"(\d+)\s+passed", l, re.I):
                    summary_line = l
                    break
            if summary_line and summary_line not in result_lines:
                if result_lines and result_lines[-1].strip() != "":
                    result_lines.append("")
                result_lines.append(summary_line)

            output = "\n".join(result_lines).strip()

            passed = 0
            failed = 0
            errors = 0

            m = re.search(r"(\d+)\s+passed", raw_output, re.I)
            if m:
                passed = int(m.group(1))
            else:
                passed = sum(1 for l in result_lines if re.search(r"\bpassed\b", l, re.I) and not pattern_summary.search(l))

            m = re.search(r"(\d+)\s+failed", raw_output, re.I)
            if m:
                failed = int(m.group(1))
            else:
                failed = sum(1 for l in result_lines if re.search(r"\bfailed\b", l, re.I) and not pattern_summary.search(l))

            m = re.search(r"(\d+)\s+errors?", raw_output, re.I)
            if m:
                errors = int(m.group(1))
            else:
                errors = sum(1 for l in result_lines if re.search(r"\berror\b", l, re.I))

            success = rc == 0

            await websocket.send_json({
                "type": "progress",
                "message": f"Tests completed: {passed} passed, {failed} failed"
            })

            return {
                "success": success,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "output": output,
                "execution_time": execution_time,
                "screenshots": [],
                "timestamp": time.time()
            }

        except Exception as e:
            return {
                "success": False,
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "output": f"Execution error: {str(e)}",
                "execution_time": time.time() - start_time,
                "screenshots": [],
                "timestamp": time.time()
            }
    
    async def capture_evidence(self, page) -> dict:
        """Capture screenshots and other evidence during test execution"""
        
        screenshot = await page.screenshot()
        b64 = None
        if screenshot:
            try:
                b64 = base64.b64encode(screenshot).decode('utf-8')
            except Exception:
                b64 = None

        return {
            "screenshot_base64": b64,
            "url": getattr(page, 'url', None),
            "timestamp": time.time()
        }