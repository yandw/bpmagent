import asyncio
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright
from .base import BaseBrowserService, PageElement, ElementType
import logging

logger = logging.getLogger(__name__)


class PlaywrightBrowserService(BaseBrowserService):
    """基于Playwright的浏览器自动化服务"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # 默认配置
        self.headless = config.get('headless', True)
        self.browser_type = config.get('browser_type', 'chromium')
        self.viewport = config.get('viewport', {'width': 1280, 'height': 720})
        self.user_agent = config.get('user_agent', None)
    
    async def start_browser(self) -> bool:
        """启动浏览器"""
        try:
            self.playwright = await async_playwright().start()
            
            # 选择浏览器类型
            if self.browser_type == 'firefox':
                browser_launcher = self.playwright.firefox
            elif self.browser_type == 'webkit':
                browser_launcher = self.playwright.webkit
            else:
                browser_launcher = self.playwright.chromium
            
            # 启动浏览器
            launch_options = {
                'headless': self.headless,
                'args': ['--no-sandbox', '--disable-dev-shm-usage']
            }
            
            self.browser = await browser_launcher.launch(**launch_options)
            
            # 创建新页面
            context_options = {
                'viewport': self.viewport,
                'ignore_https_errors': True
            }
            
            if self.user_agent:
                context_options['user_agent'] = self.user_agent
            
            context = await self.browser.new_context(**context_options)
            self.page = await context.new_page()
            
            # 设置默认超时
            self.page.set_default_timeout(30000)
            
            logger.info("浏览器启动成功")
            return True
            
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            return False
    
    async def close_browser(self):
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            logger.info("浏览器已关闭")
            
        except Exception as e:
            logger.error(f"关闭浏览器时出错: {e}")
    
    async def navigate_to(self, url: str) -> bool:
        """导航到指定URL"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            response = await self.page.goto(url, wait_until='domcontentloaded')
            
            if response and response.status < 400:
                logger.info(f"成功导航到: {url}")
                return True
            else:
                logger.error(f"导航失败，状态码: {response.status if response else 'None'}")
                return False
                
        except Exception as e:
            logger.error(f"导航到 {url} 时出错: {e}")
            return False
    
    async def take_screenshot(self) -> bytes:
        """截取当前页面截图"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            screenshot = await self.page.screenshot(full_page=True)
            return screenshot
            
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return b""
    
    async def get_page_html(self) -> str:
        """获取当前页面HTML"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            html = await self.page.content()
            return html
            
        except Exception as e:
            logger.error(f"获取页面HTML失败: {e}")
            return ""
    
    async def find_elements(self, selector: str) -> List[PageElement]:
        """查找页面元素"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            elements = []
            locators = await self.page.locator(selector).all()
            
            for i, locator in enumerate(locators):
                try:
                    # 获取元素信息
                    tag_name = await locator.evaluate('el => el.tagName.toLowerCase()')
                    element_type = await locator.get_attribute('type') or tag_name
                    name = await locator.get_attribute('name') or await locator.get_attribute('id') or f"{tag_name}_{i}"
                    value = await locator.input_value() if tag_name in ['input', 'textarea'] else await locator.text_content()
                    placeholder = await locator.get_attribute('placeholder')
                    required = await locator.get_attribute('required') is not None
                    
                    # 初始化options变量
                    options = []
                    
                    # 确定元素类型
                    if tag_name == 'input':
                        if element_type in ['text', 'email', 'password', 'number']:
                            elem_type = ElementType.INPUT
                        elif element_type == 'checkbox':
                            elem_type = ElementType.CHECKBOX
                        elif element_type == 'radio':
                            elem_type = ElementType.RADIO
                        elif element_type == 'file':
                            elem_type = ElementType.FILE_UPLOAD
                        else:
                            elem_type = ElementType.INPUT
                    elif tag_name == 'select':
                        elem_type = ElementType.SELECT
                        # 获取选项
                        options = await locator.locator('option').all_text_contents()
                    elif tag_name == 'textarea':
                        elem_type = ElementType.TEXTAREA
                    elif tag_name == 'button' or (tag_name == 'input' and element_type == 'submit'):
                        elem_type = ElementType.BUTTON
                    elif tag_name == 'a':
                        elem_type = ElementType.LINK
                    else:
                        continue  # 跳过不支持的元素类型
                    
                    # 生成更准确的选择器
                    element_selector = f"{selector}:nth-of-type({i+1})"
                    
                    page_element = PageElement(
                        element_type=elem_type,
                        selector=element_selector,
                        name=name,
                        value=value,
                        required=required,
                        options=options,
                        placeholder=placeholder
                    )
                    
                    elements.append(page_element)
                    
                except Exception as e:
                    logger.warning(f"解析元素 {i} 时出错: {e}")
                    continue
            
            return elements
            
        except Exception as e:
            logger.error(f"查找元素失败: {e}")
            return []
    
    async def click_element(self, selector: str, timeout: int = 5000) -> bool:
        """点击元素"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            await self.page.click(selector, timeout=timeout)
            logger.info(f"成功点击元素: {selector}")
            return True
            
        except Exception as e:
            logger.error(f"点击元素 {selector} 失败: {e}")
            return False
    
    async def input_text(self, selector: str, text: str, timeout: int = 5000) -> bool:
        """输入文本"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            # 清空输入框并输入新文本
            await self.page.fill(selector, text, timeout=timeout)
            logger.info(f"成功输入文本到 {selector}: {text}")
            return True
            
        except Exception as e:
            logger.error(f"输入文本到 {selector} 失败: {e}")
            return False
    
    async def select_option(self, selector: str, value: str, timeout: int = 5000) -> bool:
        """选择下拉框选项"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            await self.page.select_option(selector, value, timeout=timeout)
            logger.info(f"成功选择选项 {value} 在 {selector}")
            return True
            
        except Exception as e:
            logger.error(f"选择选项 {value} 在 {selector} 失败: {e}")
            return False
    
    async def upload_file(self, selector: str, file_path: str, timeout: int = 10000) -> bool:
        """上传文件"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            await self.page.set_input_files(selector, file_path, timeout=timeout)
            logger.info(f"成功上传文件 {file_path} 到 {selector}")
            return True
            
        except Exception as e:
            logger.error(f"上传文件 {file_path} 到 {selector} 失败: {e}")
            return False
    
    async def wait_for_element(self, selector: str, timeout: int = 10000) -> bool:
        """等待元素出现"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            await self.page.wait_for_selector(selector, timeout=timeout)
            logger.info(f"元素 {selector} 已出现")
            return True
            
        except Exception as e:
            logger.error(f"等待元素 {selector} 超时: {e}")
            return False
    
    async def wait_for_page_load(self, timeout: int = 30000) -> bool:
        """等待页面加载完成"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            await self.page.wait_for_load_state('domcontentloaded', timeout=timeout)
            logger.info("页面加载完成")
            return True
            
        except Exception as e:
            logger.error(f"等待页面加载超时: {e}")
            return False
    
    async def scroll_to_element(self, selector: str) -> bool:
        """滚动到指定元素"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            await self.page.locator(selector).scroll_into_view_if_needed()
            logger.info(f"已滚动到元素: {selector}")
            return True
            
        except Exception as e:
            logger.error(f"滚动到元素 {selector} 失败: {e}")
            return False
    
    async def get_element_text(self, selector: str) -> str:
        """获取元素文本"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            text = await self.page.locator(selector).text_content()
            return text or ""
            
        except Exception as e:
            logger.error(f"获取元素 {selector} 文本失败: {e}")
            return ""
    
    async def is_element_visible(self, selector: str) -> bool:
        """检查元素是否可见"""
        try:
            if not self.page:
                raise Exception("浏览器未启动")
            
            return await self.page.locator(selector).is_visible()
            
        except Exception as e:
            logger.error(f"检查元素 {selector} 可见性失败: {e}")
            return False