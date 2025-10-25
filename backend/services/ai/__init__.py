from .base import BaseAIService, IntentResult, IntentType, WebPageAnalysis, AIMessage
from .qwen_service import QwenAIService
from backend.core.config import settings


def create_ai_service() -> BaseAIService:
    """
    根据配置创建AI服务实例
    
    Returns:
        BaseAIService: AI服务实例
    """
    config = {
        'api_key': settings.qwen_api_key,
        'base_url': settings.qwen_base_url,
        'model': settings.qwen_model
    }
    
    return QwenAIService(config)


__all__ = [
    "BaseAIService", 
    "IntentResult", 
    "IntentType", 
    "WebPageAnalysis", 
    "AIMessage",
    "QwenAIService", 
    "create_ai_service"
]