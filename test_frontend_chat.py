#!/usr/bin/env python3
"""
前端聊天功能测试脚本
模拟前端页面发送"你好，智能体"消息并等待大模型回复
"""

import asyncio
import websockets
import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8888"

async def test_frontend_chat():
    """测试前端聊天功能"""
    print("🚀 开始前端聊天功能测试...")
    
    try:
        # 1. 用户登录
        print("\n🔐 用户登录...")
        login_data = {
            "username": "chattest",
            "password": "chattest123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"❌ 登录失败: {response.status_code} - {response.text}")
            return
        
        login_result = response.json()
        access_token = login_result["access_token"]
        user_info = login_result["user"]
        print(f"✅ 登录成功，用户: {user_info['username']}")
        
        # 2. 创建聊天会话
        print("\n💬 创建聊天会话...")
        session_data = {
            "name": f"前端测试会话_{int(datetime.now().timestamp())}"
        }
        
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(f"{BASE_URL}/api/chat/sessions", json=session_data, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ 创建会话失败: {response.status_code} - {response.text}")
            return
        
        session_result = response.json()
        session_id = session_result["session_id"]  # 使用正确的字段名
        print(f"✅ 会话创建成功，会话ID: {session_id}")
        
        # 3. 连接WebSocket
        print("\n🔌 连接WebSocket...")
        ws_url = f"ws://localhost:8888/api/chat/ws/{session_id}?token={access_token}"
        
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket连接已建立")
            
            # 等待初始欢迎消息
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                welcome_data = json.loads(welcome_msg)
                print(f"📨 收到欢迎消息: {welcome_data.get('content', '')[:50]}...")
            except asyncio.TimeoutError:
                print("⚠️ 未收到欢迎消息")
            
            # 4. 发送测试消息："你好，智能体"
            print("\n📤 发送消息: '你好，智能体'")
            test_message = {
                "message": "你好，智能体",
                "type": "text"
            }
            
            await websocket.send(json.dumps(test_message))
            print("✅ 消息发送成功")
            
            # 5. 等待大模型回复
            print("\n⏳ 等待大模型回复...")
            response_count = 0
            max_responses = 5  # 最多等待5个响应
            
            while response_count < max_responses:
                try:
                    response_msg = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    response_data = json.loads(response_msg)
                    response_count += 1
                    
                    msg_type = response_data.get('type', 'unknown')
                    content = response_data.get('content', '')
                    
                    if msg_type == 'status':
                        print(f"📊 状态消息: {content}")
                    elif msg_type == 'message':
                        print(f"🤖 AI回复: {content}")
                        intent = response_data.get('intent', '')
                        if intent:
                            print(f"   意图识别: {intent}")
                        
                        # 如果收到正常回复消息，测试成功
                        if content and not content.startswith("抱歉"):
                            print("\n🎉 测试成功！收到了大模型的正常回复")
                            break
                        elif "错误" in content or "抱歉" in content:
                            print(f"⚠️ 收到错误回复: {content}")
                    else:
                        print(f"📨 其他消息 ({msg_type}): {content}")
                        
                except asyncio.TimeoutError:
                    print("⏰ 等待响应超时")
                    break
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析错误: {e}")
                    break
            
            print(f"\n📊 总共收到 {response_count} 个响应")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🔚 测试结束")

if __name__ == "__main__":
    asyncio.run(test_frontend_chat())