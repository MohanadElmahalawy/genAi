"""
Phase 4: Test Verifier
Executes and verifies generated tests
"""

import asyncio
import tempfile
import os
import subprocess
import time

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
            
            output = stdout.decode() + stderr.decode()
            
            # Parse results
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")
            errors = output.count(" ERROR")
            
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