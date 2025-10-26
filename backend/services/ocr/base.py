from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import base64
from io import BytesIO
# from PIL import Image  # 暂时注释掉PIL依赖


class OCRResult(BaseModel):
    """OCR识别结果模型"""
    # 识别状态
    success: bool = True  # 识别是否成功
    error_message: Optional[str] = None  # 错误信息
    error: Optional[str] = None  # 错误信息 (兼容属性)
    data: Optional[Dict[str, Any]] = None  # 识别数据 (兼容属性)
    
    # 发票基础信息
    invoice_type: Optional[str] = None  # 发票类型
    invoice_number: Optional[str] = None  # 发票号码
    invoice_date: Optional[str] = None  # 开票日期
    
    # 金额信息
    total_amount: Optional[float] = None  # 合计金额
    tax_amount: Optional[float] = None  # 税额
    
    # 商品明细
    items: List[Dict[str, Any]] = []  # 商品/服务明细
    
    # 开票方信息
    seller_name: Optional[str] = None  # 销售方名称
    seller_tax_id: Optional[str] = None  # 销售方纳税人识别号
    
    # 购买方信息
    buyer_name: Optional[str] = None  # 购买方名称
    buyer_tax_id: Optional[str] = None  # 购买方纳税人识别号
    
    # 原始识别结果
    raw_result: Dict[str, Any] = {}
    
    # 置信度
    confidence: float = 0.0


class BaseOCRService(ABC):
    """OCR服务基础抽象类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def recognize_invoice(self, image_data: bytes) -> OCRResult:
        """
        识别发票
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            OCRResult: 识别结果
        """
        pass
    
    def _image_to_base64(self, image_data: bytes) -> str:
        """将图片数据转换为base64编码"""
        return base64.b64encode(image_data).decode('utf-8')
    
    def _preprocess_image(self, image_data: bytes) -> bytes:
        """预处理图片（可选的图片优化）"""
        try:
            # 暂时跳过图片预处理，直接返回原始数据
            # TODO: 当安装PIL后，可以启用图片预处理功能
            return image_data
            
            # # 打开图片
            # image = Image.open(BytesIO(image_data))
            # 
            # # 转换为RGB模式
            # if image.mode != 'RGB':
            #     image = image.convert('RGB')
            # 
            # # 如果图片太大，进行压缩
            # max_size = (2048, 2048)
            # if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            #     image.thumbnail(max_size, Image.Resampling.LANCZOS)
            # 
            # # 保存处理后的图片
            # output = BytesIO()
            # image.save(output, format='JPEG', quality=85)
            # return output.getvalue()
            
        except Exception:
            # 如果预处理失败，返回原始数据
            return image_data
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """从文本中提取金额"""
        import re
        
        # 匹配金额模式
        patterns = [
            r'[￥¥$]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # ￥123.45
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*元',      # 123.45元
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)',           # 123.45
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    # 移除逗号并转换为浮点数
                    amount_str = matches[0].replace(',', '')
                    return float(amount_str)
                except ValueError:
                    continue
        
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """从文本中提取日期"""
        import re
        
        # 匹配日期模式
        patterns = [
            r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',  # 2024-01-01 或 2024年01月01日
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',          # 01-01-2024
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        return None