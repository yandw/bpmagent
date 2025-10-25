from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import logging
from datetime import datetime
# from PIL import Image  # 暂时注释掉PIL依赖
import io

from backend.core.database import get_db
from backend.core.config import settings
from backend.models.user import User, TaskHistory
from backend.api.auth import get_current_user
from backend.services.ocr import create_ocr_service

router = APIRouter(prefix="/upload", tags=["文件上传"])
logger = logging.getLogger(__name__)


class UploadResponse(BaseModel):
    """上传响应模型"""
    file_id: str
    filename: str
    file_path: str
    file_size: int
    content_type: str
    ocr_result: Optional[dict] = None


def validate_image_file(file: UploadFile) -> bool:
    """验证图片文件"""
    # 检查文件类型
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/bmp", "image/tiff"]
    if file.content_type not in allowed_types:
        return False
    
    # 检查文件扩展名
    allowed_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        return False
    
    return True


def save_uploaded_file(file: UploadFile, file_id: str) -> str:
    """保存上传的文件"""
    # 确保上传目录存在
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # 生成文件路径
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{file_id}{file_extension}"
    file_path = os.path.join(settings.upload_dir, filename)
    
    # 保存文件
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    return file_path


def resize_image_if_needed(file_path: str, max_size: int = 2048) -> str:
    """如果图片过大则调整大小"""
    try:
        # 暂时跳过图片大小调整，直接返回原文件路径
        # TODO: 当安装PIL后，可以启用图片大小调整功能
        logger.info(f"跳过图片大小调整: {file_path}")
        return file_path
        
        # # 原PIL代码（已注释）
        # with Image.open(file_path) as img:
        #     # 检查图片尺寸
        #     width, height = img.size
        #     
        #     if width > max_size or height > max_size:
        #         # 计算新尺寸，保持宽高比
        #         if width > height:
        #             new_width = max_size
        #             new_height = int(height * (max_size / width))
        #         else:
        #             new_height = max_size
        #             new_width = int(width * (max_size / height))
        #         
        #         # 调整图片大小
        #         resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        #         
        #         # 保存调整后的图片
        #         resized_img.save(file_path, optimize=True, quality=85)
        #         logger.info(f"图片已调整大小: {width}x{height} -> {new_width}x{new_height}")
        # 
        # return file_path
        
    except Exception as e:
        logger.error(f"调整图片大小失败: {e}")
        return file_path


@router.post("/image", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    auto_ocr: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传图片文件并可选择进行OCR识别"""
    
    # 验证文件
    if not validate_image_file(file):
        raise HTTPException(
            status_code=400,
            detail="不支持的文件类型。请上传 JPG、PNG、BMP 或 TIFF 格式的图片。"
        )
    
    # 检查文件大小
    file.file.seek(0, 2)  # 移动到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置到文件开头
    
    if file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大。最大允许大小为 {settings.max_upload_size // (1024*1024)} MB。"
        )
    
    try:
        # 生成文件ID
        file_id = str(uuid.uuid4())
        
        # 保存文件
        file_path = save_uploaded_file(file, file_id)
        
        # 调整图片大小（如果需要）
        file_path = resize_image_if_needed(file_path)
        
        # 创建任务历史记录
        task_history = TaskHistory(
            user_id=current_user.id,
            session_id=session_id,
            task_type="upload",
            user_input=f"上传文件: {file.filename}",
            status="processing"
        )
        db.add(task_history)
        db.commit()
        db.refresh(task_history)
        
        ocr_result = None
        
        # 如果启用自动OCR，进行文字识别
        if auto_ocr:
            try:
                ocr_service = create_ocr_service()
                ocr_result = await ocr_service.recognize_invoice(file_path)
                
                # 更新任务历史
                task_history.ocr_result = ocr_result.dict() if ocr_result else None
                task_history.status = "completed"
                
                logger.info(f"OCR识别完成: {file.filename}")
                
            except Exception as e:
                logger.error(f"OCR识别失败: {e}")
                task_history.status = "ocr_failed"
                task_history.bmp_response = f"OCR识别失败: {str(e)}"
        else:
            task_history.status = "completed"
        
        db.commit()
        
        # 获取实际文件大小
        actual_file_size = os.path.getsize(file_path)
        
        response = UploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_path=file_path,
            file_size=actual_file_size,
            content_type=file.content_type,
            ocr_result=ocr_result.dict() if ocr_result else None
        )
        
        return response
        
    except Exception as e:
        logger.error(f"上传文件失败: {e}")
        
        # 清理可能已创建的文件
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail="文件上传失败")


@router.post("/ocr/{file_id}")
async def process_ocr(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """对已上传的文件进行OCR识别"""
    
    # 查找文件记录
    task_history = db.query(TaskHistory).filter(
        TaskHistory.user_id == current_user.id,
        TaskHistory.task_type == "upload",
        TaskHistory.user_input.contains(file_id)
    ).first()
    
    if not task_history:
        raise HTTPException(status_code=404, detail="文件记录不存在")
    
    # 构建文件路径（这里简化处理，实际应该从数据库记录中获取）
    file_path = None
    for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
        potential_path = os.path.join(settings.upload_dir, f"{file_id}{ext}")
        if os.path.exists(potential_path):
            file_path = potential_path
            break
    
    if not file_path:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        # 进行OCR识别
        ocr_service = create_ocr_service()
        ocr_result = await ocr_service.recognize_invoice(file_path)
        
        # 更新任务历史
        task_history.ocr_result = ocr_result.dict() if ocr_result else None
        task_history.status = "completed"
        db.commit()
        
        return {
            "file_id": file_id,
            "ocr_result": ocr_result.dict() if ocr_result else None,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"OCR处理失败: {e}")
        
        # 更新任务状态
        task_history.status = "ocr_failed"
        task_history.bmp_response = f"OCR处理失败: {str(e)}"
        db.commit()
        
        raise HTTPException(status_code=500, detail="OCR处理失败")


@router.get("/files/{file_id}")
async def get_file_info(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文件信息"""
    
    # 查找文件记录
    task_history = db.query(TaskHistory).filter(
        TaskHistory.user_id == current_user.id,
        TaskHistory.task_type == "upload",
        TaskHistory.user_input.contains(file_id)
    ).first()
    
    if not task_history:
        raise HTTPException(status_code=404, detail="文件记录不存在")
    
    return {
        "file_id": file_id,
        "task_id": task_history.task_id,
        "status": task_history.status,
        "ocr_result": task_history.ocr_result,
        "created_at": task_history.created_at,
        "updated_at": task_history.updated_at
    }


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除上传的文件"""
    
    # 查找文件记录
    task_history = db.query(TaskHistory).filter(
        TaskHistory.user_id == current_user.id,
        TaskHistory.task_type == "upload",
        TaskHistory.user_input.contains(file_id)
    ).first()
    
    if not task_history:
        raise HTTPException(status_code=404, detail="文件记录不存在")
    
    try:
        # 删除物理文件
        for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            file_path = os.path.join(settings.upload_dir, f"{file_id}{ext}")
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已删除文件: {file_path}")
                break
        
        # 删除数据库记录
        db.delete(task_history)
        db.commit()
        
        return {"message": "文件已删除"}
        
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail="删除文件失败")