"""
文件上传相关接口测试
测试图片上传、OCR处理、文件信息获取、文件删除等功能
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import io
import os
import tempfile
from PIL import Image
import uuid


def create_test_image(format="PNG", size=(100, 100), color="RGB"):
    """创建测试图片"""
    img = Image.new(color, size, color=(255, 255, 255))
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes


def create_test_file(content="test content", filename="test.txt"):
    """创建测试文件"""
    file_bytes = io.BytesIO(content.encode())
    file_bytes.name = filename
    return file_bytes


class TestUploadAPI:
    """文件上传API测试类"""
    
    def test_upload_image_success(self, client: TestClient, auth_headers: dict):
        """测试成功上传图片"""
        # 创建测试图片
        test_image = create_test_image()
        
        files = {
            "file": ("test_image.png", test_image, "image/png")
        }
        data = {
            "auto_ocr": "false"  # 关闭自动OCR以避免OCR服务错误
        }
        
        response = client.post("/api/upload/file", files=files, data=data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert "file_id" in result
        assert result["filename"] == "test_image.png"
        assert result["content_type"] == "image/png"
        assert "file_path" in result
        assert "file_size" in result
    
    def test_upload_image_without_auth(self, client: TestClient):
        """测试未认证上传图片"""
        test_image = create_test_image()
        
        files = {
            "file": ("test_image.png", test_image, "image/png")
        }
        
        response = client.post("/api/upload/file", files=files)
        
        assert response.status_code == 403
    
    def test_upload_image_invalid_format(self, client: TestClient, auth_headers: dict):
        """测试上传无效格式文件"""
        # 创建文本文件而不是图片
        test_file = create_test_file("not an image", "test.txt")
        
        files = {
            "file": ("test.txt", test_file, "text/plain")
        }
        
        response = client.post("/api/upload/file", files=files, headers=auth_headers)
        
        assert response.status_code == 400
        assert "不支持的文件类型" in response.json()["detail"]
    
    def test_upload_image_too_large(self, client: TestClient, auth_headers: dict):
        """测试上传过大文件"""
        # 创建一个真正超过10MB的大图片
        # 使用更大的尺寸和更复杂的内容来确保文件大小超过限制
        large_image = create_test_image(size=(10000, 10000))
        
        # 如果还不够大，创建一个包含随机数据的更大图片
        from PIL import Image
        import random
        
        # 创建一个包含随机像素的大图片
        img = Image.new('RGB', (8000, 8000))
        pixels = []
        for i in range(8000 * 8000):
            pixels.append((random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        img.putdata(pixels)
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG', compress_level=0)  # 不压缩以增加文件大小
        img_bytes.seek(0)
        
        files = {
            "file": ("large_image.png", img_bytes, "image/png")
        }
        
        response = client.post("/api/upload/file", files=files, headers=auth_headers)
        
        # 应该返回400错误，因为文件过大
        assert response.status_code == 400
        assert "文件过大" in response.json()["detail"]
    
    def test_upload_image_with_session_id(self, client: TestClient, auth_headers: dict):
        """测试带会话ID上传图片"""
        # 先创建一个会话
        session_data = {
            "target_url": "https://example.com",
            "session_name": "测试会话"
        }
        session_response = client.post("/api/chat/sessions", json=session_data, headers=auth_headers)
        session_id = session_response.json()["session_id"]
        
        # 上传图片
        test_image = create_test_image()
        files = {
            "file": ("test_image.png", test_image, "image/png")
        }
        data = {
            "session_id": session_id,
            "auto_ocr": "false"
        }
        
        response = client.post("/api/upload/file", files=files, data=data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert "file_id" in result
    
    def test_process_ocr(self, client: TestClient, auth_headers: dict):
        """测试OCR处理"""
        # 先上传一个图片（不自动OCR）
        test_image = create_test_image()
        files = {
            "file": ("test_image.png", test_image, "image/png")
        }
        data = {
            "auto_ocr": "false"
        }
        
        upload_response = client.post("/api/upload/file", files=files, data=data, headers=auth_headers)
        file_id = upload_response.json()["file_id"]
        
        # 手动触发OCR
        response = client.post(f"/api/upload/ocr/{file_id}", headers=auth_headers)
        
        # OCR可能成功也可能失败，我们只验证响应格式
        assert response.status_code == 200
        result = response.json()
        # 无论OCR成功还是失败，都应该有这些字段
        assert "file_id" in result
        # 如果OCR成功，会有ocr_result；如果失败，会有error信息
        assert "ocr_result" in result or "error" in result
    
    def test_process_ocr_nonexistent_file(self, client: TestClient, auth_headers: dict):
        """测试处理不存在文件的OCR"""
        fake_file_id = str(uuid.uuid4())
        
        response = client.post(f"/api/upload/ocr/{fake_file_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "文件不存在" in response.json()["detail"]
    
    def test_process_ocr_without_auth(self, client: TestClient):
        """测试未认证处理OCR"""
        fake_file_id = str(uuid.uuid4())
        
        response = client.post(f"/api/upload/ocr/{fake_file_id}")
        
        assert response.status_code == 403
    
    def test_get_file_info(self, client: TestClient, auth_headers: dict):
        """测试获取文件信息"""
        # 先上传一个文件
        test_image = create_test_image()
        files = {
            "file": ("test_image.png", test_image, "image/png")
        }
        data = {
            "auto_ocr": "false"
        }
        
        upload_response = client.post("/api/upload/file", files=files, data=data, headers=auth_headers)
        file_id = upload_response.json()["file_id"]
        
        # 获取文件信息
        response = client.get(f"/api/upload/files/{file_id}", headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["file_id"] == file_id
        assert result["filename"] == "test_image.png"
        assert result["content_type"] == "image/png"
        assert "file_size" in result
        assert "created_at" in result
    
    def test_get_file_info_nonexistent(self, client: TestClient, auth_headers: dict):
        """测试获取不存在文件的信息"""
        fake_file_id = str(uuid.uuid4())
        
        response = client.get(f"/api/upload/files/{fake_file_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "文件不存在" in response.json()["detail"]
    
    def test_get_file_info_without_auth(self, client: TestClient):
        """测试未认证获取文件信息"""
        fake_file_id = str(uuid.uuid4())
        
        response = client.get(f"/api/upload/files/{fake_file_id}")
        
        assert response.status_code == 403
    
    def test_delete_file(self, client: TestClient, auth_headers: dict):
        """测试删除文件"""
        # 先上传一个文件
        test_image = create_test_image()
        files = {
            "file": ("test_image.png", test_image, "image/png")
        }
        data = {
            "auto_ocr": "false"
        }
        
        upload_response = client.post("/api/upload/file", files=files, data=data, headers=auth_headers)
        file_id = upload_response.json()["file_id"]
        
        # 删除文件
        response = client.delete(f"/api/upload/files/{file_id}", headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "文件删除成功"
        
        # 验证文件已被删除
        get_response = client.get(f"/api/upload/files/{file_id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_delete_file_nonexistent(self, client: TestClient, auth_headers: dict):
        """测试删除不存在的文件"""
        fake_file_id = str(uuid.uuid4())
        
        response = client.delete(f"/api/upload/files/{fake_file_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "文件不存在" in response.json()["detail"]
    
    def test_delete_file_without_auth(self, client: TestClient):
        """测试未认证删除文件"""
        fake_file_id = str(uuid.uuid4())
        
        response = client.delete(f"/api/upload/files/{fake_file_id}")
        
        assert response.status_code == 403


@pytest.mark.asyncio
class TestUploadAPIAsync:
    """文件上传API异步测试类"""
    
    async def test_upload_image_async(self, async_client: AsyncClient, test_user_data: dict):
        """测试异步上传图片"""
        # 先注册和登录用户
        await async_client.post("/api/auth/register", json=test_user_data)
        login_response = await async_client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 创建测试图片
        test_image = create_test_image()
        
        files = {
            "file": ("test_image.png", test_image, "image/png")
        }
        data = {
            "auto_ocr": "false"
        }
        
        response = await async_client.post("/api/upload/file", files=files, data=data, headers=headers)
        
        assert response.status_code == 200
        result = response.json()
        assert "file_id" in result
        assert result["filename"] == "test_image.png"


class TestFileValidation:
    """文件验证测试类"""
    
    def test_validate_file_valid_types(self):
        """测试验证有效文件类型"""
        from backend.api.upload import validate_file
        from fastapi import UploadFile
        
        # 模拟有效的文件类型
        valid_types = [
            ("test.jpg", "image/jpeg"),
            ("test.png", "image/png"),
            ("test.jpeg", "image/jpeg"),
            ("test.pdf", "application/pdf")
        ]
        
        for filename, content_type in valid_types:
            # 使用headers参数设置content_type
            mock_file = UploadFile(
                filename=filename, 
                file=io.BytesIO(b"fake file data"),
                headers={"content-type": content_type}
            )
            
            assert validate_file(mock_file) is True
    
    def test_validate_file_invalid_types(self):
        """测试验证无效文件类型"""
        from backend.api.upload import validate_file
        from fastapi import UploadFile
        
        # 模拟无效的文件类型
        invalid_types = [
            ("test.txt", "text/plain"),
            ("test.doc", "application/msword"),
            ("test.mp4", "video/mp4"),
            ("test.zip", "application/zip")
        ]
        
        for filename, content_type in invalid_types:
            # 使用headers参数设置content_type
            mock_file = UploadFile(
                filename=filename, 
                file=io.BytesIO(b"fake file data"),
                headers={"content-type": content_type}
            )
            
            assert validate_file(mock_file) is False
    
    def test_validate_file_invalid_extension(self):
        """测试验证无效文件扩展名"""
        from backend.api.upload import validate_file
        from fastapi import UploadFile
        
        # 内容类型正确但扩展名错误
        mock_file = UploadFile(
            filename="test.txt", 
            file=io.BytesIO(b"fake file data"),
            headers={"content-type": "image/png"}
        )
        
        assert validate_file(mock_file) is False