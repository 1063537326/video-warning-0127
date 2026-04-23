# 本地开发测试启动指南

> 适用于 Windows 环境，基于当前项目实际配置

---

## 📋 前置检查清单

在启动之前，请确认以下服务/文件已就绪：

| 项目 | 要求 | 验证方式 |
|------|------|----------|
| PostgreSQL | 运行中，端口 `5432` | 终端输入 `psql -U postgres -c "SELECT 1"` |
| 数据库 | 已创建 `video_warning` 数据库 | `psql -U postgres -l` 查看列表 |
| Python 虚拟环境 | 已安装依赖 | `backend\venv\` 目录存在 |
| Node.js | 已安装前端依赖 | `frontend\node_modules\` 目录存在 |
| YOLO 模型 | 模型文件存在 | `backend\data\models\yolo11n.pt` |
| CompreFace（可选） | 服务运行在 `172.16.18.22:8000` | 人脸识别功能需要，不影响其他功能 |

---

## 🚀 启动步骤

### 步骤 1：启动后端

打开一个 **PowerShell 终端**：

```powershell
# 进入后端目录
cd d:\MX_Projects\works\video-warning-0127\backend

# 激活虚拟环境
.\venv\Scripts\activate

# 启动后端服务（开发模式，自动重载）
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

**启动成功的标志**（看到以下关键日志）：

```
日志系统已初始化: 目录=logs, 级别=DEBUG
WebSocket 管理器已启动
YOLO 模型加载成功
视频分析引擎初始化成功
INFO:     Uvicorn running on http://127.0.0.1:8001
```

> **注意**：如果看到 CompreFace `unreachable` 的警告是正常的（CompreFace 不在本机），
> 只是人脸识别功能不可用，不影响视频流和目标追踪。

### 步骤 2：启动前端

**新开一个** PowerShell 终端：

```powershell
# 进入前端目录
cd d:\MX_Projects\works\video-warning-0127\frontend

# 启动开发服务器
npm run dev
```

**启动成功的标志**：

```
VITE v5.4.21  ready in 481 ms

  ➜  Local:   http://localhost:5173/
```

### 步骤 3：打开浏览器

在浏览器中访问：**http://localhost:5173**

---

## 🔍 功能验证

### 1. 登录

- 使用已有的账户登录（如果没有账户，参见下方"创建测试用户"）

### 2. 健康检查（无需登录）

直接浏览器访问：**http://localhost:8001/health**

预期返回：

```json
{
  "status": "healthy",
  "app": "VideoWarningSystem",
  "version": "1.0.0",
  "engine_status": "running",
  "websocket_clients": 0,
  "checks": {
    "engine": "running",
    "database": "ok",
    "compreface": "unreachable"    // 如果 CompreFace 不可达，这里会是 unreachable
  }
}
```

### 3. API 文档

- Swagger UI: **http://localhost:8001/docs**
- ReDoc: **http://localhost:8001/redoc**

### 4. 实时视频流

登录后进入「实时监控」页面，可以看到摄像头画面。如果摄像头已配置且 RTSP 流可达，
画面会实时显示带有 YOLO 检测框的视频流。

### 5. WebSocket 验证

打开浏览器开发者工具（F12）→ Network → WS 标签页，应看到：
- 一条 `/ws` 连接（全局唯一）
- 定期的 `ping/pong` 心跳消息

---

## 🛠️ 常用命令

### 创建测试用户（如果数据库是空的）

```powershell
cd d:\MX_Projects\works\video-warning-0127\backend
.\venv\Scripts\activate

# 进入 Python 交互式环境
python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash

async def create_admin():
    async with AsyncSessionLocal() as db:
        user = User(
            username='admin',
            password_hash=get_password_hash('admin123'),
            role=UserRole.admin,
            is_active=True
        )
        db.add(user)
        await db.commit()
        print('管理员用户创建成功: admin / admin123')

asyncio.run(create_admin())
"
```

### 数据库迁移

```powershell
cd d:\MX_Projects\works\video-warning-0127\backend
.\venv\Scripts\activate
alembic upgrade head
```

### 查看日志

```powershell
# 实时查看全量日志
Get-Content -Wait d:\MX_Projects\works\video-warning-0127\backend\logs\app.log

# 只看错误日志
Get-Content -Wait d:\MX_Projects\works\video-warning-0127\backend\logs\error.log
```

### 停止服务

在对应终端按 `Ctrl + C` 即可停止。

---

## ⚠️ 常见问题

### Q: 后端启动报 `ModuleNotFoundError`

**原因**：未激活虚拟环境或依赖未安装

```powershell
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Q: 数据库连接失败

**原因**：PostgreSQL 未启动或连接信息不对

检查 `backend\.env` 中的 `DATABASE_URL`：
```
DATABASE_URL=postgresql+asyncpg://postgres:123456@127.0.0.1:5432/video_warning
```

确保密码（`123456`）和数据库名（`video_warning`）正确。

### Q: 前端页面空白或 API 报 CORS 错误

**原因**：后端未启动，或 CORS 配置不匹配

确认：
1. 后端在 `127.0.0.1:8001` 运行中
2. 前端在 `localhost:5173` 运行中（Vite 会自动代理 `/api` 和 `/ws` 请求到后端）

### Q: 视频流黑屏

**原因**：摄像头 RTSP 地址不可达

在「摄像头管理」页面检查 RTSP URL 是否正确，确保摄像头在网络中可访问。

### Q: 报警功能不触发

**原因**：CompreFace 服务不可达

当前 CompreFace 配置地址为 `172.16.18.22:8000`，仅在该网络环境下可用。
目标追踪和视频流不受影响，仅人脸识别报警需要 CompreFace。

---

## 📁 关键配置文件

| 文件 | 用途 |
|------|------|
| `backend/.env` | 后端所有环境变量（数据库、JWT、CompreFace 等） |
| `frontend/vite.config.ts` | 前端代理配置（API/WS/静态文件代理到后端） |
| `backend/app/core/config.py` | 后端配置类（`.env` 的 Pydantic 映射） |
