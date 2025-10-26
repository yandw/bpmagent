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


def validate_file(file: UploadFile) -> bool:
    """验证文件类型（支持图片和PDF）"""
    # 检查文件类型
    allowed_types = [
        "image/jpeg", "image/png", "image/jpg", 
        "application/pdf"
    ]
    if file.content_type not in allowed_types:
        return False
    
    # 检查文件扩展名
    allowed_extensions = [".jpg", ".jpeg", ".png", ".pdf"]
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


def process_file_if_needed(file_path: str, max_size: int = 2048) -> str:
    """如果是图片文件且过大则调整大小，PDF文件直接返回"""
    try:
        # 检查文件扩展名
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # 如果是PDF文件，直接返回
        if file_extension == '.pdf':
            logger.info(f"PDF文件无需处理: {file_path}")
            return file_path
        
        # 对于图片文件，暂时跳过大小调整，直接返回原文件路径
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
        logger.error(f"处理文件失败: {e}")
        return file_path


@router.post("/file", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    auto_ocr: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传文件（支持图片和PDF）并可选择进行OCR识别"""
    
    # 验证文件
    if not validate_file(file):
        raise HTTPException(
            status_code=400,
            detail="不支持的文件类型。请上传 JPG、PNG、JPEG 或 PDF 格式的文件。"
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
        file_path = process_file_if_needed(file_path)
        
        # 创建任务历史记录
        task_history = TaskHistory(
            user_id=current_user.id,
            session_id=session_id,
            task_type="upload",
            task_status="processing",
            status="processing",
            user_input=f"上传文件: {file.filename}",
            input_data={"original_filename": file.filename, "file_uuid": file_id, "file_path": file_path}
        )
        db.add(task_history)
        db.commit()
        db.refresh(task_history)
        
        ocr_result = None
        
        # 自动OCR处理
        if auto_ocr and file_path:
            try:
                logger.info(f"开始OCR识别: {file_path}")
                ocr_service = create_ocr_service()
                
                if hasattr(ocr_service, 'extract_text_from_image'):
                    ocr_result = await ocr_service.extract_text_from_image(file_path)
                else:
                    # 兼容旧接口
                    with open(file_path, 'rb') as f:
                        image_data = f.read()
                    ocr_result = await ocr_service.recognize_invoice(image_data)
                
                # 检查OCR结果
                if ocr_result and ocr_result.success:
                    # 更新任务状态为OCR完成
                    task_history.status = "ocr_completed"
                    task_history.ocr_result = ocr_result.dict()
                    
                    # 提取商品项目数量用于日志
                    items_count = len(ocr_result.items) if ocr_result.items else 0
                    confidence_text = f"，置信度: {ocr_result.confidence:.1%}" if ocr_result.confidence > 0 else ""
                    
                    logger.info(f"OCR识别成功: {file_path}，提取到 {len([k for k, v in ocr_result.dict().items() if v and k != 'raw_result'])} 项信息，包含 {items_count} 个商品明细{confidence_text}")
                else:
                    # OCR失败，记录错误信息
                    task_history.status = "ocr_failed"
                    error_msg = ocr_result.error if ocr_result else "OCR识别失败"
                    task_history.ocr_result = {"error": error_msg}
                    logger.error(f"OCR识别失败: {file_path} - {error_msg}")
                    
            except Exception as e:
                # OCR异常，记录错误
                task_history.status = "ocr_failed"
                task_history.ocr_result = {"error": f"OCR处理异常: {str(e)}"}
                logger.error(f"OCR处理异常: {file_path} - {e}")
            
            # 保存任务状态
            try:
                db.commit()
            except Exception as e:
                logger.error(f"保存OCR结果失败: {e}")
                db.rollback()
        else:
            task_history.task_status = "completed"
            task_history.status = "completed"
        
        db.commit()
        
        # 获取实际文件大小
        actual_file_size = os.path.getsize(file_path)
        
        response = UploadResponse(
            file_id=str(task_history.id),  # 使用任务ID作为file_id
            filename=file.filename,
            file_path=file_path,
            file_size=actual_file_size,
            content_type=file.content_type,
            ocr_result=ocr_result if ocr_result else None
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
    
    # 查找对应的任务记录
    task = db.query(TaskHistory).filter(TaskHistory.id == file_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 从任务记录中获取文件路径
    file_path = None
    if task.input_data and isinstance(task.input_data, dict):
        file_path = task.input_data.get("file_path")
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        # 进行OCR识别
        logger.info(f"开始手动OCR识别: {file_path}")
        ocr_service = create_ocr_service()
        
        if hasattr(ocr_service, 'extract_text_from_image'):
            ocr_result = await ocr_service.extract_text_from_image(file_path)
        else:
            # 兼容旧接口
            with open(file_path, 'rb') as f:
                image_data = f.read()
            ocr_result = await ocr_service.recognize_invoice(image_data)
        
        # 检查OCR结果
        if ocr_result and ocr_result.success:
            # 更新任务记录为成功
            task.ocr_result = ocr_result.dict()
            task.status = "ocr_completed"
            
            # 提取商品项目数量用于日志
            items_count = len(ocr_result.items) if ocr_result.items else 0
            confidence_text = f"，置信度: {ocr_result.confidence:.1%}" if ocr_result.confidence > 0 else ""
            
            logger.info(f"手动OCR识别成功: {file_path}，提取到 {len([k for k, v in ocr_result.dict().items() if v and k != 'raw_result'])} 项信息，包含 {items_count} 个商品明细{confidence_text}")
            
            try:
                db.commit()
            except Exception as e:
                logger.error(f"保存OCR结果失败: {e}")
                db.rollback()
                raise HTTPException(status_code=500, detail="保存OCR结果失败")
            
            return {
                "file_id": file_id,
                "ocr_result": ocr_result.dict(),
                "status": "completed",
                "message": f"OCR识别成功，提取到 {items_count} 个商品明细{confidence_text}"
            }
        else:
            # OCR失败
            error_msg = ocr_result.error if ocr_result else "OCR识别失败"
            task.ocr_result = {"error": error_msg}
            task.status = "ocr_failed"
            
            logger.error(f"手动OCR识别失败: {file_path} - {error_msg}")
            
            try:
                db.commit()
            except Exception as e:
                logger.error(f"保存OCR错误结果失败: {e}")
                db.rollback()
            
            return {
                "file_id": file_id,
                "error": error_msg,
                "status": "failed"
            }
        
    except Exception as e:
        logger.error(f"手动OCR处理异常: {file_path} - {e}")
        
        # 更新任务状态为失败
        task.status = "ocr_failed"
        task.ocr_result = {"error": f"OCR处理异常: {str(e)}"}
        
        try:
            db.commit()
        except Exception as db_e:
            logger.error(f"保存OCR异常结果失败: {db_e}")
            db.rollback()
        
        return {
            "file_id": file_id,
            "error": f"OCR处理异常: {str(e)}",
            "status": "failed"
        }


@router.get("/files/{file_id}")
async def get_file_info(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文件信息"""
    
    # 查找对应的任务记录
    task = db.query(TaskHistory).filter(TaskHistory.id == file_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 从任务记录中获取文件信息
    file_path = None
    original_filename = "unknown"
    if task.input_data and isinstance(task.input_data, dict):
        file_path = task.input_data.get("file_path")
        original_filename = task.input_data.get("original_filename", f"file_{task.id}")
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 获取文件大小
    file_size = os.path.getsize(file_path)
    
    return {
        "file_id": str(task.id),  # 确保返回字符串类型的ID
        "filename": original_filename,
        "content_type": "image/png",  # 添加content_type字段
        "file_size": file_size,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "task_type": task.task_type,
        "status": task.status,
        "ocr_results": task.ocr_results
    }


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除文件"""
    
    # 查找对应的任务记录
    task = db.query(TaskHistory).filter(TaskHistory.id == file_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 从任务记录中获取文件路径
    file_path = None
    if task.input_data and isinstance(task.input_data, dict):
        file_path = task.input_data.get("file_path")
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        # 删除物理文件
        os.remove(file_path)
        
        # 删除数据库记录
        db.delete(task)
        db.commit()
        
        return {"message": "文件删除成功", "file_id": file_id}
        
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail="删除文件失败")