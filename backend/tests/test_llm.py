#!/usr/bin/env python3
"""
LLM接口测试脚本
测试阿里云通义千问API的连接和功能
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.services.ai import create_ai_service
from backend.core.config import settings


@pytest.mark.asyncio
async def test_ai_service_init():
    """测试AI服务初始化"""
    print("🔧 测试AI服务初始化...")
    ai_service = create_ai_service()
    assert ai_service is not None
    print(f"✅ AI服务初始化成功")
    print(f"   - API Key: {settings.qwen_api_key[:10]}...")
    print(f"   - Base URL: {settings.qwen_base_url}")
    print(f"   - Model: {settings.qwen_model}")
    return ai_service


@pytest.mark.asyncio
async def test_intent_recognition():
    """测试意图识别功能"""
    print("\n🎯 测试意图识别功能...")
    
    ai_service = create_ai_service()
    assert ai_service is not None
    
    test_cases = [
        "我要报销这张发票",
        "帮我填写报销单",
        "上传发票进行报销",
        "你好，我想咨询一下",
        "今天天气怎么样？"
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: '{test_input}'")
        result = await ai_service.recognize_intent(test_input)
        print(f"   识别结果: {result}")
        assert result is not None


@pytest.mark.asyncio
async def test_conversation():
    """测试对话功能"""
    print("\n💬 测试对话功能...")
    
    ai_service = create_ai_service()
    assert ai_service is not None
    
    test_messages = [
        "你好，我是新用户",
        "我想了解报销流程",
        "需要准备哪些材料？"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n对话 {i}: '{message}'")
        response = await ai_service.generate_response(message)
        print(f"   回复: {response}")
        assert response is not None
        assert len(response) > 0


@pytest.mark.asyncio
async def test_web_analysis():
    """测试网页分析功能"""
    print("\n🌐 测试网页分析功能...")
    
    ai_service = create_ai_service()
    assert ai_service is not None
    
    # 创建一个简单的测试图片（1x1像素的PNG）
    import base64
    # 1x1像素透明PNG的base64数据
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    test_image_bytes = base64.b64decode(test_image_b64)
    
    # 模拟网页HTML内容
    mock_html = """
    <html>
        <body>
            <form id="expense-form">
                <input type="text" name="amount" placeholder="金额" />
                <input type="text" name="description" placeholder="描述" />
                <select name="category">
                    <option value="travel">差旅费</option>
                    <option value="meal">餐费</option>
                </select>
                <button type="submit">提交</button>
            </form>
        </body>
    </html>
    """
    
    print("分析模拟报销表单页面...")
    analysis = await ai_service.analyze_webpage(test_image_bytes, mock_html)
    print(f"   页面类型: {analysis.page_type}")
    print(f"   表单字段数量: {len(analysis.form_fields)}")
    print(f"   按钮数量: {len(analysis.buttons)}")
    print(f"   置信度: {analysis.confidence:.2f}")
    assert analysis is not None


# 保留原有的main函数用于直接运行脚本
async def main():
    """主测试函数"""
    print("🚀 开始测试LLM接口...")
    print("=" * 50)
    
    # 检查配置
    if not settings.qwen_api_key or settings.qwen_api_key == "your-qwen-api-key":
        print("❌ 错误: 请在.env文件中配置有效的QWEN_API_KEY")
        return
    
    # 测试AI服务初始化
    ai_service = create_ai_service()
    if not ai_service:
        return
    
    print("\n" + "=" * 50)
    print("🎉 LLM接口测试完成!")


if __name__ == "__main__":
    asyncio.run(main())