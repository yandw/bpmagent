from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # 应用基础配置
    app_name: str = "BPM Agent"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str
    
    # 数据库配置
    database_url: str = "sqlite:///./bmp_agent.db"
    
    # Redis配置
    redis_url: str = "redis://localhost:6379/0"
    
    # 阿里百炼API配置
    qwen_api_key: str
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-turbo"
    
    # OCR服务配置
    ocr_provider: str = "baidu"  # baidu, tencent, aliyun, paddle
    
    # 百度OCR
    baidu_ocr_api_key: Optional[str] = None
    baidu_ocr_secret_key: Optional[str] = None
    
    # 腾讯OCR
    tencent_secret_id: Optional[str] = None
    tencent_secret_key: Optional[str] = None
    
    # 阿里云OCR
    aliyun_access_key_id: Optional[str] = None
    aliyun_access_key_secret: Optional[str] = None
    
    # PaddleOCR服务
    paddle_ocr_url: Optional[str] = None
    
    # JWT配置
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    
    # 文件上传配置
    max_file_size: int = 10485760  # 10MB
    max_upload_size: int = 10485760  # 10MB (别名，保持兼容性)
    upload_dir: str = "./uploads"
    
    # 浏览器配置
    browser_headless: bool = True
    browser_timeout: int = 30000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 创建全局配置实例
settings = Settings()

# 确保上传目录存在
os.makedirs(settings.upload_dir, exist_ok=True)