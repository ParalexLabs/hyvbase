from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright
import aiohttp
from bs4 import BeautifulSoup
from .base import SwarmBaseTool

class BrowserTool(SwarmBaseTool):
    """Tool for browser automation using Playwright."""
    
    name: str = "browser"
    description: str = "Navigate web pages, take screenshots, and extract information"
    
    def __init__(self):
        super().__init__()
        self._browser = None
        self._context = None
        
    async def _setup(self):
        """Initialize browser if not already done."""
        if not self._browser:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=True)
            self._context = await self._browser.new_context()
    
    async def _arun(self, command: str) -> str:
        """Execute browser commands."""
        await self._setup()
        
        try:
            # Parse command and parameters
            cmd_parts = command.split(" ", 1)
            action = cmd_parts[0]
            params = cmd_parts[1] if len(cmd_parts) > 1 else ""
            
            if action == "visit":
                return await self._visit_page(params)
            elif action == "screenshot":
                return await self._take_screenshot(params)
            elif action == "extract":
                return await self._extract_content(params)
            else:
                return f"Unknown command: {action}"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _visit_page(self, url: str) -> str:
        """Visit a webpage and return its title."""
        page = await self._context.new_page()
        await page.goto(url)
        title = await page.title()
        return f"Visited page: {title}"
    
    async def _take_screenshot(self, selector: str) -> str:
        """Take screenshot of an element or full page."""
        page = self._context.pages[0]
        if selector:
            element = await page.query_selector(selector)
            if element:
                await element.screenshot(path="element.png")
                return "Screenshot taken of element"
        await page.screenshot(path="page.png")
        return "Screenshot taken of full page"
    
    async def _extract_content(self, selector: str) -> str:
        """Extract content from the page using a CSS selector."""
        page = self._context.pages[0]
        elements = await page.query_selector_all(selector)
        texts = [await el.text_content() for el in elements]
        return "\n".join(texts)

class RequestsTool(SwarmBaseTool):
    """Tool for making HTTP requests."""
    
    name: str = "requests"
    description: str = "Make HTTP requests to web APIs and endpoints"
    
    async def _arun(self, command: str) -> str:
        """Execute HTTP requests."""
        try:
            # Parse command
            cmd_parts = command.split(" ", 2)
            method = cmd_parts[0].upper()
            url = cmd_parts[1]
            data = cmd_parts[2] if len(cmd_parts) > 2 else None
            
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url) as response:
                        return await self._process_response(response)
                elif method == "POST":
                    async with session.post(url, json=eval(data)) as response:
                        return await self._process_response(response)
                else:
                    return f"Unsupported method: {method}"
                    
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _process_response(self, response: aiohttp.ClientResponse) -> str:
        """Process HTTP response."""
        if response.content_type == 'application/json':
            return str(await response.json())
        return await response.text()

class PlaywrightTool(SwarmBaseTool):
    """Advanced web automation tool using Playwright."""
    
    name: str = "playwright"
    description: str = "Advanced web automation for complex scenarios"
    
    def __init__(self):
        super().__init__()
        self._playwright = None
        self._browser = None
        self._page = None
    
    async def _setup(self):
        """Initialize Playwright if not already done."""
        if not self._playwright:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch()
            self._page = await self._browser.new_page()
    
    async def _arun(self, command: str) -> str:
        """Execute Playwright automation commands."""
        await self._setup()
        
        try:
            # Parse command
            cmd_parts = command.split(" ", 1)
            action = cmd_parts[0]
            params = cmd_parts[1] if len(cmd_parts) > 1 else ""
            
            if action == "navigate":
                await self._page.goto(params)
                return f"Navigated to {params}"
                
            elif action == "click":
                await self._page.click(params)
                return f"Clicked {params}"
                
            elif action == "type":
                selector, text = params.split(" ", 1)
                await self._page.type(selector, text)
                return f"Typed into {selector}"
                
            elif action == "scrape":
                return await self._scrape_content(params)
                
            else:
                return f"Unknown command: {action}"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _scrape_content(self, selector: str) -> str:
        """Scrape content from the page."""
        elements = await self._page.query_selector_all(selector)
        results = []
        
        for element in elements:
            text = await element.text_content()
            results.append(text.strip())
        
        return "\n".join(results)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop() 