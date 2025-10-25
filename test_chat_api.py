#!/usr/bin/env python3
"""
测试前端调用后端chat接口的脚本
模拟前端的完整流程：登录 -> 创建会话 -> 发送消息
"""

import requests
import json
import time
import websocket
import threading
from typing import Optional

class ChatAPITester:
    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.session_id: Optional[str] = None
        self.ws: Optional[websocket.WebSocket] = None
        
    def login(self, username: str = "test@example.com", password: str = "testpassword") -> bool:
        """登录获取token"""
        print("🔐 开始登录...")
        
        # 首先尝试注册用户（如果不存在）
        register_data = {
            "username": username,
            "email": username,
            "password": password
        }
        
        try:
            register_response = requests.post(f"{self.base_url}/api/auth/register", json=register_data)
            if register_response.status_code == 200:
                print("✅ 用户注册成功")
            else:
                print("ℹ️ 用户可能已存在，继续登录...")
        except Exception as e:
            print(f"注册请求失败: {e}")
        
        # 登录
        login_data = {
            "username": "chattest",
            "password": "chattest123"
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/auth/login", json=login_data)
            if response.status_code == 200:
                result = response.json()
                self.token = result.get("access_token")
                print(f"✅ 登录成功，获取token: {self.token[:20]}...")
                return True
            else:
                print(f"❌ 登录失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 登录请求失败: {e}")
            return False
    
    def create_session(self) -> bool:
        """创建聊天会话"""
        if not self.token:
            print("❌ 未登录，无法创建会话")
            return False
            
        print("💬 创建聊天会话...")
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        session_data = {
            "session_name": f"测试会话_{int(time.time())}",
            "target_url": "https://example.com"
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/chat/sessions", 
                                   json=session_data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                self.session_id = result.get("session_id")
                print(f"✅ 会话创建成功，会话ID: {self.session_id}")
                print(f"   会话名称: {result.get('session_name')}")
                print(f"   创建时间: {result.get('created_at')}")
                return True
            else:
                print(f"❌ 创建会话失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 创建会话请求失败: {e}")
            return False
    
    def get_sessions(self) -> bool:
        """获取用户的所有会话"""
        if not self.token:
            print("❌ 未登录，无法获取会话列表")
            return False
            
        print("📋 获取会话列表...")
        
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            response = requests.get(f"{self.base_url}/api/chat/sessions", headers=headers)
            if response.status_code == 200:
                sessions = response.json()
                print(f"✅ 获取到 {len(sessions)} 个会话:")
                for session in sessions:
                    print(f"   - {session.get('session_name')} ({session.get('session_id')})")
                return True
            else:
                print(f"❌ 获取会话列表失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 获取会话列表请求失败: {e}")
            return False
    
    def on_websocket_message(self, ws, message):
        """WebSocket消息处理"""
        try:
            data = json.loads(message)
            print(f"📨 收到WebSocket消息: {data}")
        except Exception as e:
            print(f"❌ 解析WebSocket消息失败: {e}")
    
    def on_websocket_error(self, ws, error):
        """WebSocket错误处理"""
        print(f"❌ WebSocket错误: {error}")
    
    def on_websocket_close(self, ws, close_status_code, close_msg):
        """WebSocket关闭处理"""
        print(f"🔌 WebSocket连接已关闭: {close_status_code} - {close_msg}")
    
    def on_websocket_open(self, ws):
        """WebSocket连接打开"""
        print("✅ WebSocket连接已建立")
    
    def connect_websocket(self) -> bool:
        """连接WebSocket"""
        if not self.token or not self.session_id:
            print("❌ 缺少token或session_id，无法连接WebSocket")
            return False
            
        print("🔌 连接WebSocket...")
        
        ws_url = f"ws://localhost:8888/api/chat/ws/{self.session_id}?token={self.token}"
        
        try:
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self.on_websocket_message,
                on_error=self.on_websocket_error,
                on_close=self.on_websocket_close,
                on_open=self.on_websocket_open
            )
            
            # 在后台线程中运行WebSocket
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # 等待连接建立
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"❌ WebSocket连接失败: {e}")
            return False
    
    def send_message(self, message: str) -> bool:
        """通过WebSocket发送消息"""
        if not self.ws:
            print("❌ WebSocket未连接")
            return False
            
        print(f"📤 发送消息: {message}")
        
        message_data = {
            "message": message,
            "message_type": "text",
            "session_id": self.session_id
        }
        
        try:
            self.ws.send(json.dumps(message_data))
            return True
        except Exception as e:
            print(f"❌ 发送消息失败: {e}")
            return False
    
    def test_complete_flow(self):
        """测试完整的聊天流程"""
        print("🚀 开始测试完整的聊天流程...\n")
        
        # 1. 登录
        if not self.login():
            return False
        
        print()
        
        # 2. 创建会话
        if not self.create_session():
            return False
        
        print()
        
        # 3. 获取会话列表
        if not self.get_sessions():
            return False
        
        print()
        
        # 4. 连接WebSocket
        if not self.connect_websocket():
            return False
        
        print()
        
        # 5. 发送测试消息
        test_messages = [
            "你好，我是测试用户",
            "请帮我分析一下当前的业务流程",
            "谢谢你的帮助"
        ]
        
        for msg in test_messages:
            if self.send_message(msg):
                print("✅ 消息发送成功")
                time.sleep(2)  # 等待响应
            else:
                print("❌ 消息发送失败")
            print()
        
        print("🎉 测试完成！")
        
        # 保持连接一段时间以接收响应
        print("⏳ 等待响应中...")
        time.sleep(10)
        
        return True

def main():
    """主函数"""
    print("=" * 50)
    print("🧪 Chat API 测试工具")
    print("=" * 50)
    
    tester = ChatAPITester()
    
    try:
        tester.test_complete_flow()
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
    finally:
        if tester.ws:
            tester.ws.close()
        print("\n🔚 测试结束")

if __name__ == "__main__":
    main()