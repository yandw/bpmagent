# -*- coding: utf-8 -*-
"""
增强版阿里云OCR测试程序
基于官方sample.py，添加了图片数据和环境变量配置
"""
import os
import sys
import base64
from typing import List
from dotenv import load_dotenv

from alibabacloud_ocr_api20210707.client import Client as ocr_api20210707Client
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials.models import Config as CredentialConfig
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ocr_api20210707 import models as ocr_api_20210707_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_console.client import Client as ConsoleClient
from alibabacloud_tea_util.client import Client as UtilClient


class EnhancedSample:
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        
    @staticmethod
    def create_client() -> ocr_api20210707Client:
        """
        使用凭据初始化账号Client
        @return: Client
        @throws Exception
        """
        # 加载环境变量
        load_dotenv()
        
        # 从环境变量获取密钥 - 支持多种环境变量名称
        access_key_id = (os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID') or 
                        os.getenv('ALIYUN_ACCESS_KEY_ID'))
        access_key_secret = (os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET') or 
                           os.getenv('ALIYUN_ACCESS_KEY_SECRET'))
        
        print(f"Access Key ID: {'已配置' if access_key_id else '未配置'} ({access_key_id[:10] + '...' if access_key_id else 'None'})")
        print(f"Access Key Secret: {'已配置' if access_key_secret else '未配置'} ({'***' if access_key_secret else 'None'})")
        
        if access_key_id and access_key_secret:
            # 使用明确的AccessKey配置
            credential_config = CredentialConfig(
                type='access_key',
                access_key_id=access_key_id,
                access_key_secret=access_key_secret
            )
            credential = CredentialClient(credential_config)
        else:
            # 使用默认凭据链
            credential = CredentialClient()
        
        config = open_api_models.Config(
            credential=credential
        )
        # Endpoint 请参考 https://api.aliyun.com/product/ocr-api
        config.endpoint = f'ocr-api.cn-hangzhou.aliyuncs.com'
        return ocr_api20210707Client(config)

    @staticmethod
    def load_test_image() -> bytes:
        """
        加载测试图片
        @return: 图片的二进制数据
        """
        # 使用绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        test_image_path = os.path.join(project_root, "backend/tests/test_data/test_invoice.jpg")
        
        if not os.path.exists(test_image_path):
            raise FileNotFoundError(f"测试图片不存在: {test_image_path}")
        
        print(f"测试图片: {test_image_path}")
        print(f"图片大小: {os.path.getsize(test_image_path)} bytes")
        
        with open(test_image_path, 'rb') as f:
            image_data = f.read()
        
        return image_data

    @staticmethod
    def main(args: List[str]) -> None:
        """
        同步方式测试OCR
        """
        print("="*60)
        print(" 增强版阿里云OCR测试程序 - 同步调用")
        print("="*60)
        
        try:
            # 创建客户端
            client = EnhancedSample.create_client()
            
            # 加载测试图片
            image_data = EnhancedSample.load_test_image()
            
            # 创建请求对象
            recognize_mixed_invoices_request = ocr_api_20210707_models.RecognizeMixedInvoicesRequest()
            # 设置图片数据
            recognize_mixed_invoices_request.body = image_data
            
            runtime = util_models.RuntimeOptions()
            
            print("\n开始发送OCR请求...")
            
            # 调用API
            resp = client.recognize_mixed_invoices_with_options(recognize_mixed_invoices_request, runtime)
            
            print("\n" + "="*60)
            print(" API调用成功")
            print("="*60)
            
            # 打印响应
            response_json = UtilClient.to_jsonstring(resp)
            print("响应内容:")
            print(response_json)
            
            # 保存结果到文件
            with open("poc_ocr_result.json", "w", encoding="utf-8") as f:
                f.write(response_json)
            print(f"\n结果已保存到: poc_ocr_result.json")
            
        except Exception as error:
            print("\n" + "="*60)
            print(" API调用失败")
            print("="*60)
            
            # 错误 message
            print(f"错误信息: {error}")
            
            # 如果有详细错误信息
            if hasattr(error, 'message'):
                print(f"详细错误: {error.message}")
            
            # 诊断地址
            if hasattr(error, 'data') and error.data and error.data.get("Recommend"):
                print(f"诊断地址: {error.data.get('Recommend')}")
            
            # 保存错误信息
            error_info = {
                "error": str(error),
                "message": getattr(error, 'message', None),
                "recommend": getattr(error, 'data', {}).get('Recommend') if hasattr(error, 'data') and error.data else None
            }
            
            with open("poc_ocr_error.json", "w", encoding="utf-8") as f:
                import json
                json.dump(error_info, f, indent=2, ensure_ascii=False)
            print(f"错误信息已保存到: poc_ocr_error.json")

    @staticmethod
    async def main_async(args: List[str]) -> None:
        """
        异步方式测试OCR
        """
        print("="*60)
        print(" 增强版阿里云OCR测试程序 - 异步调用")
        print("="*60)
        
        try:
            # 创建客户端
            client = EnhancedSample.create_client()
            
            # 加载测试图片
            image_data = EnhancedSample.load_test_image()
            
            # 创建请求对象
            recognize_mixed_invoices_request = ocr_api_20210707_models.RecognizeMixedInvoicesRequest()
            # 设置图片数据
            recognize_mixed_invoices_request.body = image_data
            
            runtime = util_models.RuntimeOptions()
            
            print("\n开始发送异步OCR请求...")
            
            # 异步调用API
            resp = await client.recognize_mixed_invoices_with_options_async(recognize_mixed_invoices_request, runtime)
            
            print("\n" + "="*60)
            print(" 异步API调用成功")
            print("="*60)
            
            # 打印响应
            response_json = UtilClient.to_jsonstring(resp)
            print("响应内容:")
            print(response_json)
            
            # 保存结果到文件
            with open("poc_ocr_async_result.json", "w", encoding="utf-8") as f:
                f.write(response_json)
            print(f"\n异步结果已保存到: poc_ocr_async_result.json")
            
        except Exception as error:
            print("\n" + "="*60)
            print(" 异步API调用失败")
            print("="*60)
            
            # 错误 message
            print(f"错误信息: {error}")
            
            # 如果有详细错误信息
            if hasattr(error, 'message'):
                print(f"详细错误: {error.message}")
            
            # 诊断地址
            if hasattr(error, 'data') and error.data and error.data.get("Recommend"):
                print(f"诊断地址: {error.data.get('Recommend')}")


def test_sync():
    """测试同步调用"""
    EnhancedSample.main([])


async def test_async():
    """测试异步调用"""
    await EnhancedSample.main_async([])


if __name__ == '__main__':
    import asyncio
    
    print("选择测试模式:")
    print("1. 同步调用")
    print("2. 异步调用")
    print("3. 两种都测试")
    
    choice = input("请输入选择 (1/2/3，默认1): ").strip() or "1"
    
    if choice == "1":
        test_sync()
    elif choice == "2":
        asyncio.run(test_async())
    elif choice == "3":
        test_sync()
        print("\n" + "="*60)
        print(" 开始异步测试")
        print("="*60)
        asyncio.run(test_async())
    else:
        print("无效选择，使用默认同步调用")
        test_sync()