from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from backend.core.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    # 增加连接池配置
    poolclass=QueuePool,  # 使用连接池管理数据库连接
    pool_size=20,  # 增加连接池大小
    max_overflow=20,  # 增加最大溢出连接数
    pool_timeout=60,  # 增加连接超时时间
    pool_recycle=3600  # 每小时回收连接
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()