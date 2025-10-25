"""
聊天相关接口测试
测试会话创建、获取、历史记录等功能
注意：WebSocket测试需要特殊处理，这里主要测试HTTP接口
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json
import uuid


class TestChatAPI:
    """聊天API测试类"""
    
    def test_create_session(self, client: TestClient, auth_headers: dict):
        """测试创建会话"""
        session_data = {
            "target_url": "https://example.com",
            "session_name": "测试会话"
        }
        
        response = client.post("/api/chat/sessions", json=session_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_name"] == session_data["session_name"]
        assert data["target_url"] == "https://example.com/"  # HttpUrl会自动添加尾部斜杠
        assert data["status"] == "active"
        assert "created_at" in data
    
    def test_create_session_without_auth(self, client: TestClient):
        """测试未认证创建会话"""
        session_data = {
            "target_url": "https://example.com",
            "session_name": "测试会话"
        }
        
        response = client.post("/api/chat/sessions", json=session_data)
        
        assert response.status_code == 403
    
    def test_create_session_invalid_data(self, client: TestClient, auth_headers: dict):
        """测试创建会话无效数据"""
        invalid_data = {
            "target_url": "invalid-url",  # 无效URL
            "session_name": ""  # 空名称
        }
        
        response = client.post("/api/chat/sessions", json=invalid_data, headers=auth_headers)
        
        # 应该返回422验证错误
        assert response.status_code == 422
    
    def test_get_user_sessions(self, client: TestClient, auth_headers: dict):
        """测试获取用户会话列表"""
        # 先创建几个会话
        session_data_1 = {
            "target_url": "https://example1.com",
            "session_name": "测试会话1"
        }
        session_data_2 = {
            "target_url": "https://example2.com", 
            "session_name": "测试会话2"
        }
        
        client.post("/api/chat/sessions", json=session_data_1, headers=auth_headers)
        client.post("/api/chat/sessions", json=session_data_2, headers=auth_headers)
        
        # 获取会话列表
        response = client.get("/api/chat/sessions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        
        # 检查会话数据结构
        for session in data:
            assert "session_id" in session
            assert "session_name" in session
            assert "status" in session
            assert "created_at" in session
    
    def test_get_user_sessions_without_auth(self, client: TestClient):
        """测试未认证获取会话列表"""
        response = client.get("/api/chat/sessions")
        
        assert response.status_code == 403
    
    def test_get_session_by_id(self, client: TestClient, auth_headers: dict):
        """测试根据ID获取会话"""
        # 先创建一个会话
        session_data = {
            "target_url": "https://example.com",
            "session_name": "测试会话"
        }
        
        create_response = client.post("/api/chat/sessions", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # 获取会话详情
        response = client.get(f"/api/chat/sessions/{session_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["session_name"] == session_data["session_name"]
        assert data["status"] == "active"
    
    def test_get_session_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的会话"""
        fake_session_id = str(uuid.uuid4())
        
        response = client.get(f"/api/chat/sessions/{fake_session_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "会话不存在" in response.json()["detail"]
    
    def test_get_session_without_auth(self, client: TestClient):
        """测试未认证获取会话详情"""
        fake_session_id = str(uuid.uuid4())
        
        response = client.get(f"/api/chat/sessions/{fake_session_id}")
        
        assert response.status_code == 403
    
    def test_get_session_history(self, client: TestClient, auth_headers: dict):
        """测试获取会话历史记录"""
        # 先创建一个会话
        session_data = {
            "target_url": "https://example.com",
            "session_name": "测试会话"
        }
        
        create_response = client.post("/api/chat/sessions", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # 获取会话历史记录
        response = client.get(f"/api/chat/sessions/{session_id}/history", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 新创建的会话应该没有历史记录
        assert len(data) == 0
    
    def test_get_session_history_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在会话的历史记录"""
        fake_session_id = str(uuid.uuid4())
        
        response = client.get(f"/api/chat/sessions/{fake_session_id}/history", headers=auth_headers)
        
        assert response.status_code == 404
        assert "会话不存在" in response.json()["detail"]
    
    def test_get_session_history_without_auth(self, client: TestClient):
        """测试未认证获取会话历史记录"""
        fake_session_id = str(uuid.uuid4())
        
        response = client.get(f"/api/chat/sessions/{fake_session_id}/history")
        
        assert response.status_code == 403


@pytest.mark.asyncio
class TestChatAPIAsync:
    """聊天API异步测试类"""
    
    async def test_create_session_async(self, async_client: AsyncClient, test_user_data: dict):
        """测试异步创建会话"""
        # 先注册和登录用户
        await async_client.post("/api/auth/register", json=test_user_data)
        login_response = await async_client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 创建会话
        session_data = {
            "target_url": "https://example.com",
            "session_name": "异步测试会话"
        }
        
        response = await async_client.post("/api/chat/sessions", json=session_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_name"] == session_data["session_name"]
    
    async def test_get_sessions_async(self, async_client: AsyncClient, test_user_data: dict):
        """测试异步获取会话列表"""
        # 先注册和登录用户
        await async_client.post("/api/auth/register", json=test_user_data)
        login_response = await async_client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 创建会话
        session_data = {
            "target_url": "https://example.com",
            "session_name": "异步测试会话"
        }
        await async_client.post("/api/chat/sessions", json=session_data, headers=headers)
        
        # 获取会话列表
        response = await async_client.get("/api/chat/sessions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestWebSocketConnection:
    """WebSocket连接测试类"""
    
    def test_websocket_connection_without_token(self, client: TestClient):
        """测试无token的WebSocket连接"""
        session_id = str(uuid.uuid4())
        
        with pytest.raises(Exception):
            # WebSocket连接应该失败
            with client.websocket_connect(f"/api/chat/ws/{session_id}"):
                pass
    
    def test_websocket_connection_invalid_token(self, client: TestClient):
        """测试无效token的WebSocket连接"""
        session_id = str(uuid.uuid4())
        
        with pytest.raises(Exception):
            # WebSocket连接应该失败
            with client.websocket_connect(f"/api/chat/ws/{session_id}?token=invalid_token"):
                pass
    
    def test_websocket_connection_nonexistent_session(self, client: TestClient, auth_headers: dict):
        """测试连接不存在的会话"""
        # 从auth_headers中提取token
        token = auth_headers["Authorization"].replace("Bearer ", "")
        fake_session_id = str(uuid.uuid4())
        
        # WebSocket连接应该被服务器关闭，因为会话不存在
        # 我们需要检查连接是否会被正确关闭
        connection_closed = False
        try:
            with client.websocket_connect(f"/api/chat/ws/{fake_session_id}?token={token}") as websocket:
                # 尝试接收消息，如果会话不存在，连接应该被关闭
                try:
                    # 等待一小段时间看是否有消息或连接关闭
                    data = websocket.receive_text()
                    # 如果能接收到消息，说明连接没有被正确关闭
                    pytest.fail(f"WebSocket连接应该因为会话不存在而被关闭，但收到了消息: {data}")
                except Exception:
                    # 连接被关闭或出现异常是预期的行为
                    connection_closed = True
        except Exception:
            # 连接建立失败也是预期的行为
            connection_closed = True
        
        # 验证连接确实被关闭了
        assert connection_closed, "WebSocket连接应该因为会话不存在而被关闭"