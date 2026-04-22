# 视频监控报警系统

基于 AI 目标追踪与人脸识别的视频流陌生人检测报警系统。

## 功能特性

- 🎥 多路 RTSP 视频流实时监控（1/4/9/16 宫格切换）
- 🏃 YOLO + ByteTrack 多目标追踪（实时人员检测与跟踪）
- 👤 CompreFace 人脸识别（已知人员自动降级报警）
- 🚨 陌生人/黑名单实时报警（WebSocket 推送 + 持久化通知面板）
- 📊 报警记录管理与统计（ECharts 趋势图、CSV 导出）
- 👥 已知人员库管理（分组、多图注册）
- 📹 摄像头与区域管理
- 🔔 WebSocket 实时双向通信（心跳、订阅）
- 🕐 定时数据清理（APScheduler）
- 🔒 JWT 认证 + 角色权限控制

## 系统架构

```
RTSP 摄像头 → CameraCapture（采集线程）
    → YoloTracker（YOLO 检测 + ByteTrack 追踪）
        → annotated_frame → StreamBroadcaster → MJPEG → 前端 <img>
        → TrackerEvent → CompreFace 识别 → 决策引擎
            → 已知人员 → INFO 级日志
            → 陌生人   → CRITICAL 报警 → DB 入库 + WebSocket 推送
```

## 技术栈

### 后端
- **框架**: FastAPI（异步）
- **数据库**: PostgreSQL 15+（asyncpg 异步驱动）
- **ORM**: SQLAlchemy 2.0（Async）
- **目标检测**: YOLO v8/v11（Ultralytics）
- **多目标追踪**: ByteTrack
- **人脸识别**: CompreFace（远程 REST API）
- **视频处理**: OpenCV（RTSP 采集、帧编码）
- **实时通信**: WebSocket（FastAPI 原生）
- **任务调度**: APScheduler
- **日志**: RotatingFileHandler（app.log + error.log）

### 前端
- **框架**: Vue 3（Composition API + TypeScript）
- **构建工具**: Vite 5
- **UI 组件**: Shadcn-vue（基于 Radix-vue）
- **样式**: TailwindCSS 3
- **状态管理**: Pinia
- **图表**: ECharts（vue-echarts）
- **图标**: Lucide、Heroicons

## 项目结构

```
video-warning/
├── backend/                        # 后端代码
│   ├── app/
│   │   ├── api/v1/                # API 路由
│   │   │   ├── auth.py                # 认证（登录/登出/Token 刷新）
│   │   │   ├── cameras.py            # 摄像头 CRUD + 分析控制
│   │   │   ├── stream.py             # MJPEG 实时视频流（带鉴权）
│   │   │   ├── persons.py            # 人员管理 + 人脸上传
│   │   │   ├── groups.py             # 人员分组
│   │   │   ├── alerts.py             # 报警记录 + 统计 + 导出
│   │   │   ├── settings.py           # 系统配置（热更新）
│   │   │   └── ...
│   │   ├── core/                  # 核心模块
│   │   │   ├── config.py              # Pydantic Settings 配置
│   │   │   ├── security.py            # JWT + bcrypt
│   │   │   ├── database.py            # 异步数据库引擎（连接池）
│   │   │   ├── logging_config.py      # 日志轮转配置
│   │   │   └── scheduler.py           # APScheduler 定时任务
│   │   ├── engine/                # 视频分析引擎
│   │   │   ├── manager.py             # 引擎管理器（多摄像头调度）
│   │   │   ├── capture/               # RTSP 采集（断流重连）
│   │   │   ├── analyzers/tracker.py   # YOLO + ByteTrack 追踪器
│   │   │   ├── recognition/client.py  # CompreFace 客户端（并发控制）
│   │   │   └── stream.py             # MJPEG 帧广播器（Pub/Sub）
│   │   ├── websocket/             # WebSocket 处理
│   │   │   ├── manager.py             # 连接管理（心跳、订阅）
│   │   │   └── handlers.py            # 报警入库 + 推送（合并/降级逻辑）
│   │   ├── models/                # SQLAlchemy 模型
│   │   ├── schemas/               # Pydantic 请求/响应模型
│   │   ├── services/              # 业务逻辑层
│   │   └── tasks/cleanup.py       # 过期数据清理
│   ├── data/models/               # YOLO 模型文件
│   │   ├── yolo11n.pt                 # 身体检测模型
│   │   └── face_yolov8n.pt            # 人脸检测模型
│   ├── logs/                      # 日志目录（自动创建）
│   ├── main.py                    # 应用入口
│   └── requirements.txt
├── frontend/                       # 前端代码
│   ├── src/
│   │   ├── api/index.ts           # Axios 封装 + 全部 API
│   │   ├── components/business/   # 业务组件（LiveStream 等）
│   │   ├── composables/           # 组合函数（useWebSocket 等）
│   │   ├── views/                 # 页面（监控/报警/人员/设置等）
│   │   ├── stores/                # Pinia 状态管理
│   │   └── types/                 # TypeScript 类型定义
│   └── package.json
├── data/                           # 运行时数据
│   ├── captures/                  # 报警截图（按日期/摄像头/类型分目录）
│   └── faces/                     # 人脸库图片
└── docs/                           # 部署文档
    └── deploy_almalinux9.md       # AlmaLinux 9 部署指南
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 15+
- CompreFace 服务（外部人脸识别引擎）
- YOLO 模型文件（`yolo11n.pt` + `face_yolov8n.pt`，放入 `backend/data/models/`）

### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env：数据库连接、CompreFace 地址等

# 运行数据库迁移
alembic upgrade head

# 启动服务（开发模式）
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 前端启动

```bash
cd frontend

npm install
npm run dev
```

### CompreFace 部署

```bash
# Docker 方式部署 CompreFace（参考官方文档）
docker-compose -f docker-compose.yml up -d

# 在 .env 中配置
COMPREFACE_URL=http://<compreface-host>:8000
COMPREFACE_API_KEY=<your-api-key>
```

## API 文档

启动后端服务后访问：
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
- 健康检查: http://localhost:8001/health

## 开发计划

详见 [todo.md](./todo.md)

## 部署指南

详见 [AlmaLinux 9 部署指南](./docs/deploy_almalinux9.md)

## 许可证

MIT License
