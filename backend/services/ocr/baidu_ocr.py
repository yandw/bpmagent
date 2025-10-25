import aiohttp
import json
from typing import Dict, Any
from .base import BaseOCRService, OCRResult


class BaiduOCRService(BaseOCRService):
    """百度OCR服务实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.secret_key = config.get('secret_key')
        self.access_token = None
    
    async def _get_access_token(self) -> str:
        """获取百度API访问令牌"""
        if self.access_token:
            return self.access_token
        
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as response:
                result = await response.json()
                self.access_token = result.get("access_token")
                return self.access_token
    
    async def recognize_invoice(self, image_data: bytes) -> OCRResult:
        """
        使用百度OCR识别增值税发票
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            OCRResult: 识别结果
        """
        try:
            # 预处理图片
            processed_image = self._preprocess_image(image_data)
            
            # 获取访问令牌
            access_token = await self._get_access_token()
            
            # 调用百度增值税发票识别API
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice?access_token={access_token}"
            
            # 准备请求数据
            image_base64 = self._image_to_base64(processed_image)
            data = {
                "image": image_base64,
                "location": "true",  # 返回位置信息
                "probability": "true"  # 返回置信度
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    result = await response.json()
            
            # 解析识别结果
            return self._parse_baidu_result(result)
            
        except Exception as e:
            # 返回空结果，包含错误信息
            return OCRResult(
                raw_result={"error": str(e)},
                confidence=0.0
            )
    
    def _parse_baidu_result(self, result: Dict[str, Any]) -> OCRResult:
        """解析百度OCR返回结果"""
        if "error_code" in result:
            return OCRResult(
                raw_result=result,
                confidence=0.0
            )
        
        words_result = result.get("words_result", {})
        
        # 提取基础信息
        invoice_type = words_result.get("InvoiceType", {}).get("words", "")
        invoice_number = words_result.get("InvoiceNum", {}).get("words", "")
        invoice_date = words_result.get("InvoiceDate", {}).get("words", "")
        
        # 提取金额信息
        total_amount_text = words_result.get("TotalAmount", {}).get("words", "")
        tax_amount_text = words_result.get("TotalTax", {}).get("words", "")
        
        total_amount = self._extract_amount(total_amount_text)
        tax_amount = self._extract_amount(tax_amount_text)
        
        # 提取开票方信息
        seller_name = words_result.get("SellerName", {}).get("words", "")
        seller_tax_id = words_result.get("SellerRegisterNum", {}).get("words", "")
        
        # 提取购买方信息
        buyer_name = words_result.get("PurchaserName", {}).get("words", "")
        buyer_tax_id = words_result.get("PurchaserRegisterNum", {}).get("words", "")
        
        # 提取商品明细
        items = []
        commodity_list = words_result.get("CommodityName", [])
        if isinstance(commodity_list, list):
            for item in commodity_list:
                if isinstance(item, dict):
                    items.append({
                        "name": item.get("words", ""),
                        "amount": self._extract_amount(item.get("words", ""))
                    })
        
        # 计算平均置信度
        confidence = 0.0
        confidence_count = 0
        for key, value in words_result.items():
            if isinstance(value, dict) and "probability" in value:
                confidence += value["probability"]["average"]
                confidence_count += 1
        
        if confidence_count > 0:
            confidence = confidence / confidence_count
        
        return OCRResult(
            invoice_type=invoice_type,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            total_amount=total_amount,
            tax_amount=tax_amount,
            seller_name=seller_name,
            seller_tax_id=seller_tax_id,
            buyer_name=buyer_name,
            buyer_tax_id=buyer_tax_id,
            items=items,
            raw_result=result,
            confidence=confidence
        )