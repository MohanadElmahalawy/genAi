import sys
import asyncio
import json
import pathlib
import time

# Ensure repo root (backend/) is on path so we can import agent and utils
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.verifier import TestVerifier
from utils.metrics import MetricsTracker

class MockWebSocket:
    def __init__(self):
        self.messages = []
    async def send_json(self, msg):
        self.messages.append(msg)
        print("WS:", msg)

class MockPage:
    def __init__(self):
        self.url = "https://example.com"
    async def screenshot(self):
        # return a tiny valid PNG header + minimal content (not a full image but sufficient bytes)
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

class MockBrowserManager:
    def __init__(self):
        self._page = MockPage()
    def get_page(self):
        return self._page
    async def launch(self, headless: bool = True):
        return
    async def screenshot(self, path: str = None):
        return await self._page.screenshot()

async def main():
    metrics = MetricsTracker()
    mock_browser = MockBrowserManager()
    verifier = TestVerifier(mock_browser, metrics)
    websocket = MockWebSocket()

    # Simple, self-contained pytest test that should pass
    code = """
def test_example():
    assert 1 + 1 == 2
"""

    result = await verifier.verify(code, websocket)
    print("Verification result keys:", list(result.keys()))

    report = {
        "result": result,
        "websocket_messages": websocket.messages,
        "timestamp": time.time()
    }

    out_path = ROOT / "verification_with_screenshots.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Wrote report to {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
