"""
模拟OCR服务 - 用于开发和测试
"""
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime
import base64

class MockOCRService:
    """模拟OCR服务"""
    
    def __init__(self):
        self.is_initialized = False
        
    async def initialize(self):
        """初始化OCR服务"""
        await asyncio.sleep(0.1)  # 模拟初始化延迟
        self.is_initialized = True
        print("Mock OCR Service initialized")
        
    async def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """从图片中提取文本"""
        await asyncio.sleep(0.2)  # 模拟OCR处理延迟
        
        # 模拟OCR结果
        mock_text = f"""
        Mock OCR Result for: {image_path}
        
        Sample Form Fields Detected:
        - Username: [text field]
        - Password: [password field]
        - Email: user@example.com
        - Submit Button: [clickable]
        
        Confidence: 95%
        Processing Time: 0.2s
        """
        
        return {
            "success": True,
            "text": mock_text.strip(),
            "confidence": 0.95,
            "processing_time": 0.2,
            "detected_fields": [
                {
                    "type": "text_field",
                    "label": "Username",
                    "coordinates": {"x": 100, "y": 150, "width": 200, "height": 30}
                },
                {
                    "type": "password_field", 
                    "label": "Password",
                    "coordinates": {"x": 100, "y": 200, "width": 200, "height": 30}
                },
                {
                    "type": "email_field",
                    "label": "Email",
                    "value": "user@example.com",
                    "coordinates": {"x": 100, "y": 250, "width": 200, "height": 30}
                },
                {
                    "type": "button",
                    "label": "Submit",
                    "coordinates": {"x": 150, "y": 300, "width": 100, "height": 40}
                }
            ]
        }
        
    async def extract_text_from_base64(self, base64_image: str) -> Dict[str, Any]:
        """从base64编码的图片中提取文本"""
        await asyncio.sleep(0.2)  # 模拟OCR处理延迟
        
        # 模拟解析base64图片
        try:
            # 简单验证base64格式
            if base64_image.startswith('data:image'):
                image_data = base64_image.split(',')[1]
            else:
                image_data = base64_image
                
            # 模拟OCR结果
            mock_text = """
            Mock OCR Result from Base64 Image
            
            Detected Text:
            - Login Form
            - Username: [input field]
            - Password: [input field] 
            - Remember me: [checkbox]
            - Sign In: [button]
            
            Additional Elements:
            - Forgot Password? [link]
            - Create Account [link]
            """
            
            return {
                "success": True,
                "text": mock_text.strip(),
                "confidence": 0.92,
                "processing_time": 0.2,
                "image_size": len(image_data),
                "detected_elements": [
                    {"type": "heading", "text": "Login Form"},
                    {"type": "input", "label": "Username"},
                    {"type": "input", "label": "Password"},
                    {"type": "checkbox", "label": "Remember me"},
                    {"type": "button", "text": "Sign In"},
                    {"type": "link", "text": "Forgot Password?"},
                    {"type": "link", "text": "Create Account"}
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to process base64 image: {str(e)}",
                "message": "Invalid base64 image format"
            }
            
    async def analyze_form_structure(self, image_path: str) -> Dict[str, Any]:
        """分析表单结构"""
        await asyncio.sleep(0.15)  # 模拟分析延迟
        
        return {
            "success": True,
            "form_structure": {
                "form_type": "login_form",
                "fields": [
                    {
                        "id": "username",
                        "type": "text",
                        "label": "Username",
                        "required": True,
                        "selector": "#username"
                    },
                    {
                        "id": "password", 
                        "type": "password",
                        "label": "Password",
                        "required": True,
                        "selector": "#password"
                    }
                ],
                "buttons": [
                    {
                        "id": "submit",
                        "type": "submit",
                        "text": "Sign In",
                        "selector": "#submit-btn"
                    }
                ],
                "links": [
                    {
                        "text": "Forgot Password?",
                        "href": "/forgot-password"
                    }
                ]
            },
            "confidence": 0.88,
            "processing_time": 0.15
        }
        
    async def extract_table_data(self, image_path: str) -> Dict[str, Any]:
        """提取表格数据"""
        await asyncio.sleep(0.25)  # 模拟表格处理延迟
        
        return {
            "success": True,
            "table_data": {
                "headers": ["Name", "Email", "Status", "Actions"],
                "rows": [
                    ["John Doe", "john@example.com", "Active", "Edit | Delete"],
                    ["Jane Smith", "jane@example.com", "Inactive", "Edit | Delete"],
                    ["Bob Johnson", "bob@example.com", "Active", "Edit | Delete"]
                ],
                "row_count": 3,
                "column_count": 4
            },
            "confidence": 0.90,
            "processing_time": 0.25
        }
        
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "is_initialized": self.is_initialized,
            "service_type": "mock",
            "supported_formats": ["jpg", "png", "gif", "bmp", "base64"],
            "capabilities": [
                "text_extraction",
                "form_analysis", 
                "table_extraction",
                "element_detection"
            ]
        }
        
    async def cleanup(self):
        """清理资源"""
        self.is_initialized = False
        print("Mock OCR Service cleaned up")