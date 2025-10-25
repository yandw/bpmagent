"""
认证相关接口测试
测试用户注册、登录、获取用户信息、刷新令牌等功能
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestAuthAPI:
    """认证API测试类"""
    
    def test_register_success(self, client: TestClient, test_user_data: dict):
        """测试用户注册成功"""
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert data["full_name"] == test_user_data["full_name"]
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        # 确保密码不在响应中
        assert "password" not in data
        assert "hashed_password" not in data
    
    def test_register_duplicate_username(self, client: TestClient, test_user_data: dict):
        """测试注册重复用户名"""
        # 先注册一个用户
        client.post("/api/auth/register", json=test_user_data)
        
        # 尝试注册相同用户名
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        assert "用户名已存在" in response.json()["detail"]
    
    def test_register_duplicate_email(self, client: TestClient, test_user_data: dict):
        """测试注册重复邮箱"""
        # 先注册一个用户
        client.post("/api/auth/register", json=test_user_data)
        
        # 尝试注册相同邮箱但不同用户名
        duplicate_email_data = test_user_data.copy()
        duplicate_email_data["username"] = "different_user"
        
        response = client.post("/api/auth/register", json=duplicate_email_data)
        
        assert response.status_code == 400
        assert "邮箱已存在" in response.json()["detail"]
    
    def test_register_invalid_data(self, client: TestClient):
        """测试注册无效数据"""
        invalid_data = {
            "username": "",  # 空用户名
            "email": "invalid-email",  # 无效邮箱
            "password": "123"  # 密码太短
        }
        
        response = client.post("/api/auth/register", json=invalid_data)
        
        # 应该返回422验证错误
        assert response.status_code == 422
    
    def test_login_success(self, client: TestClient, test_user_data: dict, test_login_data: dict):
        """测试登录成功"""
        # 先注册用户
        client.post("/api/auth/register", json=test_user_data)
        
        # 登录
        response = client.post("/api/auth/login", json=test_login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data
        
        # 检查用户信息
        user_data = data["user"]
        assert user_data["username"] == test_user_data["username"]
        assert user_data["email"] == test_user_data["email"]
        assert user_data["is_active"] is True
    
    def test_login_wrong_username(self, client: TestClient, test_user_data: dict):
        """测试错误用户名登录"""
        # 先注册用户
        client.post("/api/auth/register", json=test_user_data)
        
        # 使用错误用户名登录
        wrong_login_data = {
            "username": "wronguser",
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/auth/login", json=wrong_login_data)
        
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]
    
    def test_login_wrong_password(self, client: TestClient, test_user_data: dict):
        """测试错误密码登录"""
        # 先注册用户
        client.post("/api/auth/register", json=test_user_data)
        
        # 使用错误密码登录
        wrong_login_data = {
            "username": test_user_data["username"],
            "password": "wrongpassword"
        }
        
        response = client.post("/api/auth/login", json=wrong_login_data)
        
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]
    
    def test_get_current_user_info(self, client: TestClient, auth_headers: dict):
        """测试获取当前用户信息"""
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "username" in data
        assert "email" in data
        assert "is_active" in data
        assert "created_at" in data
        # 确保密码不在响应中
        assert "password" not in data
        assert "hashed_password" not in data
    
    def test_get_current_user_info_without_auth(self, client: TestClient):
        """测试未认证获取用户信息"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 403
    
    def test_get_current_user_info_invalid_token(self, client: TestClient):
        """测试无效token获取用户信息"""
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/auth/me", headers=invalid_headers)
        
        # FastAPI的HTTPBearer默认返回401而不是403
        assert response.status_code == 401
    
    def test_refresh_token(self, client: TestClient, auth_headers: dict):
        """测试刷新令牌"""
        response = client.post("/api/auth/refresh", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_refresh_token_without_auth(self, client: TestClient):
        """测试未认证刷新令牌"""
        response = client.post("/api/auth/refresh")
        
        assert response.status_code == 403
    
    def test_refresh_token_invalid_token(self, client: TestClient):
        """测试无效token刷新令牌"""
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/api/auth/refresh", headers=invalid_headers)
        
        # FastAPI的HTTPBearer默认返回401而不是403
        assert response.status_code == 401


@pytest.mark.asyncio
class TestAuthAPIAsync:
    """认证API异步测试类"""
    
    async def test_register_async(self, async_client: AsyncClient, test_user_data: dict):
        """测试异步用户注册"""
        response = await async_client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
    
    async def test_login_async(self, async_client: AsyncClient, test_user_data: dict, test_login_data: dict):
        """测试异步用户登录"""
        # 先注册用户
        await async_client.post("/api/auth/register", json=test_user_data)
        
        # 登录
        response = await async_client.post("/api/auth/login", json=test_login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"