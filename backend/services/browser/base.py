from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel
from enum import Enum


class ElementType(str, Enum):
    """页面元素类型"""
    INPUT = "input"
    SELECT = "select"
    BUTTON = "button"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTAREA = "textarea"
    FILE_UPLOAD = "file_upload"
    LINK = "link"


class PageElement(BaseModel):
    """页面元素模型"""
    element_type: ElementType
    selector: str  # CSS选择器或XPath
    name: str  # 元素名称/标签
    value: Optional[str] = None  # 当前值
    required: bool = False  # 是否必填
    options: List[str] = []  # 下拉框选项
    placeholder: Optional[str] = None  # 占位符文本


class BrowserAction(BaseModel):
    """浏览器操作模型"""
    action_type: str  # "click", "input", "select", "upload", "wait"
    selector: str  # 目标元素选择器
    value: Optional[str] = None  # 操作值
    timeout: int = 5000  # 超时时间（毫秒）


class PageState(BaseModel):
    """页面状态模型"""
    url: str
    title: str
    page_type: str  # "login", "form", "success", "error"
    elements: List[PageElement] = []
    screenshot: Optional[bytes] = None
    html_content: Optional[str] = None


class BaseBrowserService(ABC):
    """浏览器自动化服务基础抽象类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.browser = None
        self.page = None
        self.current_state: Optional[PageState] = None
    
    @abstractmethod
    async def start_browser(self) -> bool:
        """启动浏览器"""
        pass
    
    @abstractmethod
    async def close_browser(self):
        """关闭浏览器"""
        pass
    
    @abstractmethod
    async def navigate_to(self, url: str) -> bool:
        """导航到指定URL"""
        pass
    
    @abstractmethod
    async def take_screenshot(self) -> bytes:
        """截取当前页面截图"""
        pass
    
    @abstractmethod
    async def get_page_html(self) -> str:
        """获取当前页面HTML"""
        pass
    
    @abstractmethod
    async def find_elements(self, selector: str) -> List[PageElement]:
        """查找页面元素"""
        pass
    
    @abstractmethod
    async def click_element(self, selector: str, timeout: int = 5000) -> bool:
        """点击元素"""
        pass
    
    @abstractmethod
    async def input_text(self, selector: str, text: str, timeout: int = 5000) -> bool:
        """输入文本"""
        pass
    
    @abstractmethod
    async def select_option(self, selector: str, value: str, timeout: int = 5000) -> bool:
        """选择下拉框选项"""
        pass
    
    @abstractmethod
    async def upload_file(self, selector: str, file_path: str, timeout: int = 10000) -> bool:
        """上传文件"""
        pass
    
    @abstractmethod
    async def wait_for_element(self, selector: str, timeout: int = 10000) -> bool:
        """等待元素出现"""
        pass
    
    @abstractmethod
    async def wait_for_page_load(self, timeout: int = 30000) -> bool:
        """等待页面加载完成"""
        pass
    
    async def get_current_state(self) -> PageState:
        """获取当前页面状态"""
        if not self.page:
            raise Exception("浏览器未启动或页面未加载")
        
        url = self.page.url
        title = await self.page.title()
        screenshot = await self.take_screenshot()
        html_content = await self.get_page_html()
        
        # 分析页面元素
        elements = await self._analyze_page_elements()
        
        # 判断页面类型
        page_type = await self._determine_page_type(html_content, elements)
        
        self.current_state = PageState(
            url=url,
            title=title,
            page_type=page_type,
            elements=elements,
            screenshot=screenshot,
            html_content=html_content
        )
        
        return self.current_state
    
    async def _analyze_page_elements(self) -> List[PageElement]:
        """分析页面元素"""
        elements = []
        
        # 查找输入框
        input_elements = await self.find_elements('input')
        elements.extend(input_elements)
        
        # 查找下拉框
        select_elements = await self.find_elements('select')
        elements.extend(select_elements)
        
        # 查找按钮
        button_elements = await self.find_elements('button, input[type="submit"]')
        elements.extend(button_elements)
        
        # 查找文本域
        textarea_elements = await self.find_elements('textarea')
        elements.extend(textarea_elements)
        
        return elements
    
    async def _determine_page_type(self, html_content: str, elements: List[PageElement]) -> str:
        """判断页面类型"""
        html_lower = html_content.lower()
        
        # 检查是否为登录页
        if any(keyword in html_lower for keyword in ['login', '登录', 'password', '密码']):
            return "login"
        
        # 检查是否为成功页
        if any(keyword in html_lower for keyword in ['success', '成功', 'complete', '完成']):
            return "success"
        
        # 检查是否为错误页
        if any(keyword in html_lower for keyword in ['error', '错误', 'fail', '失败']):
            return "error"
        
        # 检查是否为表单页
        form_elements = [e for e in elements if e.element_type in [ElementType.INPUT, ElementType.SELECT, ElementType.TEXTAREA]]
        if len(form_elements) > 2:
            return "form"
        
        return "unknown"
    
    async def execute_actions(self, actions: List[BrowserAction]) -> List[bool]:
        """执行一系列浏览器操作"""
        results = []
        
        for action in actions:
            try:
                if action.action_type == "click":
                    result = await self.click_element(action.selector, action.timeout)
                elif action.action_type == "input":
                    result = await self.input_text(action.selector, action.value, action.timeout)
                elif action.action_type == "select":
                    result = await self.select_option(action.selector, action.value, action.timeout)
                elif action.action_type == "upload":
                    result = await self.upload_file(action.selector, action.value, action.timeout)
                elif action.action_type == "wait":
                    result = await self.wait_for_element(action.selector, action.timeout)
                else:
                    result = False
                
                results.append(result)
                
                # 如果操作失败，可以选择继续或停止
                if not result:
                    print(f"操作失败: {action.action_type} {action.selector}")
                
            except Exception as e:
                print(f"执行操作时出错: {e}")
                results.append(False)
        
        return results