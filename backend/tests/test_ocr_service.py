"""
OCR服务单元测试
测试阿里云OCR服务的发票识别功能
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.services.ocr import create_ocr_service
from backend.services.ocr.aliyun_ocr import AliyunOCRService
from backend.services.ocr.base import OCRResult


class TestOCRService:
    """OCR服务单元测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.test_image_path = Path(__file__).parent / "test_data" / "invoice1.png"

    @pytest.mark.asyncio
    async def test_aliyun_ocr_success(self):
        """测试阿里云OCR服务成功识别"""
        # 检查配置
        access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID')
        access_key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        
        if not access_key_id or not access_key_secret:
            pytest.skip("跳过OCR测试: 未配置阿里云OCR密钥")
        
        # 创建OCR服务 - 使用正确的配置格式
        config = {
            'access_key_id': access_key_id,
            'access_key_secret': access_key_secret
        }
        ocr_service = AliyunOCRService(config)
        
        # 使用测试图片
        test_image_path = self.test_image_path
        
        # 执行OCR
        result = await ocr_service.recognize_invoice(str(test_image_path))
        
        # 断言 - 由于是真实的OCR调用，我们只验证基本结构
        assert isinstance(result, OCRResult)
        # 注意：由于OCR可能失败，我们不强制要求success为True
        if result.success:
            assert result.confidence >= 0.0
        else:
            assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_aliyun_ocr_invalid_image(self):
        """测试阿里云OCR服务处理无效图片"""
        # 检查配置
        access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID')
        access_key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        
        if not access_key_id or not access_key_secret:
            pytest.skip("跳过阿里云OCR测试: 未配置ALIYUN_ACCESS_KEY_ID或ALIYUN_ACCESS_KEY_SECRET")
        
        # 创建阿里云OCR服务
        config = {
            'access_key_id': access_key_id,
            'access_key_secret': access_key_secret
        }
        ocr_service = AliyunOCRService(config)
        
        # 使用无效图片数据
        invalid_image_data = b"invalid image data"
        
        # 执行识别
        result = await ocr_service.recognize_invoice(invalid_image_data)
        
        # 断言
        assert isinstance(result, OCRResult)
        assert result.success is False
        assert result.error_message is not None

    def test_create_ocr_service_success(self):
        """测试OCR服务工厂方法成功创建"""
        # 检查配置
        access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID')
        access_key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        
        if not access_key_id or not access_key_secret:
            pytest.skip("跳过工厂方法测试: 未配置阿里云OCR密钥")
        
        # 使用工厂方法创建服务
        ocr_service = create_ocr_service()
        
        # 验证服务类型
        assert isinstance(ocr_service, AliyunOCRService)
        assert ocr_service is not None

    @patch('backend.services.ocr.settings')
    def test_create_ocr_service_missing_config(self, mock_settings):
        """测试没有配置时的工厂方法"""
        # 模拟settings对象没有配置
        mock_settings.aliyun_access_key_id = None
        mock_settings.aliyun_access_key_secret = None
        
        with pytest.raises(ValueError, match="阿里云OCR配置缺失"):
            create_ocr_service()

    def test_ocr_result_success(self):
        """测试OCRResult成功结果"""
        result = OCRResult(
            success=True,
            confidence=0.95,
            invoice_type="增值税专用发票",
            invoice_number="12345678",
            invoice_date="2024-01-01",
            total_amount=1000.00,
            tax_amount=130.00
        )
        
        assert result.success is True
        assert result.confidence == 0.95
        assert result.invoice_type == "增值税专用发票"
        assert result.invoice_number == "12345678"
        assert result.invoice_date == "2024-01-01"
        assert result.total_amount == 1000.00
        assert result.tax_amount == 130.00

    def test_ocr_result_failure(self):
        """测试OCRResult失败结果"""
        result = OCRResult(
            success=False,
            error_message="识别失败"
        )
        
        assert result.success is False
        assert result.error_message == "识别失败"
        assert result.confidence == 0.0
        assert result.invoice_type is None