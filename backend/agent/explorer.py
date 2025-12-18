"""
Phase 1: Page Explorer
Explores and understands web pages
"""

import json
import asyncio

class PageExplorer:
    def __init__(self, llm_client, browser_manager, metrics):
        self.llm = llm_client
        self.browser = browser_manager
        self.metrics = metrics
    
    async def explore(self, url: str, websocket) -> dict:
        """
        Explore a web page and build knowledge base
        """
        await websocket.send_json({
            "type": "progress",
            "message": f"Navigating to {url}..."
        })
        
        # Navigate to page
        page = await self.browser.navigate(url)
        
        await websocket.send_json({
            "type": "progress",
            "message": "Analyzing page structure..."
        })
        
        # Extract DOM information
        dom_info = await self._extract_dom(page)
        
        # Take screenshot
        screenshot = await page.screenshot()
        
        await websocket.send_json({
            "type": "progress",
            "message": "Building knowledge base with AI..."
        })
        
        # Use LLM to analyze and structure the page
        analysis = await self._analyze_with_llm(dom_info, url)
        
        # Update metrics
        self.metrics.add_iteration({
            "phase": "exploration",
            "tokens": analysis["tokens"],
            "time": analysis["time"]
        })
        
        # Build final knowledge structure
        knowledge = {
            "url": url,
            "title": dom_info["title"],
            "elements": analysis["json"]["elements"] if analysis["json"] else [],
            "interactions": analysis["json"]["interactions"] if analysis["json"] else [],
            "structure": analysis["json"]["structure"] if analysis["json"] else {},
            "raw_dom": dom_info,
            "timestamp": self.metrics.get_timestamp()
        }
        
        await websocket.send_json({
            "type": "progress",
            "message": f"Found {len(knowledge['elements'])} testable elements"
        })
        
        return knowledge
    
    async def _extract_dom(self, page) -> dict:
        """Extract key information from DOM"""
        
        # Get basic page info
        title = await page.title()
        url = page.url
        
        # Extract interactive elements
        elements_script = """
        () => {
            const elements = [];
            
            // Find inputs
            document.querySelectorAll('input, textarea, select').forEach(el => {
                elements.push({
                    type: 'input',
                    tagName: el.tagName,
                    id: el.id,
                    name: el.name,
                    placeholder: el.placeholder,
                    inputType: el.type,
                    className: el.className,
                    text: el.value
                });
            });
            
            // Find buttons
            document.querySelectorAll('button, [type="submit"], a[href]').forEach(el => {
                elements.push({
                    type: 'button',
                    tagName: el.tagName,
                    id: el.id,
                    className: el.className,
                    text: el.textContent.trim().substring(0, 100),
                    href: el.href
                });
            });
            
            // Find forms
            document.querySelectorAll('form').forEach(el => {
                elements.push({
                    type: 'form',
                    id: el.id,
                    action: el.action,
                    method: el.method,
                    className: el.className
                });
            });
            
            return elements;
        }
        """
        
        elements = await page.evaluate(elements_script)
        
        return {
            "title": title,
            "url": url,
            "elements": elements,
            "element_count": len(elements)
        }
    
    async def _analyze_with_llm(self, dom_info: dict, url: str) -> dict:
        """Use LLM to analyze page structure"""
        
        prompt = f"""
Analyze this web page and create a structured knowledge base for testing.

URL: {url}
Title: {dom_info['title']}
Element Count: {dom_info['element_count']}

Elements found:
{json.dumps(dom_info['elements'][:20], indent=2)}

Create a JSON response with:
1. "elements": List of testable elements with:
   - id: unique identifier
   - type: input/button/form/link
   - locator: best selector strategy (prefer ID > name > CSS)
   - description: what this element does
   
2. "interactions": List of possible user interactions:
   - action: click/type/select/submit
   - target: element id
   - description: what happens
   
3. "structure": Overall page structure:
   - purpose: what the page does
   - main_flow: primary user journey
   - test_priorities: what should be tested first

Keep descriptions concise. Focus on quality locators.
"""
        
        return await self.llm.generate_json(prompt)