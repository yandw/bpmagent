# 后端服务接口测试

本目录包含BPMAgent后端服务的所有接口测试。

## 目录结构

```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py             # pytest配置和公共fixtures
├── test_auth.py            # 认证相关接口测试
├── test_chat.py            # 聊天相关接口测试
├── test_upload.py          # 文件上传相关接口测试
├── run_tests.py            # 测试运行脚本
└── README.md               # 本文档
```

## 测试覆盖范围

### 认证接口 (test_auth.py)
- ✅ 用户注册 (`POST /api/auth/register`)
- ✅ 用户登录 (`POST /api/auth/login`)
- ✅ 获取当前用户信息 (`GET /api/auth/me`)
- ✅ 刷新访问令牌 (`POST /api/auth/refresh`)
- ✅ 各种错误情况处理

### 聊天接口 (test_chat.py)
- ✅ 创建聊天会话 (`POST /api/chat/sessions`)
- ✅ 获取用户会话列表 (`GET /api/chat/sessions`)
- ✅ 获取特定会话信息 (`GET /api/chat/sessions/{session_id}`)
- ✅ 获取会话历史记录 (`GET /api/chat/sessions/{session_id}/history`)
- ✅ WebSocket连接测试
- ✅ 权限验证和错误处理

### 文件上传接口 (test_upload.py)
- ✅ 图片文件上传 (`POST /api/upload/image`)
- ✅ OCR处理 (`POST /api/upload/ocr/{file_id}`)
- ✅ 获取文件信息 (`GET /api/upload/files/{file_id}`)
- ✅ 删除文件 (`DELETE /api/upload/files/{file_id}`)
- ✅ 文件格式验证
- ✅ 权限验证和错误处理

## 运行测试

### 1. 使用测试运行脚本 (推荐)

```bash
# 进入backend目录
cd backend

# 运行所有测试
python tests/run_tests.py

# 运行特定类型的测试
python tests/run_tests.py --auth      # 只运行认证测试
python tests/run_tests.py --chat      # 只运行聊天测试
python tests/run_tests.py --upload    # 只运行上传测试

# 交互式选择测试
python tests/run_tests.py -i

# 生成覆盖率报告
python tests/run_tests.py -c

# 生成详细测试报告
python tests/run_tests.py -r

# 详细输出
python tests/run_tests.py -v
```

### 2. 直接使用pytest

```bash
# 进入backend目录
cd backend

# 运行所有测试
python -m pytest tests/

# 运行特定测试文件
python -m pytest tests/test_auth.py -v

# 生成覆盖率报告
python -m pytest tests/ --cov=backend --cov-report=html

# 运行特定测试方法
python -m pytest tests/test_auth.py::TestAuthAPI::test_register_success -v
```

## 测试环境配置

测试使用独立的SQLite数据库，不会影响开发或生产数据。测试配置在 `conftest.py` 中定义：

- **数据库**: SQLite内存数据库 (`sqlite:///./test_database.db`)
- **认证**: 自动处理用户注册和登录
- **文件上传**: 使用临时目录
- **依赖注入**: 自动覆盖生产环境依赖

## 测试数据

测试使用以下默认测试数据：

```python
test_user_data = {
    "username": "testuser",
    "email": "test@example.com", 
    "password": "testpassword123",
    "full_name": "Test User"
}
```

## 依赖要求

确保安装以下测试依赖：

```bash
pip install pytest pytest-asyncio httpx pillow
```

## 注意事项

1. **测试隔离**: 每个测试都使用独立的数据库会话
2. **异步支持**: 支持同步和异步测试
3. **文件清理**: 测试结束后自动清理临时文件
4. **错误处理**: 全面测试各种错误情况
5. **权限验证**: 测试认证和授权机制

## 测试报告

运行测试后可以查看以下报告：

- **控制台输出**: 实时测试结果
- **HTML覆盖率报告**: `htmlcov/index.html`
- **JUnit XML报告**: `test_results.xml`

## 故障排除

### 常见问题

1. **导入错误**: 确保在backend目录下运行测试
2. **依赖缺失**: 运行 `pip install -r requirements.txt`
3. **数据库锁定**: 确保没有其他进程使用测试数据库
4. **端口冲突**: 测试不需要启动服务器，使用TestClient

### 调试技巧

```bash
# 详细输出和错误信息
python -m pytest tests/ -v --tb=long

# 只运行失败的测试
python -m pytest tests/ --lf

# 进入调试模式
python -m pytest tests/ --pdb
```

## 贡献指南

添加新测试时请遵循以下规范：

1. **命名规范**: 测试文件以 `test_` 开头
2. **测试类**: 使用 `TestXXXAPI` 命名
3. **测试方法**: 使用 `test_` 开头的描述性名称
4. **文档字符串**: 为每个测试添加中文说明
5. **断言**: 使用清晰的断言消息
6. **清理**: 确保测试后清理资源