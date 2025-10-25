"""
模拟浏览器服务 - 用于开发和测试
"""
from typing import Dict, Any
import asyncio
from datetime import datetime

class MockBrowserService:
    """模拟浏览器服务"""
    
    def __init__(self):
        self.is_running = False
        self.current_page = None
        self.browser = None  # 添加browser属性以保持兼容性
        
    async def start(self):
        """启动浏览器服务"""
        self.is_running = True
        print("Mock Browser Service started")
        
    async def stop(self):
        """停止浏览器服务"""
        self.is_running = False
        self.current_page = None
        print("Mock Browser Service stopped")
        
    async def navigate_to_url(self, url: str) -> Dict[str, Any]:
        """导航到指定URL"""
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        self.current_page = {
            "url": url,
            "title": f"Mock Page - {url}",
            "loaded_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "url": url,
            "title": self.current_page["title"],
            "message": f"Successfully navigated to {url}"
        }
        
    async def fill_form_field(self, selector: str, value: str) -> Dict[str, Any]:
        """填写表单字段"""
        await asyncio.sleep(0.05)  # 模拟操作延迟
        
        return {
            "success": True,
            "selector": selector,
            "value": value,
            "message": f"Successfully filled field '{selector}' with value '{value}'"
        }
        
    async def click_element(self, selector: str) -> Dict[str, Any]:
        """点击元素"""
        await asyncio.sleep(0.05)  # 模拟操作延迟
        
        return {
            "success": True,
            "selector": selector,
            "message": f"Successfully clicked element '{selector}'"
        }
        
    async def get_page_content(self) -> Dict[str, Any]:
        """获取页面内容"""
        if not self.current_page:
            return {
                "success": False,
                "message": "No page loaded"
            }
            
        # 模拟页面内容
        mock_content = f"""
        <html>
            <head><title>{self.current_page['title']}</title></head>
            <body>
                <h1>Mock Page Content</h1>
                <p>This is a mock page for URL: {self.current_page['url']}</p>
                <form>
                    <input type="text" name="username" placeholder="Username">
                    <input type="password" name="password" placeholder="Password">
                    <button type="submit">Submit</button>
                </form>
            </body>
        </html>
        """
        
        return {
            "success": True,
            "content": mock_content,
            "url": self.current_page["url"]
        }
        
    async def take_screenshot(self) -> Dict[str, Any]:
        """截图"""
        await asyncio.sleep(0.1)  # 模拟截图延迟
        
        return {
            "success": True,
            "screenshot_path": "/mock/screenshot.png",
            "message": "Mock screenshot taken"
        }
        
    async def execute_script(self, script: str) -> Dict[str, Any]:
        """执行JavaScript脚本"""
        await asyncio.sleep(0.05)  # 模拟执行延迟
        
        return {
            "success": True,
            "script": script,
            "result": "Mock script execution result",
            "message": f"Successfully executed script: {script[:50]}..."
        }
        
    async def wait_for_element(self, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """等待元素出现"""
        await asyncio.sleep(0.1)  # 模拟等待
        
        return {
            "success": True,
            "selector": selector,
            "message": f"Element '{selector}' found (mock)"
        }
        
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "is_running": self.is_running,
            "current_page": self.current_page,
            "service_type": "mock"
        }