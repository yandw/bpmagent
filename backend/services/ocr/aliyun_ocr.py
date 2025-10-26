"""
阿里云OCR服务实现
基于阿里云官方SDK
"""
import json
import base64
import logging
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 阿里云SDK导入
from alibabacloud_ocr_api20210707.client import Client as ocr_api20210707Client
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials.models import Config as CredentialConfig
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ocr_api20210707 import models as ocr_api_20210707_models
from alibabacloud_tea_util import models as util_models

from .base import BaseOCRService, OCRResult

logger = logging.getLogger(__name__)


class AliyunOCRService(BaseOCRService):
    """阿里云OCR服务"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 加载环境变量
        load_dotenv()
        
        # 从配置或环境变量获取密钥
        self.access_key_id = (config.get("access_key_id") or 
                             os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID') or 
                             os.getenv('ALIYUN_ACCESS_KEY_ID'))
        self.access_key_secret = (config.get("access_key_secret") or 
                                 os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET') or 
                                 os.getenv('ALIYUN_ACCESS_KEY_SECRET'))
        
        if not self.access_key_id or not self.access_key_secret:
            logger.warning("阿里云OCR配置不完整，将使用Mock服务")
    
    def _create_client(self) -> ocr_api20210707Client:
        """创建阿里云OCR客户端"""
        if not self.access_key_id or not self.access_key_secret:
            raise ValueError("阿里云OCR配置不完整")
        
        # 使用明确的AccessKey配置
        credential_config = CredentialConfig(
            type='access_key',
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret
        )
        credential = CredentialClient(credential_config)
        
        # 配置客户端
        config = open_api_models.Config(
            credential=credential,
            endpoint='ocr-api.cn-hangzhou.aliyuncs.com'
        )
        
        return ocr_api20210707Client(config)
    
    async def recognize_invoice(self, image_data: bytes) -> OCRResult:
        """识别增值税发票"""
        try:
            # 检查配置
            if not self.access_key_id or not self.access_key_secret:
                return OCRResult(
                    success=False,
                    error_message="阿里云OCR配置不完整，请检查access_key_id和access_key_secret",
                    error="阿里云OCR配置不完整，请检查access_key_id和access_key_secret"
                )
            
            # 检查图片大小 (阿里云限制4MB)
            if len(image_data) > 4 * 1024 * 1024:
                return OCRResult(
                    success=False,
                    error_message="图片文件过大，请上传小于4MB的图片",
                    error="图片文件过大，请上传小于4MB的图片"
                )
            
            # 预处理图片
            processed_image = self._preprocess_image(image_data)
            
            # 调用阿里云OCR API
            result = await self._recognize_vat_invoice_sdk(processed_image)
            return result
            
        except Exception as e:
            logger.error(f"阿里云OCR识别异常: {e}")
            return OCRResult(
                success=False,
                error_message=f"OCR识别异常: {str(e)}",
                error=f"OCR识别异常: {str(e)}"
            )
    
    async def extract_text_from_image(self, image_path: str) -> OCRResult:
        """从图片文件中提取文本 (兼容接口)"""
        try:
            # 检查文件是否存在
            import os
            if not os.path.exists(image_path):
                return OCRResult(
                    success=False,
                    error="图片文件不存在"
                )
            
            # 检查文件大小
            file_size = os.path.getsize(image_path)
            if file_size > 4 * 1024 * 1024:  # 4MB
                return OCRResult(
                    success=False,
                    error="图片文件过大，请上传小于4MB的图片"
                )
            
            # 检查文件格式
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
            file_ext = os.path.splitext(image_path)[1].lower()
            if file_ext not in allowed_extensions:
                return OCRResult(
                    success=False,
                    error=f"不支持的图片格式 {file_ext}，请上传 JPG、PNG 或 BMP 格式的图片"
                )
            
            # 读取图片数据
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 调用识别方法
            return await self.recognize_invoice(image_data)
            
        except Exception as e:
            logger.error(f"阿里云OCR文件处理异常: {e}")
            return OCRResult(
                success=False,
                error=f"文件处理异常: {str(e)}"
            )
    
    async def _recognize_vat_invoice_sdk(self, image_data: bytes) -> OCRResult:
        """使用阿里云SDK调用混合发票识别API"""
        try:
            # 创建客户端
            client = self._create_client()
            
            # 构建请求 - 直接使用图片二进制数据
            request = ocr_api_20210707_models.RecognizeMixedInvoicesRequest()
            request.body = image_data
            
            # 调用API
            runtime = util_models.RuntimeOptions()
            response = client.recognize_mixed_invoices_with_options(request, runtime)
            
            # 检查响应
            if response.status_code == 200:
                if response.body and response.body.data:
                    # 解析结果
                    return self._parse_aliyun_sdk_result(response.body.data)
                else:
                    logger.warning("阿里云OCR返回空数据")
                    return OCRResult(
                        success=False,
                        error_message="OCR识别返回空数据",
                        error="OCR识别返回空数据"
                    )
            else:
                logger.error(f"阿里云OCR API调用失败，状态码: {response.status_code}")
                return OCRResult(
                    success=False,
                    error_message=f"API调用失败，状态码: {response.status_code}",
                    error=f"API调用失败，状态码: {response.status_code}"
                )
                
        except Exception as e:
            logger.error(f"阿里云OCR SDK调用异常: {e}")
            return OCRResult(
                success=False,
                error_message=f"SDK调用异常: {str(e)}",
                error=f"SDK调用异常: {str(e)}"
            )
    
    def _parse_aliyun_sdk_result(self, result_data) -> OCRResult:
        """解析阿里云SDK返回结果"""
        try:
            # 检查是否有发票数据
            if not hasattr(result_data, 'invoices') or not result_data.invoices:
                return OCRResult(
                    success=False,
                    error_message="未识别到发票信息",
                    error="未识别到发票信息"
                )
            
            # 取第一张发票的数据
            invoice = result_data.invoices[0]
            
            # 提取发票基本信息
            invoice_info = {
                "invoice_type": getattr(invoice, 'invoice_type', ''),
                "invoice_code": getattr(invoice, 'invoice_code', ''),
                "invoice_number": getattr(invoice, 'invoice_number', ''),
                "invoice_date": getattr(invoice, 'invoice_date', ''),
                "total_amount": getattr(invoice, 'sum_amount', ''),
                "seller_name": getattr(invoice, 'payee_name', ''),
                "buyer_name": getattr(invoice, 'payer_name', ''),
                "tax_amount": getattr(invoice, 'tax_amount', ''),
                "amount_without_tax": getattr(invoice, 'amount_without_tax', '')
            }
            
            # 提取商品明细
            items = []
            if hasattr(invoice, 'items') and invoice.items:
                for item in invoice.items:
                    item_info = {
                        "name": getattr(item, 'item_name', ''),
                        "specification": getattr(item, 'specification', ''),
                        "unit": getattr(item, 'unit', ''),
                        "quantity": getattr(item, 'quantity', ''),
                        "unit_price": getattr(item, 'unit_price', ''),
                        "amount": getattr(item, 'amount', ''),
                        "tax_rate": getattr(item, 'tax_rate', ''),
                        "tax_amount": getattr(item, 'tax_amount', '')
                    }
                    items.append(item_info)
            
            return OCRResult(
                success=True,
                data={
                    "invoice_info": invoice_info,
                    "items": items
                },
                invoice_type=invoice_info.get("invoice_type"),
                invoice_number=invoice_info.get("invoice_number"),
                invoice_date=invoice_info.get("invoice_date"),
                total_amount=self._parse_amount(invoice_info.get("total_amount")),
                tax_amount=self._parse_amount(invoice_info.get("tax_amount")),
                seller_name=invoice_info.get("seller_name"),
                buyer_name=invoice_info.get("buyer_name"),
                items=items,
                confidence=0.95  # SDK调用成功时设置较高置信度
            )
            
        except Exception as e:
            logger.error(f"解析阿里云SDK结果异常: {e}")
            return OCRResult(
                success=False,
                error_message=f"结果解析异常: {str(e)}",
                error=f"结果解析异常: {str(e)}"
            )
    
    def _parse_amount(self, amount_str) -> Optional[float]:
        """解析金额字符串为浮点数"""
        if not amount_str:
            return None
        try:
            # 移除货币符号和空格
            amount_str = str(amount_str).replace('¥', '').replace('￥', '').replace(',', '').strip()
            return float(amount_str)
        except (ValueError, TypeError):
            return None
    
    def _preprocess_image(self, image_data: bytes) -> bytes:
        """预处理图片数据"""
        # 这里可以添加图片预处理逻辑，如格式转换、压缩等
        # 目前直接返回原始数据
        return image_data