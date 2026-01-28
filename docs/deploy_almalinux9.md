# 视频监控报警系统 - AlmaLinux 9 部署指南

本文档详细介绍了如何在 AlmaLinux 9 服务器上部署视频监控报警系统，包括环境准备、后端部署、前端构建、数据库配置以及 Nginx 反向代理设置。

---

## 1. 前期准备 (Environment Preparation)

### 1.1 系统更新与基础工具安装

首先更新系统并安装必要的开发工具：

```bash
# 更新系统
sudo dnf update -y

# 安装基础工具
sudo dnf install -y git wget tar curl vim gcc gcc-c++ make openssl-devel bzip2-devel libffi-devel zlib-devel
```

### 1.2 安装 Python 3.11
项目需要 Python 3.10+，AlmaLinux 9 默认源中包含 Python 3.11。

```bash
# 安装 Python 3.11
sudo dnf install -y python3.11 python3.11-devel python3.11-pip

# 验证安装
python3.11 --version
```

### 1.3 安装 PostgreSQL 15
安装 PostgreSQL 15 数据库服务器。

```bash
# 安装 PostgreSQL 仓库 RPM
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# 禁用默认 PostgreSQL 模块
sudo dnf -qy module disable postgresql

# 安装 PostgreSQL 15 服务端
sudo dnf install -y postgresql15-server

# 初始化数据库
sudo /usr/pgsql-15/bin/postgresql-15-setup initdb

# 启动并设置开机自启
sudo systemctl enable postgresql-15
sudo systemctl start postgresql-15
```

### 1.4 安装 Node.js 20+ (用于前端构建)
使用 NodeSource 源安装 Node.js。

```bash
# 添加 NodeSource 仓库
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -

# 安装 Node.js
sudo dnf install -y nodejs

# 验证安装
node -v
npm -v
```

### 1.5 安装 OpenCV 依赖库
OpenCV 需要一些图形库支持才能运行。

```bash
sudo dnf install -y mesa-libGL libXext libXrender libICE libSM
```

---

## 2. 数据库配置 (Database Configuration)

### 2.1 创建数据库与用户
登录 PostgreSQL 创建项目专用的数据库和用户。

```bash
# 切换到 postgres 用户
sudo -i -u postgres

# 进入 psql 命令行
psql

# --- SQL 操作 ---
-- 创建数据库
CREATE DATABASE video_warning;

-- 创建用户 (密码请自行修改)
CREATE USER video_user WITH PASSWORD 'your_secure_password';

-- 授权
GRANT ALL PRIVILEGES ON DATABASE video_warning TO video_user;
GRANT ALL ON SCHEMA public TO video_user;

-- 退出
\q
# --- SQL 结束 ---

# 退出 postgres 用户
exit
```

### 2.2 配置 PostgreSQL 允许密码登录
编辑 `pg_hba.conf` 文件，允许本地密码认证。

```bash
# 编辑配置文件 (路径可能略有不同)
sudo vim /var/lib/pgsql/15/data/pg_hba.conf
```

找到 `IPv4 local connections` 部分，将 `ident` 或 `scram-sha-256` 修改为 `scram-sha-256` (如果是 ident 必须改)，确保如下所示：

```conf
# TYPE  DATABASE        USER            ADDRESS                 METHOD
host    all             all             127.0.0.1/32            scram-sha-256
```

重启数据库：
```bash
sudo systemctl restart postgresql-15
```

---

## 3. 后端部署 (Backend Deployment)

假设项目代码上传至 `/opt/video-warning`。

### 3.1 代码准备与虚拟环境
```bash
# 创建目录并赋权 (假设当前用户为 deploy_user)
sudo mkdir -p /opt/video-warning
sudo chown -R $USER:$USER /opt/video-warning

# ... 此时请上传代码到该目录 ...
cd /opt/video-warning/backend

# 创建虚拟环境
python3.11 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.2 环境变量配置
```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
vim .env
```
**重点修改内容**：
- `DATABASE_URL`: `postgresql+asyncpg://video_user:your_secure_password@127.0.0.1:5432/video_warning`
- `SECRET_KEY`: 生成一个新的随机字符串

### 3.3 数据库迁移
```bash
# 执行 Alembic 迁移，创建表结构

alembic upgrade head

### 3.4 数据目录准备
由于 `data/captures` 和 `data/faces` 目录被 Git 忽略，需要手动创建这些目录。模型文件 (`data/models`) 已包含在 Git 仓库中，无需手动上传。

```bash
# 进入后端目录
cd /opt/video-warning/backend

# 创建数据存储目录
mkdir -p data/captures
mkdir -p data/faces

# 设置目录权限 (确保运行用户有写权限)
# 假设运行用户为 root (如 Systemd 配置所示)，或者是 deploy_user
sudo chmod -R 755 data
```
```

