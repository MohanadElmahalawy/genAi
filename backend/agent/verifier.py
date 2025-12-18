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
            
            self.metrics.add_iteration({
                "phase": "verification",
                "tokens": 0,  # No LLM calls
                "time": result["execution_time"]
            })
            
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
            # Run pytest with verbose output
            process = await asyncio.create_subprocess_exec(
                'pytest', test_file, '-v', '--tb=short',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            execution_time = time.time() - start_time

            # Combine and decode output
            raw_output = stdout.decode() + stderr.decode()

            # Split into lines preserving order
            lines = [l.rstrip() for l in raw_output.splitlines()]

            # Match individual test result lines and the final summary line.
            pattern_test = re.compile(r"\b(PASSED|FAILED|ERROR)\b", re.I)
            pattern_summary = re.compile(r"=+.*\b(passed|failed|errors?|skipped|xfailed)\b.*in\s*[\d\.]+s.*=+", re.I)

            result_lines = [l for l in lines if pattern_test.search(l) or pattern_summary.search(l)]

            # If a separate summary line exists but wasn't matched, append it.
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

            # Parse numeric results from full raw output when possible (more reliable),
            # otherwise fall back to counting matches in the filtered lines.
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
            
            success = process.returncode == 0
            
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
                "screenshots": [],  # Could capture screenshots here
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
        
        return {
            "screenshot": screenshot,
            "url": page.url,
            "timestamp": time.time()
        }