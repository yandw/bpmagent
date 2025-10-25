#!/usr/bin/env python3
"""
调试测试问题的脚本
"""

import os
import sys
from pathlib import Path

# 设置环境变量
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("QWEN_API_KEY", "test-qwen-api-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bmp_agent.db")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# 导入模型和应用
from backend.models.user import User, UserSession, TaskHistory
from backend.core.database import Base, get_db
from backend.main import app

def test_table_creation():
    """测试表创建"""
    print("1. 测试表创建...")
    
    # 创建内存数据库
    TEST_DATABASE_URL = "sqlite:///:memory:"
    test_engine = create_engine(
        TEST_DATABASE_URL, 
        connect_args={"check_same_thread": False},
        poolclass=None
    )
    
    # 创建表
    Base.metadata.create_all(bind=test_engine)
    print(f"   创建的表: {list(Base.metadata.tables.keys())}")
    
    # 创建会话
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    print("2. 测试API调用...")
    
    # 覆盖数据库依赖 - 在创建客户端之前
    app.dependency_overrides[get_db] = override_get_db
    
    # 创建测试客户端
    client = TestClient(app)
    
    # 测试数据
    test_user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    # 调用注册API
    try:
        response = client.post("/api/auth/register", json=test_user_data)
        print(f"   响应状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   响应数据: {response.json()}")
            print("✅ 测试成功!")
        else:
            print(f"   错误响应: {response.text}")
            print("❌ 测试失败!")
    except Exception as e:
        print(f"   异常: {e}")
        print("❌ 测试失败!")
        
        # 尝试直接查询数据库
        print("3. 直接测试数据库连接...")
        db = TestingSessionLocal()
        try:
            # 检查表是否存在
            from sqlalchemy import text
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result.fetchall()]
            print(f"   数据库中的表: {tables}")
            
            # 尝试查询用户表
            users = db.query(User).all()
            print(f"   用户表中的记录数: {len(users)}")
        except Exception as db_e:
            print(f"   数据库查询异常: {db_e}")
        finally:
            db.close()
    
    # 清理
    app.dependency_overrides.clear()

if __name__ == "__main__":
    test_table_creation()