---

## 4. 前端部署 (Frontend Deployment)

### 4.1 编译构建
```bash
cd /opt/video-warning/frontend

# 安装依赖
npm install

# 环境变量配置 (生产环境)
vim .env.production
# 内容示例:
# VITE_API_BASE_URL=/api/v1
# VITE_WS_URL=wss://your-domain.com/ws  (如果配置了 SSL)
# 或 VITE_WS_URL=ws://your-ip:80/ws (通过 Nginx 转发)
# 注意：后端端口已改为 8001，若直连后端请使用 8001

# 构建项目
npm run build
```
构建完成后，静态文件将位于 `frontend/dist` 目录。

---

## 5. Nginx 配置 (Reverse Proxy)

> **⚠️ 注意**：由于服务器上可能运行着 CompreFace (默认占用 8000 端口)，我们将本项目的后端服务配置在 **8001** 端口，并通过 Nginx (80) 进行转发。

### 5.1 安装 Nginx
```bash
sudo dnf install -y nginx
sudo systemctl enable nginx
```

### 5.2 配置站点
创建配置文件 `/etc/nginx/conf.d/video-warning.conf`：

```nginx
server {
    listen 80;
    server_name your_server_ip_or_domain;

    # 前端静态文件
    location / {
        root /opt/video-warning/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理 (转发到 8001)
    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API 文档代理 (Swagger/Redoc)
    location /docs {
        proxy_pass http://127.0.0.1:8001/docs;
        proxy_set_header Host $host;
    }
    location /openapi.json {
        proxy_pass http://127.0.0.1:8001/openapi.json;
        proxy_set_header Host $host;
    }

    # WebSocket 代理
    location /ws {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # 静态资源 (截图等)
    location /static {
        alias /opt/video-warning/backend/data;
        expires 7d;
    }
}
```

由于 SELinux 可能会阻止 Nginx 访问文件或网络，建议临时测试时宽容模式，生产环境需配置 SELinux 策略：
```bash
# 允许 Nginx 网络连接
sudo setsebool -P httpd_can_network_connect 1

# 或者如果在测试环境，可以临时宽容
sudo setenforce 0
```
*注意：更安全的方式是给予 `/opt/video-warning` 目录正确的 SELinux 上下文：*
```bash
sudo chcon -R -t httpd_sys_content_t /opt/video-warning/frontend/dist
```

重启 Nginx：
```bash
sudo nginx -t
sudo systemctl restart nginx
```

---

## 6. Systemd 服务配置 (Process Management)

使用 Systemd 管理后端服务，确保开机自启和异常重启。

### 6.1 创建后端服务文件
编辑 `/etc/systemd/system/video-backend.service`:

```ini
[Unit]
Description=Video Warning Backend Service
After=network.target postgresql-15.service

[Service]
# 修改为实际的用户和组 (8001 是非特权端口，建议使用非 root 用户，如 deploy_user)
User=root
Group=root
WorkingDirectory=/opt/video-warning/backend
Environment="PATH=/opt/video-warning/backend/venv/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin"

# 启动命令 (使用 uvicorn，端口修改为 8001 以避开 CompreFace)
ExecStart=/opt/video-warning/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 4

# 自动重启
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.2 启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable video-backend
sudo systemctl start video-backend

# 查看状态
sudo systemctl status video-backend
```

---

## 7. 视频分析进程 (可选)

如果视频分析逻辑是独立运行的脚本（如 `videos.py`），建议也配置为一个 Systemd 服务。

编辑 `/etc/systemd/system/video-analyze.service`:

```ini
[Unit]
Description=Video Warning Analysis Process
After=network.target video-backend.service

[Service]
User=root
WorkingDirectory=/opt/video-warning
Environment="PATH=/opt/video-warning/backend/venv/bin:/usr/local/bin:/usr/bin"
# 确保 PYTHONPATH 包含 backend 目录，以便导入 app 模块
Environment="PYTHONPATH=/opt/video-warning/backend"

# 启动命令
ExecStart=/opt/video-warning/backend/venv/bin/python3 videos.py

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动分析服务：
```bash
sudo systemctl enable video-analyze
sudo systemctl start video-analyze
```

---

## 8. 防火墙设置

如果需要外部访问，请开放 HTTP 端口。

```bash
# 开放 80 端口
sudo firewall-cmd --permanent --add-service=http

# 如果使用了 HTTPS
sudo firewall-cmd --permanent --add-service=https

# 重新加载防火墙
sudo firewall-cmd --reload
```

## 9. 维护与日志

- **查看后端日志**:
  `sudo journalctl -u video-backend -f`
- **查看分析服务日志**:
  `sudo journalctl -u video-analyze -f`
- **查看 Nginx 日志**:
  `/var/log/nginx/error.log`

部署完成！
