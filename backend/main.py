from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import logging
import os
from contextlib import asynccontextmanager

from backend.core.config import settings
from backend.core.database import engine, Base
from backend.api import auth, chat, upload

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("应用启动中...")
    
    # 创建数据库表
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
    
    # 确保必要的目录存在
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    yield
    
    # 关闭时执行
    logger.info("应用关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title="BPM Agent",
    description="智能对话式BPM代理工具",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(upload.router, prefix="/api")

# 静态文件服务（用于前端）
if os.path.exists("frontend/dist"):
    app.mount("/static", StaticFiles(directory="frontend/dist/static"), name="static")

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    }

# 根路径
@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径，返回简单的欢迎页面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BPM Agent</title>
        <meta charset="utf-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }
            .feature {
                margin: 20px 0;
                padding: 15px;
                background: #f8f9fa;
                border-left: 4px solid #007bff;
                border-radius: 4px;
            }
            .api-link {
                text-align: center;
                margin-top: 30px;
            }
            .api-link a {
                color: #007bff;
                text-decoration: none;
                font-weight: bold;
            }
            .api-link a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 BPM Agent</h1>
            <p>欢迎使用智能对话式BPM代理工具！</p>
            
            <div class="feature">
                <h3>🎯 核心功能</h3>
                <ul>
                    <li>智能对话交互</li>
                    <li>自动表单填写</li>
                    <li>OCR文档识别</li>
                    <li>浏览器自动化</li>
                    <li>BPM流程集成</li>
                </ul>
            </div>
            
            <div class="feature">
                <h3>🚀 技术栈</h3>
                <ul>
                    <li>后端：Python + FastAPI</li>
                    <li>AI模型：阿里云通义千问 (Qwen3)</li>
                    <li>浏览器自动化：Playwright</li>
                    <li>数据库：PostgreSQL/SQLite</li>
                    <li>实时通信：WebSocket</li>
                </ul>
            </div>
            
            <div class="feature">
                <h3>📚 API文档</h3>
                <p>访问 <a href="/docs">/docs</a> 查看完整的API文档</p>
                <p>访问 <a href="/redoc">/redoc</a> 查看ReDoc格式的API文档</p>
            </div>
            
            <div class="api-link">
                <p>开始使用：<a href="/docs">API 文档</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# API信息端点
@app.get("/api/info")
async def api_info():
    """API信息"""
    return {
        "name": "BPM Agent API",
        "version": "1.0.0",
        "description": "智能对话式BPM代理工具API",
        "endpoints": {
            "auth": "/api/auth",
            "chat": "/api/chat", 
            "upload": "/api/upload",
            "docs": "/docs",
            "health": "/health"
        },
        "features": [
            "用户认证与授权",
            "实时对话交互",
            "文件上传与OCR",
            "浏览器自动化",
            "智能表单填写"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    # 开发环境运行
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8888,
        reload=True,
        log_level="info"
    )