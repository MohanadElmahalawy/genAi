"""
Browser Manager
Handles Playwright browser instance
"""

from playwright.async_api import async_playwright

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def launch(self, headless: bool = False):
        """Launch browser instance"""
        self.playwright = await async_playwright().start()
        
        # Launch Chromium in headed or headless mode
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=['--start-maximized']
        )
        
        # Use full browser window instead of fixed viewport
        self.context = await self.browser.new_context(
            viewport=None,  # full window
            screen={'width': 1920, 'height': 1080}  # emulate monitor size
        )
        
        self.page = await self.context.new_page()
    
    async def navigate(self, url: str):
        """Navigate to a URL and scroll to top-left"""
        if not self.page:
            await self.launch()
        
        await self.page.goto(url, wait_until='networkidle')
        
        # Scroll to top-left to avoid clipped content
        await self.page.evaluate("window.scrollTo(0, 0)")
        return self.page
    
    def get_page(self):
        """Return current page object"""
        return self.page
    
    async def close(self):
        """Close browser and cleanup"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
    
    async def screenshot(self, path: str = None):
        """Take full-page screenshot"""
        if not self.page:
            return None
        return await self.page.screenshot(path=path, full_page=True)
    
    async def resize_to_full_content(self):
        """Optional: Resize viewport to fit entire page content"""
        if not self.page:
            return
        width = await self.page.evaluate("document.body.scrollWidth")
        height = await self.page.evaluate("document.body.scrollHeight")
        await self.page.set_viewport_size({"width": width, "height": height})
