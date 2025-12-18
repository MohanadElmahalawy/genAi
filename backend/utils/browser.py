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
        
        # Launch Chromium in headed mode so user can see
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=['--start-maximized']
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        self.page = await self.context.new_page()
    
    async def navigate(self, url: str):
        """Navigate to URL"""
        if not self.page:
            await self.launch()
        
        await self.page.goto(url, wait_until='networkidle')
        return self.page
    
    def get_page(self):
        """Get current page"""
        return self.page
    
    async def close(self):
        """Close browser"""
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
        """Take screenshot"""
        if not self.page:
            return None
        
        return await self.page.screenshot(path=path, full_page=True)