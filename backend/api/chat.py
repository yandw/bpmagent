from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
import json
import logging
from datetime import datetime

from backend.core.database import get_db
from backend.models.user import User, UserSession, TaskHistory
from backend.api.auth import get_current_user
from backend.services.bpm_agent import BPMAgentService
from backend.services.validation import SmartValidationService

router = APIRouter(prefix="/chat", tags=["对话"])
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """聊天消息模型"""
    message: str
    message_type: str = "text"  # text, image, file
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    message: str
    message_type: str = "text"
    intent: Optional[str] = None
    actions: List[Dict[str, Any]] = []
    session_id: str
    timestamp: datetime


class SessionCreate(BaseModel):
    """会话创建模型"""
    session_name: Optional[str] = Field(None, min_length=1, max_length=100, description="会话名称")
    target_url: Optional[HttpUrl] = Field(None, description="目标URL")


class SessionResponse(BaseModel):
    """会话响应模型"""
    session_id: str
    session_name: str
    target_url: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# 活跃的WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                self.disconnect(session_id)


manager = ConnectionManager()


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的对话会话"""
    try:
        import uuid
        
        # 生成唯一的会话ID
        session_id = str(uuid.uuid4())
        # 生成会话名称
        session_name = f"会话_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if hasattr(session_data, 'session_name') and session_data.session_name:
            session_name = session_data.session_name
        
        # 创建会话记录
        db_session = UserSession(
            user_id=current_user.id,
            session_id=session_id,
            session_name=session_name,
            is_active=True
        )
        
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        # 返回符合SessionResponse格式的数据
        return SessionResponse(
            session_id=db_session.session_id,
            session_name=db_session.session_name,
            target_url=str(session_data.target_url) if session_data.target_url else None,
            status="active",
            created_at=db_session.created_at
        )
        
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail="创建会话失败")


@router.get("/sessions", response_model=List[SessionResponse])
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的所有会话"""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id
    ).order_by(UserSession.created_at.desc()).all()
    
    # 转换为SessionResponse格式
    response_sessions = []
    for session in sessions:
        response_sessions.append(SessionResponse(
            session_id=session.session_id,
            session_name=f"会话_{session.created_at.strftime('%Y%m%d_%H%M%S')}",
            target_url=None,  # UserSession模型中没有target_url字段
            status="active" if session.is_active else "inactive",
            created_at=session.created_at
        ))
    
    return response_sessions


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定会话信息"""
    session = db.query(UserSession).filter(
        UserSession.session_id == session_id,
        UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 转换为SessionResponse格式
    return SessionResponse(
        session_id=session.session_id,
        session_name=session.session_name or f"会话_{session.created_at.strftime('%Y%m%d_%H%M%S')}",
        target_url=None,  # UserSession模型中没有target_url字段
        status="active" if session.is_active else "inactive",
        created_at=session.created_at
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除会话"""
    session = db.query(UserSession).filter(
        UserSession.session_id == session_id,
        UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 更新会话状态为已删除
    session.is_active = False
    db.commit()
    
    # 断开WebSocket连接
    manager.disconnect(session_id)
    
    return {"message": "会话已删除"}


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """WebSocket对话端点"""
    
    # 从查询参数获取token
    if not token:
        query_params = dict(websocket.query_params)
        token = query_params.get('token')
    
    logger.info(f"WebSocket连接请求: session_id={session_id}, has_token={bool(token)}")
    
    # 验证JWT token
    if not token:
        logger.warning(f"WebSocket连接被拒绝: 缺少认证token, session_id={session_id}")
        await websocket.close(code=4001, reason="缺少认证token")
        return
    
    try:
        from backend.api.auth import verify_token_string
        user = verify_token_string(token, db)
        if not user:
            logger.warning(f"WebSocket连接被拒绝: 无效的认证token, session_id={session_id}")
            await websocket.close(code=4001, reason="无效的认证token")
            return
        logger.info(f"WebSocket认证成功: user_id={user.id}, session_id={session_id}")
    except Exception as e:
        logger.error(f"Token验证失败: {e}, session_id={session_id}")
        await websocket.close(code=4001, reason="认证失败")
        return
    
    await manager.connect(websocket, session_id)
    
    # 验证会话是否存在且属于当前用户
    session = db.query(UserSession).filter(
        UserSession.session_id == session_id,
        UserSession.user_id == user.id
    ).first()
    
    if not session:
        logger.warning(f"WebSocket连接被拒绝: 会话不存在或不属于用户, session_id={session_id}, user_id={user.id}")
        await websocket.close(code=4004, reason="会话不存在")
        return
    
    logger.info(f"WebSocket连接建立成功: session_id={session_id}, user_id={user.id}")
    
    # 创建BPM代理服务
    bpm_agent = BPMAgentService(user, session, db)
    validation_service = SmartValidationService()
    
    try:
        # 发送欢迎消息
        welcome_message = {
            "type": "message",
            "content": "您好！我是您的BPM助手，可以帮助您自动填写表单和处理业务流程。请告诉我您需要什么帮助？",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_message(session_id, welcome_message)
        
        while True:
            # 接收用户消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_message = message_data.get("message", "")
            message_type = message_data.get("type", "text")
            
            if not user_message:
                continue
            
            try:
                # 发送处理中状态
                processing_message = {
                    "type": "status",
                    "content": "正在处理您的请求...",
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_message(session_id, processing_message)
                
                # 使用BPM代理处理消息 - 流式版本
                async for stream_response in bpm_agent.process_user_message_stream(user_message, message_type):
                    # 如果响应包含表单数据，进行智能验证
                    if "form_data" in message_data and stream_response.get("type") == "message_complete":
                        form_data = message_data["form_data"]
                        validation_results = validation_service.validate_form_data(form_data)
                        validation_summary = validation_service.get_validation_summary(validation_results)
                        
                        stream_response["data"]["validation"] = {
                            "results": [result.dict() for result in validation_results],
                            "summary": validation_summary
                        }
                    
                    # 转换响应格式以适配WebSocket消息格式
                    if stream_response.get("type") == "message_chunk":
                        # 流式消息块
                        websocket_response = {
                            "type": "message_chunk",
                            "content": stream_response["data"]["content"],
                            "message_type": stream_response["data"]["message_type"],
                            "timestamp": datetime.now().isoformat()
                        }
                    elif stream_response.get("type") == "message_complete":
                        # 消息完成
                        websocket_response = {
                            "type": "message_complete",
                            "content": stream_response["data"]["full_message"],
                            "intent": stream_response["data"]["intent"],
                            "actions": stream_response["data"]["actions"],
                            "timestamp": datetime.now().isoformat()
                        }
                        # 如果有验证信息，添加到响应中
                        if "validation" in stream_response["data"]:
                            websocket_response["validation"] = stream_response["data"]["validation"]
                    elif stream_response.get("type") == "error":
                        # 错误消息
                        websocket_response = {
                            "type": "error",
                            "content": stream_response["data"]["message"],
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        # 其他类型消息（如意图识别结果）
                        websocket_response = {
                            "type": stream_response.get("type", "status"),
                            "content": stream_response.get("data", {}),
                            "timestamp": datetime.now().isoformat()
                        }
                    
                    # 发送响应消息
                    await manager.send_message(session_id, websocket_response)
                
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
                
                # 发送错误消息
                error_message = {
                    "type": "error",
                    "content": "抱歉，处理您的请求时出现了错误，请稍后重试。",
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_message(session_id, error_message)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        # 清理资源
        await bpm_agent.cleanup()
        manager.disconnect(session_id)


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取会话历史记录"""
    # 验证会话权限
    session = db.query(UserSession).filter(
        UserSession.session_id == session_id,
        UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 获取历史记录
    history = db.query(TaskHistory).filter(
        TaskHistory.session_id == session_id
    ).order_by(TaskHistory.created_at.asc()).all()
    
    return history