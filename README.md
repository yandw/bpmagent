# 对话式BPM Agent

基于Browser Use模式的智能企业流程自动化助手，专注于智能报销场景。

## 技术架构

### 核心技术栈
- **后端框架**: Python + FastAPI
- **浏览器自动化**: Playwright
- **AI模型**: 阿里百炼 Qwen3
- **OCR服务**: 百度/腾讯/阿里云OCR API 或 自部署PaddleOCR
- **数据库**: PostgreSQL
- **缓存**: Redis
- **前端**: React + WebSocket

### 系统架构图
```
用户界面 (React) 
    ↓ WebSocket
后端API (FastAPI)
    ↓
AI决策引擎 (Qwen3) → OCR服务 → 浏览器控制器 (Playwright)
    ↓                    ↓              ↓
数据库 (PostgreSQL)   文件存储      受控浏览器实例
```

## 核心功能模块

1. **对话交互界面** - 文件上传、自然语言交互、实时状态反馈
2. **AI核心能力** - 意图识别、发票OCR、网页智能理解
3. **浏览器自动化** - 自动登录、表单填充、流程提交
4. **智能校验** - 必填项检测、对话式追问
5. **用户管理** - 认证授权、配置管理、历史记录

## OCR服务推荐

### 1. 百度OCR (推荐)
- **优势**: 发票识别准确率高，专门的增值税发票识别API
- **价格**: 1000次/月免费，超出部分0.006元/次
- **API文档**: https://cloud.baidu.com/doc/OCR/index.html

### 2. 腾讯OCR
- **优势**: 识别速度快，支持多种发票类型
- **价格**: 1000次/月免费，超出部分0.006元/次
- **API文档**: https://cloud.tencent.com/document/product/866

### 3. 阿里云OCR
- **优势**: 与Qwen模型同一生态，集成方便
- **价格**: 500次/月免费，超出部分0.01元/次
- **API文档**: https://help.aliyun.com/product/442365.html

### 4. PaddleOCR (自部署)
- **优势**: 完全免费，数据不出本地
- **缺点**: 需要GPU服务器，维护成本高
- **部署文档**: https://github.com/PaddlePaddle/PaddleOCR

## 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd BPMAgent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

### 2. 配置环境变量
```bash
# 复制配置文件
cp .env.example .env

# 编辑配置文件，填入你的API密钥
vim .env
```

### 3. 数据库初始化
```bash
# 启动PostgreSQL和Redis
# 运行数据库迁移
alembic upgrade head
```

### 4. 启动服务
```bash
# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动前端 (另一个终端)
cd frontend
npm install
npm start
```

## 项目结构
```
BPMAgent/
├── app/                    # 后端应用
│   ├── api/               # API路由
│   ├── core/              # 核心配置
│   ├── models/            # 数据模型
│   ├── services/          # 业务逻辑
│   │   ├── ai/           # AI服务
│   │   ├── ocr/          # OCR服务
│   │   └── browser/      # 浏览器自动化
│   └── main.py           # 应用入口
├── frontend/              # 前端应用
├── tests/                 # 测试文件
├── uploads/               # 文件上传目录
├── requirements.txt       # Python依赖
├── .env.example          # 环境变量模板
└── README.md             # 项目说明
```

## 开发计划

- [x] 项目架构设计
- [ ] 核心模块实现
- [ ] 前端界面开发
- [ ] 集成测试
- [ ] 性能优化
- [ ] 部署文档

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License