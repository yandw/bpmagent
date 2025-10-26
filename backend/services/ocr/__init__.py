"""
OCR服务模块
"""
from .base import BaseOCRService, OCRResult
from .aliyun_ocr import AliyunOCRService
from backend.core.config import settings

def create_ocr_service() -> BaseOCRService:
    """创建OCR服务实例 - 只支持阿里云OCR"""
    if not settings.aliyun_access_key_id or not settings.aliyun_access_key_secret:
        raise ValueError("阿里云OCR配置缺失：需要设置ALIYUN_ACCESS_KEY_ID和ALIYUN_ACCESS_KEY_SECRET")
    
    # 使用阿里云OCR服务
    config = {
        'access_key_id': settings.aliyun_access_key_id,
        'access_key_secret': settings.aliyun_access_key_secret
    }
    return AliyunOCRService(config)


__all__ = ["BaseOCRService", "OCRResult", "AliyunOCRService", "create_ocr_service"]