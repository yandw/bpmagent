from abc import ABC, abstractmethod
from typing import Dict, List, Any
from pydantic import BaseModel
from enum import Enum


class IntentType(str, Enum):
    """意图类型枚举"""
    EXPENSE_REPORT = "expense_report"  # 报销申请
    LEAVE_REQUEST = "leave_request"    # 请假申请
    PURCHASE_REQUEST = "purchase_request"  # 采购申请
    CONTRACT_APPROVAL = "contract_approval"  # 合同审批
    FORM_FILLING = "form_filling"  # 表单填写
    OCR_PROCESSING = "ocr_processing"  # OCR处理
    QUESTION_ANSWERING = "question_answering"  # 问答
    DATA_EXTRACTION = "data_extraction"  # 数据提取
    UNKNOWN = "unknown"  # 未知意图


class AIMessage(BaseModel):
    """AI消息模型"""
    role: str  # "user", "assistant", "system"
    content: str
    metadata: Dict[str, Any] = {}


class IntentResult(BaseModel):
    """意图识别结果"""
    intent: IntentType
    confidence: float
    entities: Dict[str, Any] = {}  # 提取的实体信息
    context: Dict[str, Any] = {}   # 上下文信息


class WebPageAnalysis(BaseModel):
    """网页分析结果"""
    page_type: str  # "login", "form", "success", "error"
    form_fields: List[Dict[str, Any]] = []  # 表单字段信息
    required_fields: List[str] = []  # 必填字段
    buttons: List[Dict[str, Any]] = []  # 按钮信息
    error_messages: List[str] = []  # 错误信息
    success_indicators: List[str] = []  # 成功指示器
    confidence: float = 0.0
    actionable_elements: List[Dict[str, Any]] = []  # 可操作元素列表


class BaseAIService(ABC):
    """AI服务基础抽象类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.conversation_history: List[AIMessage] = []
    
    @abstractmethod
    async def recognize_intent(self, user_input: str, context: Dict[str, Any] = None) -> IntentResult:
        """
        识别用户意图
        
        Args:
            user_input: 用户输入文本
            context: 上下文信息（如OCR结果、历史对话等）
            
        Returns:
            IntentResult: 意图识别结果
        """
        pass
    
    @abstractmethod
    async def analyze_webpage(self, screenshot: bytes, html_content: str = None) -> WebPageAnalysis:
        """
        分析网页内容
        
        Args:
            screenshot: 网页截图
            html_content: 网页HTML内容（可选）
            
        Returns:
            WebPageAnalysis: 网页分析结果
        """
        pass
    
    @abstractmethod
    async def generate_question(self, missing_fields: List[str], context: Dict[str, Any]) -> str:
        """
        生成追问问题
        
        Args:
            missing_fields: 缺失的字段列表
            context: 上下文信息
            
        Returns:
            str: 生成的问题
        """
        pass
    
    @abstractmethod
    async def extract_answer(self, user_response: str, question_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        从用户回复中提取答案
        
        Args:
            user_response: 用户回复
            question_context: 问题上下文
            
        Returns:
            Dict[str, Any]: 提取的答案
        """
        pass
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加消息到对话历史"""
        message = AIMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.conversation_history.append(message)
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
    
    def get_recent_messages(self, count: int = 10) -> List[AIMessage]:
        """获取最近的消息"""
        return self.conversation_history[-count:] if count > 0 else self.conversation_history