from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from backend.core.database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # BMP系统配置
    bmp_config = Column(JSON, default={})  # 存储BMP系统登录信息和配置
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserSession(Base):
    """用户会话模型"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    session_name = Column(String(100))  # 存储会话名称
    browser_session_data = Column(Text)  # 存储浏览器会话数据
    is_active = Column(Boolean, default=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))


class TaskHistory(Base):
    """任务历史记录模型"""
    __tablename__ = "task_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    session_id = Column(String(255), index=True)  # 关联会话ID
    task_type = Column(String(50), nullable=False)  # 'expense_report', 'leave_request', etc.
    task_status = Column(String(20), nullable=False)  # 'pending', 'processing', 'completed', 'failed'
    status = Column(String(20), nullable=False, default="pending")  # 状态别名，保持兼容性
    
    # 任务数据
    user_input = Column(Text)  # 用户输入的原始数据（文本格式）
    input_data = Column(JSON)  # 用户输入的原始数据
    ocr_results = Column(JSON)  # OCR识别结果
    ocr_result = Column(JSON)  # OCR结果别名，保持兼容性
    ai_analysis = Column(JSON)  # AI分析结果
    bmp_response = Column(JSON)  # BMP系统响应
    
    # 结果信息
    flow_id = Column(String(100))  # BMP系统流程ID
    error_message = Column(Text)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))