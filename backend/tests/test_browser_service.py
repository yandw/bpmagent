import pytest
import asyncio
from backend.services.browser import create_browser_service, PlaywrightBrowserService


class TestBrowserService:
    """浏览器服务测试"""

    @pytest.fixture
    def browser_config(self):
        """浏览器配置"""
        return {
            'headless': True,
            'browser_type': 'chromium',
            'viewport': {'width': 1280, 'height': 720},
            'user_agent': None
        }

    def test_create_browser_service(self, browser_config):
        """测试创建浏览器服务"""
        service = create_browser_service(browser_config)
        assert isinstance(service, PlaywrightBrowserService)
        assert service.config == browser_config

    @pytest.mark.asyncio
    async def test_browser_lifecycle(self, browser_config):
        """测试浏览器生命周期"""
        service = create_browser_service(browser_config)
        
        # 启动浏览器
        success = await service.start_browser()
        assert success is True
        assert service.browser is not None
        assert service.page is not None
        
        # 关闭浏览器
        await service.close_browser()

    @pytest.mark.asyncio
    async def test_navigate_to_url(self, browser_config):
        """测试导航到URL"""
        service = create_browser_service(browser_config)
        
        try:
            # 启动浏览器
            await service.start_browser()
            
            # 导航到测试页面
            success = await service.navigate_to("https://httpbin.org/html")
            assert success is True
            
            # 获取页面HTML
            html = await service.get_page_html()
            assert "Herman Melville" in html
            
        finally:
            await service.close_browser()

    @pytest.mark.asyncio
    async def test_take_screenshot(self, browser_config):
        """测试截图功能"""
        service = create_browser_service(browser_config)
        
        try:
            # 启动浏览器
            await service.start_browser()
            
            # 导航到测试页面
            await service.navigate_to("https://httpbin.org/html")
            
            # 截图
            screenshot = await service.take_screenshot()
            assert isinstance(screenshot, bytes)
            assert len(screenshot) > 0
            
        finally:
            await service.close_browser()

    @pytest.mark.asyncio
    async def test_find_elements(self, browser_config):
        """测试查找元素"""
        service = create_browser_service(browser_config)
        
        try:
            # 启动浏览器
            await service.start_browser()
            
            # 导航到测试页面
            await service.navigate_to("https://httpbin.org/forms/post")
            
            # 查找输入元素
            elements = await service.find_elements("input")
            assert len(elements) > 0
            
            # 检查元素属性
            for element in elements:
                assert element.selector is not None
                assert element.element_type is not None
                
        finally:
            await service.close_browser()

    @pytest.mark.asyncio
    async def test_input_and_click(self, browser_config):
        """测试输入和点击操作"""
        service = create_browser_service(browser_config)
        
        try:
            # 启动浏览器
            await service.start_browser()
            
            # 导航到测试页面
            await service.navigate_to("https://httpbin.org/forms/post")
            
            # 输入文本
            success = await service.input_text("input[name='custname']", "Test User")
            assert success is True
            
            # 检查元素是否可见
            visible = await service.is_element_visible("input[name='custname']")
            assert visible is True
            
            # 获取元素文本
            text = await service.get_element_text("input[name='custname']")
            # 注意：input元素的文本可能为空，这是正常的
            
        finally:
            await service.close_browser()

    @pytest.mark.asyncio
    async def test_wait_for_element(self, browser_config):
        """测试等待元素"""
        service = create_browser_service(browser_config)
        
        try:
            # 启动浏览器
            await service.start_browser()
            
            # 导航到测试页面
            await service.navigate_to("https://httpbin.org/html")
            
            # 等待元素出现
            success = await service.wait_for_element("h1", timeout=5000)
            assert success is True
            
        finally:
            await service.close_browser()

    @pytest.mark.asyncio
    async def test_scroll_to_element(self, browser_config):
        """测试滚动到元素"""
        service = create_browser_service(browser_config)
        
        try:
            # 启动浏览器
            await service.start_browser()
            
            # 导航到测试页面
            await service.navigate_to("https://httpbin.org/html")
            
            # 滚动到元素
            success = await service.scroll_to_element("h1")
            assert success is True
            
        finally:
            await service.close_browser()