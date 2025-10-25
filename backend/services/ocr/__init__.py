"""
OCR服务模块
"""
from .base import BaseOCRService, OCRResult
# from .tesseract_service import TesseractOCRService
from .mock_service import MockOCRService

def create_ocr_service() -> BaseOCRService:
    """创建OCR服务实例"""
    # 暂时使用模拟服务避免复杂的图像处理依赖
    return MockOCRService()


__all__ = ["BaseOCRService", "OCRResult", "BaiduOCRService", "create_ocr_service"]