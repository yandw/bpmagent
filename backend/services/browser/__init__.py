from .base import BaseBrowserService, PageElement, ElementType, BrowserAction, PageState
from .playwright_service import PlaywrightBrowserService
from .mock_service import MockBrowserService
from backend.core.config import settings
from typing import Dict, Any


def create_browser_service(config: Dict[str, Any] = None) -> BaseBrowserService:
    """
    根据配置创建浏览器服务实例
    
    Args:
        config: 浏览器配置，如果为None则使用默认配置
    
    Returns:
        BaseBrowserService: 浏览器服务实例
    """
    if config is None:
        config = {
            'headless': settings.browser_headless,
            'browser_type': 'chromium',
            'viewport': {'width': 1280, 'height': 720},
            'user_agent': None
        }
    
    # 使用Playwright服务
    return PlaywrightBrowserService(config)


__all__ = [
    "BaseBrowserService",
    "PageElement", 
    "ElementType", 
    "BrowserAction", 
    "PageState",
    "PlaywrightBrowserService",
    "create_browser_service"
]