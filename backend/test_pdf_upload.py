#!/usr/bin/env python3
"""
测试PDF文件上传功能的简单脚本
"""

import requests
import os

def test_pdf_upload():
    """测试PDF文件上传"""
    # API端点
    url = "http://localhost:8888/api/upload/file"
    
    # 测试PDF文件路径
    pdf_path = "/Users/atomyan/Workspace/BPMAgent/backend/tests/test_data/test_pdf.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"错误：测试PDF文件不存在: {pdf_path}")
        return False
    
    # 准备文件上传
    with open(pdf_path, 'rb') as f:
        files = {
            'file': ('test_pdf.pdf', f, 'application/pdf')
        }
        
        data = {
            'auto_ocr': 'false'  # PDF暂时不进行OCR
        }
        
        # 需要认证头，这里使用测试用户的token
        headers = {
            'Authorization': 'Bearer test_token'  # 实际使用时需要真实token
        }
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                print("PDF上传成功!")
                print(f"文件ID: {result.get('file_id')}")
                print(f"文件名: {result.get('filename')}")
                print(f"内容类型: {result.get('content_type')}")
                return True
            else:
                print(f"PDF上传失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"请求失败: {e}")
            return False

if __name__ == "__main__":
    print("开始测试PDF文件上传...")
    success = test_pdf_upload()
    if success:
        print("✅ PDF上传测试通过")
    else:
        print("❌ PDF上传测试失败")