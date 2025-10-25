"""
pytest配置文件
提供测试环境设置和公共fixtures
"""

import os
import sys
from pathlib import Path

# 必须在导入任何backend模块之前设置环境变量
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("QWEN_API_KEY", "test-qwen-api-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bmp_agent.db")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import pytest_asyncio
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
import httpx

from backend.main import app
from backend.core.database import Base, get_db
from backend.core.config import settings
# 导入所有模型类以确保表能被创建
from backend.models.user import User, UserSession, TaskHistory

# 测试数据库URL - 使用文件数据库避免内存数据库的连接问题
TEST_DATABASE_URL = "sqlite:///./test_bmp_agent_temp.db"

# 创建测试数据库引擎
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=None  # 文件数据库不需要连接池
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """覆盖数据库依赖，使用测试数据库"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    # 确保测试数据库文件不存在
    test_db_file = "test_bmp_agent_temp.db"
    if os.path.exists(test_db_file):
        try:
            os.remove(test_db_file)
        except OSError:
            pass
    
    # 创建所有表
    Base.metadata.create_all(bind=test_engine)
    
    # 覆盖数据库依赖
    app.dependency_overrides[get_db] = override_get_db
    
    yield
    
    # 清理
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()
    
    # 关闭所有连接
    test_engine.dispose()
    
    # 删除测试数据库文件
    if os.path.exists(test_db_file):
        try:
            os.remove(test_db_file)
        except OSError:
            pass


@pytest.fixture
def client(db_session) -> TestClient:
    """创建测试客户端"""
    # 确保在创建客户端时数据库依赖已经被覆盖
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """创建异步测试客户端"""
    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def test_login_data():
    """测试登录数据"""
    return {
        "username": "testuser",
        "password": "testpassword123"
    }


@pytest.fixture
def auth_headers(client: TestClient, test_user_data: dict):
    """获取认证头部"""
    # 先注册用户
    client.post("/api/auth/register", json=test_user_data)
    
    # 登录获取token
    login_response = client.post("/api/auth/login", json={
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    })
    
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def cleanup_test_files():
    """清理测试文件"""
    test_db_file = "test_bmp_agent_temp.db"
    if os.path.exists(test_db_file):
        try:
            os.remove(test_db_file)
        except OSError:
            pass  # 忽略删除失败的情况


@pytest.fixture(autouse=True)
def cleanup():
    """自动清理fixture"""
    yield
    cleanup_test_files()