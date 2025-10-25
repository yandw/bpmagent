#!/usr/bin/env python3
"""
LLM接口测试脚本
测试阿里云通义千问API的连接和功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.services.ai import create_ai_service
from backend.core.config import settings


async def test_ai_service_init():
    """测试AI服务初始化"""
    print("🔧 测试AI服务初始化...")
    try:
        ai_service = create_ai_service()
        print(f"✅ AI服务初始化成功")
        print(f"   - API Key: {settings.qwen_api_key[:10]}...")
        print(f"   - Base URL: {settings.qwen_base_url}")
        print(f"   - Model: {settings.qwen_model}")
        return ai_service
    except Exception as e:
        print(f"❌ AI服务初始化失败: {e}")
        return None


async def test_intent_recognition(ai_service):
    """测试意图识别功能"""
    print("\n🎯 测试意图识别功能...")
    
    test_cases = [
        "我要报销这张发票",
        "帮我填写报销单",
        "上传发票进行报销",
        "你好，我想咨询一下",
        "今天天气怎么样？"
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        try:
            print(f"\n测试用例 {i}: '{test_input}'")
            result = await ai_service.recognize_intent(test_input)
            print(f"   意图: {result.intent}")
            print(f"   置信度: {result.confidence:.2f}")
            print(f"   实体: {result.entities}")
        except Exception as e:
            print(f"   ❌ 错误: {e}")


async def test_conversation(ai_service):
    """测试对话生成功能"""
    print("\n💬 测试对话生成功能...")
    
    test_messages = [
        "你好，我是BPM助手的用户",
        "我想了解如何使用报销功能",
        "请帮我分析这张发票的内容"
    ]
    
    for i, message in enumerate(test_messages, 1):
        try:
            print(f"\n对话测试 {i}: '{message}'")
            response = await ai_service.generate_response(message)
            print(f"   回复: {response}")
        except Exception as e:
            print(f"   ❌ 错误: {e}")


async def test_web_analysis(ai_service):
    """测试网页分析功能"""
    print("\n🌐 测试网页分析功能...")
    
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
    
    try:
        print("分析模拟报销表单页面...")
        analysis = await ai_service.analyze_webpage(test_image_bytes, mock_html)
        print(f"   页面类型: {analysis.page_type}")
        print(f"   表单字段数量: {len(analysis.form_fields)}")
        print(f"   按钮数量: {len(analysis.buttons)}")
        print(f"   置信度: {analysis.confidence:.2f}")
        
        # 构建可操作元素列表用于测试
        actionable_elements = []
        for field in analysis.form_fields:
            actionable_elements.append({
                'element_type': 'input',
                'selector': f"input[name='{field.get('name', '')}']"
            })
        for button in analysis.buttons:
            actionable_elements.append({
                'element_type': 'button', 
                'selector': f"button:contains('{button.get('text', '')}')"
            })
        
        print(f"   可操作元素数量: {len(actionable_elements)}")
        for element in actionable_elements:
            print(f"     - {element['element_type']}: {element['selector']}")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")


async def main():
    """主测试函数"""
    print("🚀 开始测试LLM接口...")
    print("=" * 50)
    
    # 检查配置
    if not settings.qwen_api_key or settings.qwen_api_key == "your-qwen-api-key":
        print("❌ 错误: 请在.env文件中配置有效的QWEN_API_KEY")
        return
    
    # 测试AI服务初始化
    ai_service = await test_ai_service_init()
    if not ai_service:
        return
    
    # 测试各项功能
    await test_intent_recognition(ai_service)
    await test_conversation(ai_service)
    await test_web_analysis(ai_service)
    
    print("\n" + "=" * 50)
    print("🎉 LLM接口测试完成!")


if __name__ == "__main__":
    asyncio.run(main())