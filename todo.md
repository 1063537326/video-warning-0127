# 视频监控报警系统 - 开发待办清单

> 基于 Requirements.md V2.0 需求文档制定的开发计划

## 📋 项目概览

| 项目名称 | 视频流陌生人检测报警系统 |
|---------|------------------------|
| 技术栈（后端） | FastAPI + SQLAlchemy (Async) + OpenCV + InsightFace |
| 技术栈（前端） | Vue 3 + Vite + Shadcn-vue + TailwindCSS |
| 数据库 | PostgreSQL 15+ |
| 实时通信 | WebSocket |

---

## 🏗️ 阶段一：项目基础设施搭建

### 1.1 开发环境配置
- [x] 创建项目目录结构（前后端分离）
  ```
  video-warning/
  ├── backend/                    # 后端代码
  │   ├── app/
  │   │   ├── api/                # API 路由
  │   │   │   ├── v1/
  │   │   │   │   ├── auth.py         # 认证接口
  │   │   │   │   ├── users.py        # 用户管理
  │   │   │   │   ├── cameras.py      # 摄像头管理
  │   │   │   │   ├── zones.py        # 区域管理
  │   │   │   │   ├── persons.py      # 人员管理
  │   │   │   │   ├── groups.py       # 人员分组
  │   │   │   │   ├── alerts.py       # 报警记录
  │   │   │   │   ├── settings.py     # 系统配置
  │   │   │   │   └── logs.py         # 操作日志
  │   │   │   └── deps.py             # 依赖注入
  │   │   ├── core/               # 核心配置
  │   │   │   ├── config.py           # 配置管理
  │   │   │   ├── security.py         # 安全（JWT、加密）
  │   │   │   └── database.py         # 数据库连接
  │   │   ├── models/             # SQLAlchemy 模型
  │   │   │   ├── user.py
  │   │   │   ├── camera.py
  │   │   │   ├── person.py
  │   │   │   ├── alert.py
  │   │   │   └── ...
  │   │   ├── schemas/            # Pydantic 模型
  │   │   ├── services/           # 业务逻辑层
  │   │   ├── engine/             # 视频分析引擎
  │   │   │   ├── capture/            # 视频采集
  │   │   │   ├── recognition/        # 人脸识别
  │   │   │   ├── pipeline/           # 分析管道
  │   │   │   └── manager.py          # 引擎管理器
  │   │   ├── websocket/          # WebSocket 处理
  │   │   │   ├── manager.py          # 连接管理器
  │   │   │   └── handlers.py         # 消息处理
  │   │   ├── tasks/              # 定时任务
  │   │   │   └── cleanup.py          # 数据清理任务
  │   │   └── utils/              # 工具函数
  │   │       ├── storage.py          # 文件存储
  │   │       └── crypto.py           # 加密工具
  │   ├── alembic/                # 数据库迁移
  │   ├── tests/                  # 测试用例
  │   ├── main.py                 # 应用入口
  │   ├── requirements.txt
  │   └── .env.example
  │
  ├── frontend/                   # 前端代码
  │   ├── src/
  │   │   ├── api/                # API 请求封装
  │   │   ├── assets/             # 静态资源（图片、音效）
  │   │   ├── components/         # 通用组件
  │   │   │   ├── ui/                 # Shadcn 组件
  │   │   │   ├── layout/             # 布局组件
  │   │   │   └── business/           # 业务组件
  │   │   ├── composables/        # 组合式函数
  │   │   ├── router/             # 路由配置
  │   │   ├── stores/             # Pinia 状态管理
  │   │   ├── utils/              # 工具函数
  │   │   ├── views/              # 页面
  │   │   │   ├── auth/               # 登录页
  │   │   │   ├── dashboard/          # 仪表盘
  │   │   │   ├── monitor/            # 实时监控
  │   │   │   ├── alerts/             # 报警记录
  │   │   │   ├── persons/            # 人员管理
  │   │   │   ├── cameras/            # 摄像头管理
  │   │   │   ├── settings/           # 系统设置
  │   │   │   └── ...
  │   │   ├── App.vue
  │   │   └── main.ts
  │   ├── public/
  │   ├── index.html
  │   ├── package.json
  │   ├── tailwind.config.js
  │   ├── vite.config.ts
  │   └── tsconfig.json
  │
  ├── data/                       # 数据存储目录（生产环境可配置其他路径）
  │   ├── captures/               # 报警截图 (按日期分目录)
  │   └── faces/                  # 人脸库图片 (按人员ID分目录)
  │
  ├── logs/                       # 日志目录
  │
  ├── docs/                       # 项目文档
  │
  ├── .gitignore
  └── README.md
  ```
- [x] 配置 Python 3.10+ 虚拟环境
- [x] 配置 Node.js 18+ 环境
- [x] 安装并配置 PostgreSQL 15+ 数据库
- [x] 配置环境变量文件 (.env / .env.example)
- [x] 配置 Git (.gitignore)
- [ ] 编写项目 README.md 文档

### 1.2 后端项目初始化
- [x] 初始化 FastAPI 项目框架
- [x] 配置 SQLAlchemy (Async) ORM
- [x] 配置数据库连接与迁移工具 (Alembic)
- [ ] 配置日志系统 (loguru / logging)
- [ ] 配置 CORS 中间件
- [ ] 配置全局异常处理器
- [ ] 配置 API 限流中间件 (slowapi)
- [ ] 配置静态文件服务 (截图访问)
- [x] 编写 requirements.txt 依赖清单

### 1.3 前端项目初始化
- [ ] 使用 Vite 创建 Vue 3 项目 (TypeScript)
- [ ] 配置 TailwindCSS
- [ ] 安装配置 Shadcn-vue 组件库
- [ ] 配置路由 (Vue Router) + 路由守卫
- [ ] 配置状态管理 (Pinia) + 持久化插件
- [ ] 配置 Axios 请求封装（拦截器、错误处理、Token 刷新）
- [ ] 配置 WebSocket 客户端（断线重连、心跳机制）
- [ ] 配置图表库 (vue-echarts)
- [ ] 配置动画库 (@vueuse/motion)

---

## 🗄️ 阶段二：数据库设计与后端核心开发

### 2.1 数据库模型设计

#### 2.1.1 用户与权限
- [ ] 设计用户表 (users)
  - `id` (PK), `username` (唯一), `password_hash`
  - `email`, `phone` (可选联系方式)
  - `role` (ENUM: admin/operator) - 管理员/操作员
  - `is_active` (启用/禁用)
  - `last_login_at`, `created_at`, `updated_at`

#### 2.1.2 摄像头管理
- [ ] 设计摄像头区域表 (camera_zones) - 区域/楼层分组
  - `id` (PK), `name`, `description`
  - `building`, `floor` (楼栋/楼层，便于多维度筛选)
  - `sort_order`, `created_at`, `updated_at`
- [ ] 设计摄像头配置表 (cameras)
  - `id` (PK), `name`, `zone_id` (FK -> camera_zones)
  - `rtsp_url`, `username`, `password` (加密存储)
  - `resolution`, `fps` (分辨率/帧率配置)
  - `status` (ENUM: online/offline/error) - 连接状态
  - `is_enabled` (是否启用分析)
  - `last_heartbeat_at` (最后心跳时间)
  - `config` (JSONB - 扩展配置：检测区域ROI、灵敏度等)
  - `created_at`, `updated_at`

#### 2.1.3 人员管理
- [ ] 设计人员分组表 (person_groups) - 员工/访客/VIP/黑名单等
  - `id` (PK), `name`, `description`
  - `color` (前端标签颜色)
  - `alert_enabled` (该分组是否触发报警)
  - `alert_priority` (报警优先级)
  - `sort_order`, `created_at`, `updated_at`
- [ ] 设计已知人员表 (known_persons)
  - `id` (PK), `name`, `employee_id` (工号，可选)
  - `group_id` (FK -> person_groups)
  - `department`, `phone`, `remark` (备注)
  - `is_active` (在职/离职)
  - `created_at`, `updated_at`
- [ ] 设计人脸图片表 (face_images) - 一人多图支持
  - `id` (PK), `person_id` (FK -> known_persons)
  - `image_path` (原始图片路径)
  - `feature_vector` (VECTOR(512) - 预留 pgvector 扩展)
  - `quality_score` (图片质量分数)
  - `is_primary` (是否主图)
  - `created_at`

#### 2.1.4 报警记录
- [ ] 设计报警记录表 (alert_logs)
  - `id` (PK), `camera_id` (FK -> cameras)
  - `alert_type` (ENUM: stranger/known/blacklist) - 陌生人/已知人员/黑名单
  - `person_id` (FK -> known_persons, NULL=陌生人)
  - `confidence` (识别置信度 0.0-1.0)
  - `face_image_path` (人脸截图路径)
  - `full_image_path` (全景截图路径)
  - `face_bbox` (JSONB - 人脸框坐标 {x,y,w,h})
  - `status` (ENUM: pending/processed/ignored) - 待处理/已处理/已忽略
  - `processed_by` (FK -> users, 处理人)
  - `processed_at`, `process_remark` (处理备注)
  - `metadata` (JSONB - 扩展字段：特征向量、其他分析结果)
  - `created_at`
  - **索引设计**：`(created_at, camera_id, status)` 复合索引

#### 2.1.5 系统配置
- [ ] 设计系统配置表 (system_configs)
  - `id` (PK), `config_key` (唯一键)
  - `config_value`, `value_type` (string/number/boolean/json)
  - `description` (配置说明)
  - `updated_at`, `updated_by` (FK -> users)
  - **预设配置项**：
    - `face_similarity_threshold` (人脸相似度阈值, 默认0.6)
    - `alert_cooldown_seconds` (同一人报警冷却时间, 默认60秒)
    - `data_retention_days` (数据保留天数, 默认30天)
    - `capture_quality` (截图质量 JPEG 0-100)

#### 2.1.6 操作审计与日志
- [ ] 设计操作日志表 (operation_logs) - 审计追踪
  - `id` (PK), `user_id` (FK -> users)
  - `action` (操作类型: create/update/delete/login/logout)
  - `target_type` (目标类型: camera/person/alert/config)
  - `target_id` (目标ID)
  - `details` (JSONB - 变更详情，before/after)
  - `ip_address`, `user_agent`
  - `created_at`
- [ ] 设计数据清理日志表 (cleanup_logs) - 清理任务记录
  - `id` (PK), `cleanup_type` (alert/capture)
  - `records_deleted` (删除记录数)
  - `files_deleted` (删除文件数)
  - `bytes_freed` (释放空间大小)
  - `started_at`, `finished_at`
  - `status` (success/failed), `error_message`

#### 2.1.7 数据库优化
- [ ] 创建必要索引（时间范围查询、外键关联、状态筛选）
- [ ] 配置 JSONB 字段 GIN 索引（metadata 查询优化）
- [ ] 预留 pgvector 扩展（人脸特征向量相似度检索）
- [x] 创建数据库迁移脚本 (Alembic)

### 2.2 API 接口开发

#### 2.2.1 用户认证模块 (JWT)
- [x] 登录接口 (POST /auth/login)
- [x] 登出接口 (POST /auth/logout)
- [x] 刷新 Token (POST /auth/refresh)
- [x] 获取当前用户信息 (GET /auth/me)
- [x] 修改密码 (PUT /auth/password)

#### 2.2.2 用户管理模块（管理员）
- [x] 用户列表 (GET /users) - 支持分页、关键词搜索、角色筛选、状态筛选
- [x] 创建用户 (POST /users)
- [x] 获取用户详情 (GET /users/{id})
- [x] 编辑用户 (PUT /users/{id})
- [x] 启用/禁用用户 (PATCH /users/{id}/status)
- [x] 重置用户密码 (POST /users/{id}/reset-password)
- [x] 删除用户 (DELETE /users/{id})

#### 2.2.3 摄像头区域管理模块
- [x] 区域列表 (GET /zones) - 支持分页、关键词搜索、楼栋/楼层筛选
- [x] 获取所有区域 (GET /zones/all) - 用于下拉选择
- [x] 获取区域树 (GET /zones/tree) - 按楼栋-楼层分组
- [x] 获取楼栋列表 (GET /zones/buildings)
- [x] 获取楼层列表 (GET /zones/floors)
- [x] 创建区域 (POST /zones)
- [x] 获取区域详情 (GET /zones/{id})
- [x] 编辑区域 (PUT /zones/{id})
- [x] 删除区域 (DELETE /zones/{id}) - 支持强制删除

#### 2.2.4 摄像头管理模块
- [x] 摄像头列表 (GET /cameras) - 支持分页、关键词搜索、区域/状态/启用筛选
- [x] 获取所有摄像头 (GET /cameras/all) - 用于下拉选择
- [x] 新增摄像头 (POST /cameras)
- [x] 获取摄像头详情 (GET /cameras/{id})
- [x] 编辑摄像头 (PUT /cameras/{id})
- [x] 删除摄像头 (DELETE /cameras/{id})
- [x] 测试摄像头连通性 (POST /cameras/{id}/test) - 使用 OpenCV 测试 RTSP 流
- [x] 启用/停用摄像头分析 (PATCH /cameras/{id}/toggle)
- [x] 获取摄像头实时状态 (GET /cameras/status) - 含在线/离线/错误统计
- [x] 更新摄像头状态 (PATCH /cameras/{id}/status) - 内部接口

#### 2.2.5 人员分组管理模块
- [x] 分组列表 (GET /person-groups) - 支持分页、关键词搜索、报警状态筛选
- [x] 获取所有分组 (GET /person-groups/all) - 用于下拉选择
- [x] 获取分组统计 (GET /person-groups/stats) - 含人员数量统计
- [x] 创建分组 (POST /person-groups)
- [x] 获取分组详情 (GET /person-groups/{id})
- [x] 编辑分组 (PUT /person-groups/{id})
- [x] 删除分组 (DELETE /person-groups/{id}) - 支持强制删除
- [x] 切换报警状态 (PATCH /person-groups/{id}/alert)

#### 2.2.6 已知人员管理模块
- [x] 人员列表查询 (GET /persons) - 支持分页、关键词搜索、分组/状态/人脸筛选
- [x] 获取所有人员 (GET /persons/all) - 用于下拉选择
- [x] 新增人员 (POST /persons)
- [x] 获取人员详情 (GET /persons/{id}) - 包含所有人脸图片
- [x] 编辑人员信息 (PUT /persons/{id})
- [x] 更新人员状态 (PATCH /persons/{id}/status) - 在职/离职
- [x] 删除人员 (DELETE /persons/{id}) - 同时删除关联人脸图片
- [x] 上传人脸图片 (POST /persons/{id}/faces) - 支持 JPEG/PNG，最大 5MB
- [x] 删除人脸图片 (DELETE /persons/{id}/faces/{face_id})
- [x] 设置主图 (PATCH /persons/{id}/faces/{face_id}/primary)
- [x] 批量导入人员 (POST /persons/import) - 单次最多 100 条

#### 2.2.7 报警记录模块
- [x] 历史报警查询 (GET /alerts) - 多维度筛选：时间段+区域+摄像头+人员类型+状态
- [x] 报警详情 (GET /alerts/{id})
- [x] 处理报警 (PATCH /alerts/{id}/process)
- [x] 忽略报警 (PATCH /alerts/{id}/ignore)
- [x] 批量处理报警 (POST /alerts/batch-process)
- [x] 报警统计数据 (GET /alerts/statistics) - 仪表盘用
- [x] 报警趋势数据 (GET /alerts/trend) - 图表展示用
- [x] 创建报警 (POST /alerts) - 内部接口
- [x] 导出报警记录 (GET /alerts/export/csv) - CSV格式

#### 2.2.8 系统配置模块
- [x] 获取系统配置 (GET /settings) - 按分组返回
- [x] 获取单个配置项 (GET /settings/item/{key})
- [x] 更新系统配置 (PUT /settings) - 批量更新
- [x] 初始化系统配置 (POST /settings/init-configs)
- [x] 手动触发数据清理 (POST /settings/cleanup) - 支持模拟运行
- [x] 获取清理日志 (GET /settings/cleanup-logs)
- [x] 获取系统状态 (GET /settings/status) - 磁盘空间、数据库、系统信息

#### 2.2.9 操作日志模块
- [x] 操作日志查询 (GET /operation-logs) - 支持用户、操作类型、目标类型、时间筛选
- [x] 操作日志统计 (GET /operation-logs/statistics)
- [x] 获取操作类型列表 (GET /operation-logs/actions)
- [x] 获取目标类型列表 (GET /operation-logs/target-types)
- [x] 操作日志详情 (GET /operation-logs/{id})
- [x] 创建操作日志 (POST /operation-logs) - 内部接口
- [x] 批量删除旧日志 (DELETE /operation-logs)

---

## 🎥 阶段三：视频流处理与人脸识别核心引擎

### 3.1 视频流采集模块
- [x] RTSP 视频流连接管理 (OpenCV VideoCapture)
- [x] 断流自动重连机制（指数退避策略）
- [x] 视频帧队列（生产者端，控制队列大小防内存溢出）
- [x] 多路摄像头并发管理
- [x] 帧率控制/跳帧策略（降低 CPU 负载，如每秒处理 5 帧）
- [x] 摄像头状态上报（在线/离线/错误）

### 3.2 人脸识别模块
- [x] 集成 InsightFace 人脸检测与识别
- [x] 人脸特征向量提取 (512维)
- [x] 人脸特征比对算法（余弦相似度）
- [x] 已知人员/陌生人判定逻辑
- [x] 识别置信度阈值配置（可动态调整）
- [x] 人脸质量评估（模糊、遮挡、角度过大过滤）
- [x] 人脸特征缓存（内存缓存已知人员特征，减少数据库查询）
- [ ] GPU 加速支持 (CUDA / OpenVINO，可选)

### 3.3 分析管道架构 (Pipeline)
- [x] 设计 Processor Pipeline 基类
- [x] 实现 FaceDetectNode（人脸检测节点）
- [x] 实现 FaceRecognizeNode（人脸识别节点）
- [x] 实现 AlertNode（报警生成节点）
- [x] 管道节点动态加载机制（便于未来扩展）

### 3.4 多进程架构实现
- [x] 采集进程（读取 RTSP + 解码）
- [x] 分析进程（人脸检测 + 识别）
- [x] 进程间通信队列 (使用 threading + Queue)
- [x] 进程健康监控与自动重启

---

## 🚨 阶段四：报警与通知系统

### 4.1 报警触发机制
- [x] 陌生人检测触发逻辑
- [x] 报警去重机制（同一人短时间内不重复报警）
- [x] 报警信息组装（截图、时间、摄像头、置信度）

### 4.2 WebSocket 实时推送
- [x] WebSocket 服务端实现 (FastAPI WebSocket)
- [x] 报警消息实时推送（JSON 格式标准化）
- [x] 摄像头状态变更推送
- [x] 系统通知推送（清理完成、服务异常等）
- [x] 客户端心跳检测 (ping/pong)
- [x] 连接管理器（多客户端广播、房间/频道支持）
- [ ] 消息序列化与压缩

### 4.3 报警声音提示
- [ ] 前端报警音效播放
- [ ] 声音开关配置
- [ ] 不同报警级别不同音效（可选）

### 4.4 报警动作接口设计（可扩展）
- [ ] 设计 Action Interface 基类
- [ ] 实现数据库记录 Action
- [ ] 实现 WebSocket 推送 Action
- [ ] 预留短信/邮件/声光报警器扩展接口

---

## 📸 阶段五：存储策略实现

### 5.1 文件存储模块
- [ ] 图片存储路径规划
  - 报警截图：`/data/captures/YYYY/MM/DD/{uuid}.jpg`
  - 人脸库图片：`/data/faces/{person_id}/{uuid}.jpg`
- [ ] 截图保存服务
  - [ ] 人脸截图（裁剪）
  - [ ] 全景截图（完整画面）
  - [ ] 图片压缩（JPEG 质量可配置）
- [ ] 图片访问接口（静态文件服务，带权限验证）

### 5.2 数据清理机制
- [ ] 过期数据自动清理任务（APScheduler 定时任务）
- [ ] 可配置的保留天数（报警记录、截图分别配置）
- [ ] 清理日志记录
- [ ] 磁盘空间监控与告警（空间不足时提醒）

### 5.3 数据备份（可选）
- [ ] 数据库备份脚本 (pg_dump)
- [ ] 重要数据定期备份策略

---

## 🎨 阶段六：前端界面开发

### 6.1 布局与通用组件
- [x] 主布局框架（导航栏 + 侧边栏 + 内容区）
- [ ] 深色/浅色主题切换
- [x] 低饱和度配色方案设计
- [x] 通用表格组件（分页+筛选）
- [x] 通用表单组件
- [x] Loading / Empty 状态组件

### 6.2 核心页面开发
- [x] 登录页面（记住密码、登录动画）
- [x] 仪表盘页面
  - [x] 今日报警统计卡片
  - [ ] 报警趋势折线图 (ECharts)
  - [x] 摄像头状态概览
  - [ ] 最近报警列表
- [x] 实时监控页面
  - [x] 多路视频流展示
  - [x] 视频布局切换（1/4/9/16 宫格）
  - [x] 摄像头状态指示（在线/离线/错误）
  - [x] 信号丢失友好提示
  - [x] 全屏模式
- [x] 报警记录页面
  - [x] 多维度筛选查询（时间、区域、摄像头、类型、状态）
  - [x] 报警详情弹窗（截图放大、人员信息）
  - [x] 批量处理功能
  - [x] 导出 Excel/CSV
- [x] 人员管理页面
  - [x] 人员列表（分页、搜索、按分组筛选）
  - [x] 新增/编辑人员表单
  - [x] 人脸图片上传预览（多图支持）
  - [ ] 批量导入功能
- [x] 人员分组管理页面
  - [x] 分组列表
  - [x] 新增/编辑分组（名称、颜色、报警配置）
- [x] 摄像头管理页面
  - [x] 摄像头列表
  - [x] 新增/编辑摄像头表单
  - [x] 连通性测试按钮
  - [x] 按区域分组显示
- [x] 摄像头区域管理页面
  - [x] 区域列表（楼栋、楼层）
  - [x] 新增/编辑区域
- [x] 用户管理页面（管理员）
  - [x] 用户列表
  - [x] 新增/编辑用户
  - [x] 启用/禁用、重置密码
- [x] 操作日志页面
  - [x] 日志列表（分页、筛选）
  - [x] 操作详情查看
- [x] 系统设置页面
  - [x] 识别阈值配置
  - [x] 报警冷却时间配置
  - [x] 数据保留天数配置
  - [x] 存储空间使用情况
  - [x] 手动清理按钮
- [x] 个人中心页面
  - [x] 个人信息查看
  - [x] 修改密码

### 6.3 报警通知组件
- [ ] 持久化通知侧边栏 (Persistent Notification Feed)
  - [ ] 右侧边缘定位（可折叠/展开）
  - [ ] 卡片从右上角滑入动画
  - [ ] 卡片堆叠滚动列表
  - [ ] 卡片内容：截图缩略图、摄像头名称、时间、置信度
  - [ ] 处理/忽略按钮
  - [ ] 点击跳转报警详情
  - [ ] 未读数量徽标
  - [ ] 不遮挡主界面
- [ ] WebSocket 消息接收与状态管理
- [ ] 报警声音提示（可开关）
- [ ] 浏览器通知 (Notification API，可选)

### 6.4 动画与交互优化
- [ ] 页面切换过渡动画
- [ ] 列表加载动画
- [ ] 报警卡片出现/消失动画
- [ ] 按钮交互反馈

---

## 🧪 阶段七：测试与优化

### 7.1 功能测试
- [ ] API 接口测试 (pytest + httpx)
- [ ] 人脸识别准确率测试
- [ ] 多路视频流压力测试
- [ ] WebSocket 连接稳定性测试
- [ ] 数据清理任务测试
- [ ] 权限控制测试（管理员/操作员）

### 7.2 安全测试
- [ ] JWT Token 过期与刷新测试
- [ ] SQL 注入防护测试
- [ ] XSS 防护测试
- [ ] API 限流测试
- [ ] 敏感数据加密验证（密码、RTSP 密码）

### 7.3 性能优化
- [ ] 数据库查询优化（索引设计、慢查询分析）
- [ ] 视频流解码性能优化
- [ ] 人脸特征缓存命中率优化
- [ ] 前端首屏加载优化（懒加载、代码分割）
- [ ] 内存/CPU 占用监控
- [ ] 长时间运行稳定性测试（内存泄漏检测）

### 7.4 兼容性测试
- [ ] 主流浏览器兼容性（Chrome、Edge、Firefox）
- [ ] 不同分辨率屏幕适配

---

## 📦 阶段八：部署与文档

### 8.1 部署准备
- [ ] 生产环境配置文件 (.env.production)
- [ ] 数据库初始化脚本（建表、初始数据）
- [ ] 默认管理员账户创建
- [ ] 服务启动脚本
  - [ ] 后端服务 (systemd / Windows Service)
  - [ ] 视频分析引擎 (独立进程)
- [ ] Nginx 反向代理配置
  - [ ] API 代理
  - [ ] WebSocket 代理
  - [ ] 静态文件服务
  - [ ] HTTPS 配置（可选）

### 8.2 运维监控
- [ ] 服务健康检查接口 (GET /health)
- [ ] 日志文件轮转配置
- [ ] 进程守护与自动重启
- [ ] 磁盘空间监控告警

### 8.3 文档编写
- [ ] API 接口文档 (Swagger/OpenAPI 自动生成)
- [x] 部署指南（详细步骤）
- [ ] 配置说明文档
- [ ] 用户使用手册（操作说明）
- [ ] 常见问题 FAQ

---

## 📝 更新日志

### 2026-01-28 - 部署指南更新与端口冲突解决

**概述**：解决部署环境与现有 CompreFace 服务的端口冲突问题。

**详细内容**：

1. **端口冲突分析与解决**
   - 确认 CompreFace Docker 部署占用宿主机 8000 端口 (UI)
   - 确认 CompreFace PostgreSQL (5432) 仅在容器内部暴露，不占用宿主机端口
   - 调整后端服务部署端口为 **329** 以避开冲突
   - 更新 Nginx 反向代理配置适配新端口

2. **文档更新** (`docs/deploy_almalinux9.md`)
   - 更新 Nginx 配置示例
   - 更新 Systemd 服务启动命令
   - 添加关于端口冲突的警告提示

---

### 2026-01-19 - 实时监控页面增强

**概述**：增强实时监控页面，集成 WebSocket 实时数据、告警通知和摄像头状态更新。

**详细内容**：

1. **WebSocket 集成**
   - 实时接收告警消息
   - 实时接收摄像头状态更新
   - 显示连接状态和引擎状态

2. **告警面板**
   - 右侧可折叠告警面板
   - 显示最近 10 条告警
   - 告警类型标识（陌生人/黑名单/已知人员）
   - 人脸图片缩略图显示
   - 摄像头来源和时间戳

3. **状态指示**
   - WebSocket 连接状态指示
   - 引擎运行状态指示
   - 摄像头实时 FPS 显示
   - 告警数量徽章

**涉及文件**：
- `frontend/src/views/monitor/MonitorView.vue`
- `frontend/src/types/index.ts` (添加缺失字段)

---

### 2026-01-19 - 人员注册时特征同步

**概述**：实现人脸图片上传时自动提取特征并同步到视频分析引擎。

**详细内容**：

1. **人脸特征服务** (`services/face_feature.py`)
   - `FaceFeatureService` 类提供特征提取和同步功能
   - `extract_embedding_from_file()` - 从文件提取特征
   - `extract_embedding_from_bytes()` - 从字节数据提取特征
   - `sync_person_to_engine()` - 同步人员到引擎
   - `remove_person_from_engine()` - 从引擎移除人员
   - `get_database_stats()` - 获取人脸库统计

2. **Persons API 更新** (`api/v1/persons.py`)
   - `POST /{id}/faces` - 上传图片时自动提取特征并同步
   - `POST /sync-to-engine` - 批量同步所有人员到引擎
   - `POST /{id}/sync-to-engine` - 同步单个人员到引擎
   - `GET /engine-database/stats` - 获取引擎人脸库统计
   - `DELETE /{id}` - 删除人员时同步从引擎移除

3. **Schema 更新** (`schemas/person.py`)
   - `FaceUploadResponse` 添加 `feature_extracted` 字段

**涉及文件**：
- `backend/app/services/face_feature.py` (新增)
- `backend/app/api/v1/persons.py`
- `backend/app/schemas/person.py`

---

### 2026-01-19 - 摄像头管理与引擎联动

**概述**：实现摄像头管理与视频分析引擎的联动功能，支持启动/停止摄像头分析。

**详细内容**：

1. **后端 API 更新** (`api/v1/cameras.py`)
   - 修改 `toggle` 接口，启用时自动添加摄像头到引擎，停用时移除
   - 新增 `POST /cameras/{id}/start-analysis` - 启动摄像头分析
   - 新增 `POST /cameras/{id}/stop-analysis` - 停止摄像头分析
   - 新增 `GET /cameras/{id}/analysis-status` - 获取摄像头分析状态

2. **前端 API 更新** (`api/index.ts`)
   - 添加 `startAnalysis()` - 启动分析
   - 添加 `stopAnalysis()` - 停止分析
   - 添加 `getAnalysisStatus()` - 获取分析状态

3. **前端摄像头管理页面** (`views/cameras/CamerasView.vue`)
   - 分析开关与引擎联动
   - 添加"详情"按钮查看分析状态
   - 新增分析状态弹窗，显示：
     - 引擎状态（运行中/连接中/已停止/错误）
     - 启用状态
     - 实时数据（FPS、队列大小、总帧数、已处理帧数）
   - 支持在弹窗中启动/停止分析

**涉及文件**：
- `backend/app/api/v1/cameras.py`
- `frontend/src/api/index.ts`
- `frontend/src/views/cameras/CamerasView.vue`

---

### 2026-01-19 - 前端 WebSocket 集成与引擎状态显示

**概述**：完成前端与后端视频分析引擎的 WebSocket 集成，支持实时报警通知和引擎状态显示。

**详细内容**：

1. **类型定义更新** (`types/index.ts`)
   - 添加 WebSocket 消息类型定义 (`WsMessageType`)
   - 添加 WebSocket 消息接口 (`WsMessage`, `WsAlertData`, `WsCameraStatusData`, `WsEngineStatusData`)
   - 添加引擎状态类型 (`EngineStatus`, `EngineStats`, `EngineCameraStatus`)

2. **WebSocket 组合式函数重构** (`composables/useWebSocket.ts`)
   - 适配后端新的消息格式（connect, pong, alert, camera_status, engine_status 等）
   - Token 认证改为 URL 查询参数方式
   - 添加摄像头订阅/取消订阅功能 (`subscribe`, `unsubscribe`)
   - 添加引擎状态响应式变量
   - 支持 base64 编码的报警图片
   - 优化心跳机制（25秒间隔）

3. **报警 Store 更新** (`stores/alert.ts`)
   - 扩展 `AlertNotification` 接口
   - 支持 base64 data URI 图片格式
   - 添加分组名称、全图字段

4. **API 模块扩展** (`api/index.ts`)
   - 添加 `engineApi` 模块
     - `getStatus()` - 获取引擎状态
     - `getCameras()` - 获取引擎管理的摄像头状态
   - 添加 `healthApi` 模块
     - `check()` - 健康检查

5. **主布局更新** (`components/layout/MainLayout.vue`)
   - 顶部栏添加引擎状态指示器
   - 显示引擎运行状态（运行中/启动中/停止中/已停止/异常/不可用）
   - 状态图标带脉冲动画效果

**涉及文件**：
- `frontend/src/types/index.ts`
- `frontend/src/composables/useWebSocket.ts`
- `frontend/src/stores/alert.ts`
- `frontend/src/api/index.ts`
- `frontend/src/components/layout/MainLayout.vue`

---

### 2026-01-19 16:30 - 前端增强功能开发

**概述**：完成三个重要的前端增强功能：深色主题、ECharts 图表、报警通知组件

**详细内容**：

1. **深色主题功能**
   - 创建 `useTheme.ts` 组合式函数
     - 支持浅色/深色/跟随系统三种模式
     - 本地存储持久化
     - 监听系统主题变化自动切换
   - 更新 `main.css` 添加深色模式样式
     - 所有组件类添加 `dark:` 变体
     - 滚动条、阴影等细节适配
   - 在 `MainLayout` 顶部栏添加主题切换按钮
     - 循环切换模式（浅色→深色→系统）
     - 显示当前模式图标和提示

2. **ECharts 报警趋势图**
   - 在仪表盘页面添加报警趋势图
     - 支持 7天/30天/90天 时间范围切换
     - 堆叠柱状图显示各类型报警数量
     - 自动适配深色主题
   - 添加报警类型分布饼图
     - 显示陌生人/已知人员/黑名单占比
     - 环形图设计，支持悬停高亮

3. **WebSocket 报警通知组件**
   - 增强 `useWebSocket.ts` 组合式函数
     - 支持消息类型分发和事件回调
     - 自动重连机制（指数退避）
     - 内置报警消息处理
   - 更新 `useAlertStore` 状态管理
     - 未读计数、已读标记
     - 声音开关（本地持久化）
     - 侧边栏显示状态
   - 完善 `AlertCard.vue` 报警卡片组件
     - 显示报警类型、摄像头、区域、置信度
     - 时间格式化（相对时间）
     - 缩略图预览
   - 完善 `NotificationFeed.vue` 通知侧边栏
     - 右侧滑入动画
     - 列表项进入/退出动画
     - 清空、声音开关等操作
   - 在 `MainLayout` 添加通知入口
     - 未读数量徽章
     - WebSocket 连接状态指示器

**文件变更**：
- `frontend/src/composables/useTheme.ts` (新增)
- `frontend/src/composables/useWebSocket.ts` (重构)
- `frontend/src/stores/alert.ts` (重构)
- `frontend/src/assets/main.css` (更新)
- `frontend/src/main.ts` (更新)
- `frontend/src/components/layout/MainLayout.vue` (更新)
- `frontend/src/components/business/AlertCard.vue` (重构)
- `frontend/src/components/business/NotificationFeed.vue` (重构)
- `frontend/src/views/dashboard/DashboardView.vue` (更新)

---

### 2026-01-19 14:00 - 实时监控页面开发

**概述**：完成实时监控页面的开发，支持多路视频流展示框架

**详细内容**：

1. **页面功能**
   - 多路视频流网格展示（支持 1/4/9/16 宫格布局）
   - 布局动态切换
   - 全屏模式（浏览器全屏 API）
   - 摄像头选择弹窗（支持区域筛选）
   - 单路放大查看

2. **视频槽位功能**
   - 显示摄像头名称、区域、状态
   - 状态指示灯（在线/离线/错误）
   - 分析状态标记
   - 分辨率和帧率信息
   - 快捷操作（放大、更换、移除）

3. **交互设计**
   - 自动填充在线摄像头
   - 空槽位点击添加
   - 悬停显示操作按钮
   - 渐变遮罩信息栏

4. **待接入**
   - 实际 RTSP 视频流渲染（需后端视频引擎）
   - WebSocket 实时状态更新
   - 报警弹窗叠加

---

### 2026-01-19 13:56 - 前端核心页面开发完成

**概述**：完成所有前端管理页面的开发，实现完整的 CRUD 功能

**详细内容**：

1. **区域管理页面** (`ZonesView.vue`)
   - 区域列表（分页、搜索、楼栋筛选）
   - 新增/编辑/删除区域
   - 显示关联摄像头数量

2. **摄像头管理页面** (`CamerasView.vue`)
   - 摄像头列表（分页、区域/状态筛选）
   - RTSP 配置（地址、认证、分辨率、帧率）
   - 连通性测试（检测分辨率、帧率、响应时间）
   - 启用/禁用分析切换

3. **人员分组页面** (`GroupsView.vue`)
   - 卡片网格展示分组
   - 颜色标签选择（预设+自定义）
   - 报警触发开关
   - 优先级配置

4. **人员管理页面** (`PersonsView.vue`)
   - 人员列表（分页、分组/状态筛选）
   - 人员详情弹窗
   - 人脸图片管理（上传/删除/设为主图）
   - 在职/离职状态切换

5. **报警记录页面** (`AlertsView.vue`)
   - 多维度筛选（日期、区域、摄像头、类型、状态）
   - 报警详情弹窗（截图对比）
   - 批量处理/忽略
   - CSV 导出

6. **用户管理页面** (`UsersView.vue`)
   - 用户列表（角色/状态筛选）
   - 新增/编辑用户
   - 启用/禁用用户
   - 重置密码

7. **操作日志页面** (`LogsView.vue`)
   - 日志列表（用户、操作类型、目标类型、时间筛选）
   - 日志详情（变更前后对比）

8. **系统设置页面** (`SettingsView.vue`)
   - 配置分组展示
   - 配置编辑（文本/数字/布尔类型）
   - 数据清理功能（模拟/实际执行）
   - 系统状态（磁盘、CPU、内存、数据库）

9. **个人中心页面** (`ProfileView.vue`)
   - 个人信息展示
   - 修改密码

**页面特色**：
- 统一的 UI 风格（TailwindCSS + 自定义组件类）
- 响应式设计
- 加载状态和空状态提示
- 分页组件
- 弹窗交互（Teleport）
- 表单验证和错误提示

---

### 2026-01-19 11:00 - 操作日志 API 开发

**概述**：完成操作日志 API 的完整实现，支持操作记录的查询、统计、管理，并提供审计工具函数

**详细内容**：

1. **操作日志 Schemas 创建**
   - 创建 `app/schemas/log.py` 定义操作日志相关数据模型
   - `ActionTypeEnum` - 操作类型枚举（create/update/delete/login/logout/export/import/process/ignore/upload/cleanup）
   - `TargetTypeEnum` - 目标类型枚举（user/camera/zone/person/group/alert/config/face/system）
   - `OperationLogResponse` - 操作日志响应（含用户信息、中文标签）
   - `OperationLogListResponse` - 列表响应（分页）
   - `OperationLogCreateRequest` - 创建请求
   - `OperationLogStatistics` - 统计数据
   - `ACTION_LABELS` / `TARGET_TYPE_LABELS` - 中文标签映射

2. **审计工具函数创建**
   - 创建 `app/utils/audit.py` 提供操作日志记录工具
   - `log_operation()` - 记录操作日志
   - `get_client_ip()` - 获取客户端 IP（支持反向代理）
   - `get_user_agent()` - 获取 User-Agent
   - `log_operation_from_request()` - 从请求对象自动提取信息并记录
   - `build_change_details()` - 构建变更详情（before/after）

3. **操作日志 API 实现** (`app/api/v1/logs.py`)
   - `GET /api/v1/operation-logs` - 获取日志列表（支持用户、操作类型、目标类型、时间、IP 筛选）
   - `GET /api/v1/operation-logs/statistics` - 获取统计数据（按操作/目标/用户统计）
   - `GET /api/v1/operation-logs/actions` - 获取操作类型列表（带中文标签）
   - `GET /api/v1/operation-logs/target-types` - 获取目标类型列表（带中文标签）
   - `GET /api/v1/operation-logs/{log_id}` - 获取日志详情
   - `POST /api/v1/operation-logs` - 创建操作日志（内部接口）
   - `DELETE /api/v1/operation-logs` - 批量删除旧日志（按保留天数）

4. **特色功能**
   - 自动关联用户信息
   - 操作类型和目标类型自动转换为中文标签
   - 支持记录变更前后对比（before/after）
   - 支持 IP 地址模糊搜索
   - 提供审计工具函数便于在其他 API 中记录操作

5. **API 测试验证**
   - ✅ 创建操作日志（4 条：create/update/delete/login）
   - ✅ 获取日志列表（按时间倒序）
   - ✅ 获取统计数据（by_action、by_target_type、by_user）
   - ✅ 按操作类型筛选（action=create）
   - ✅ 获取日志详情（含 before/after 变更详情）
   - ✅ 获取操作类型列表（11 种类型）
   - ✅ 获取目标类型列表（9 种类型）

---

### 2026-01-19 13:12 - 前端开发启动（阶段六）

**概述**：开始前端界面开发，完成项目基础架构、登录页面、仪表盘页面

**详细内容**：

1. **前端依赖安装**
   - 核心依赖：Vue 3.4、Vue Router 4.2、Pinia 2.1、Axios 1.6
   - 图表库：ECharts 5.4、vue-echarts 6.6
   - UI 工具：@vueuse/core、@vueuse/motion、radix-vue
   - 图标：@heroicons/vue、lucide-vue-next
   - 样式工具：class-variance-authority、clsx、tailwind-merge

2. **TailwindCSS 主题配置**
   - 自定义配色方案：primary（深蓝灰）、accent（青蓝）、warning、danger、success
   - 自定义动画：fade-in、slide-in、pulse-slow
   - 组件类：btn、input、card、badge、table、nav-item、stat-card

3. **TypeScript 类型定义** (`src/types/index.ts`)
   - 用户相关：User、LoginRequest、TokenResponse
   - 摄像头相关：Camera、Zone、CameraStatus
   - 人员相关：Person、PersonGroup、FaceImage
   - 报警相关：Alert、AlertStatistics
   - 系统相关：SystemStatus、ConfigGroup、OperationLog

4. **API 模块** (`src/api/index.ts`)
   - authApi - 认证相关（login、logout、getCurrentUser、refreshToken）
   - userApi - 用户管理
   - zoneApi - 区域管理
   - cameraApi - 摄像头管理
   - groupApi - 人员分组
   - personApi - 人员管理
   - alertApi - 报警管理
   - settingsApi - 系统配置
   - logApi - 操作日志

5. **路由配置** (`src/router/index.ts`)
   - 登录页：/login
   - 主布局嵌套路由：dashboard、monitor、alerts、persons、groups、cameras、zones、users、logs、settings、profile
   - 路由守卫：认证检查、管理员权限检查

6. **状态管理** (`src/stores/auth.ts`)
   - 用户状态、Token 管理
   - 登录/登出方法
   - 本地存储持久化

7. **核心页面实现**
   - `MainLayout.vue` - 主布局（侧边栏导航 + 顶部栏）
   - `LoginView.vue` - 登录页面（表单验证、密码显示切换、响应式设计）
   - `DashboardView.vue` - 仪表盘（统计卡片、报警统计、系统状态、快捷入口）

8. **开发服务器**
   - 前端：http://localhost:5173
   - 后端：http://localhost:8000

---

### 2026-01-19 - 后端核心引擎开发

**概述**：完成视频分析引擎的核心功能开发，包括 RTSP 视频流采集、人脸检测与识别、报警生成与推送、WebSocket 服务端

**详细内容**：

1. **视频流采集模块** (`app/engine/capture/`)
   - `CameraCapture` 类 - 单路摄像头 RTSP 流采集
   - `CaptureConfig` - 采集配置（RTSP 地址、帧率、队列大小等）
   - `FrameData` - 帧数据封装（图像、时间戳、分辨率等）
   - 断流自动重连（指数退避策略，初始 1 秒，最大 60 秒）
   - 帧率控制/跳帧策略（降低 CPU 负载）
   - 帧队列管理（防内存溢出，队列满时丢弃旧帧）
   - 摄像头状态回调（在线/离线/错误/重连中）

2. **人脸识别模块** (`app/engine/recognition/`)
   - `FaceDetector` 类 - InsightFace 人脸检测
     - 支持多种模型（buffalo_l、buffalo_s 等）
     - 人脸质量评估（大小、边缘、比例综合评分）
     - 人脸裁剪（带边距）
   - `FaceDatabase` 类 - 人脸特征数据库
     - 特征向量存储与管理
     - 余弦相似度比对
     - 批量识别支持
   - `FaceRecognizer` 类 - 完整识别服务
     - 整合检测与比对
     - 报警冷却管理（防重复报警）
     - 黑名单分组支持
   - `AlertCooldownManager` - 报警冷却控制

3. **分析管道模块** (`app/engine/pipeline/`)
   - `Pipeline` 类 - 管道编排
   - `PipelineNode` 基类 - 节点抽象
   - `PipelineContext` - 上下文数据传递
   - `DetectionNode` - 人脸检测节点
   - `RecognitionNode` - 人脸识别节点
   - `AlertNode` - 报警生成节点
   - `FramePreprocessNode` - 帧预处理节点
   - `PipelineBuilder` - 管道构建器（支持配置化构建）

4. **引擎管理器** (`app/engine/manager.py`)
   - `EngineManager` 类 - 视频分析引擎核心
     - 多摄像头并发管理
     - 采集线程与分析线程分离
     - 健康检查与自动重启
     - 人脸库动态加载
   - `EngineConfig` - 引擎配置
   - 全局引擎实例管理（get_engine、set_engine、create_engine）

5. **WebSocket 增强** (`app/websocket/`)
   - `ConnectionManager` 重构
     - 客户端信息管理（用户、订阅摄像头）
     - 心跳检测与超时断开
     - 摄像头订阅机制
   - 消息处理器增强
     - `push_alert` - 报警推送（支持摄像头订阅者优先）
     - `push_camera_status` - 摄像头状态推送
     - `push_system_notification` - 系统通知推送
     - `push_engine_status` - 引擎状态推送
   - 引擎回调函数（engine_alert_callback、engine_status_callback）

6. **主程序集成** (`main.py`)
   - 引擎生命周期管理（启动、关闭）
   - WebSocket 端点（/ws）
   - 引擎状态 API（/api/v1/engine/status、/api/v1/engine/cameras）
   - 健康检查增强（含引擎状态、WebSocket 客户端数）

7. **依赖更新** (`requirements.txt`)
   - 添加 `insightface>=0.7.3`
   - 添加 `onnxruntime>=1.20.0`（CPU 版本）
   - 注释保留 `onnxruntime-gpu` 供 GPU 加速使用

**文件清单**：
- `app/engine/capture/__init__.py`
- `app/engine/capture/camera_capture.py`
- `app/engine/recognition/__init__.py`
- `app/engine/recognition/face_detector.py`
- `app/engine/recognition/face_database.py`
- `app/engine/recognition/face_recognizer.py`
- `app/engine/pipeline/__init__.py`
- `app/engine/pipeline/base.py`
- `app/engine/pipeline/nodes.py`
- `app/engine/manager.py`
- `app/engine/__init__.py`
- `app/websocket/manager.py`（重构）
- `app/websocket/handlers.py`（重构）
- `app/websocket/__init__.py`
- `main.py`（更新）
- `requirements.txt`（更新）

---

### 2026-01-19 10:36 - 系统配置 API 开发

**概述**：完成系统配置 API 的完整实现，支持配置管理、数据清理、系统状态监控

**详细内容**：

1. **系统配置 Schemas 创建**
   - 创建 `app/schemas/settings.py` 定义系统配置相关数据模型
   - `ConfigValueType` - 配置值类型枚举（string/number/boolean/json）
   - `ConfigItemResponse` - 单个配置项响应
   - `ConfigGroupResponse` - 配置分组响应
   - `SystemConfigResponse` - 系统配置响应（按分组）
   - `ConfigUpdateRequest/Result` - 配置批量更新请求和结果
   - `CleanupTypeEnum` - 清理类型枚举（alert/capture/all）
   - `CleanupRequest/Result` - 数据清理请求和结果
   - `CleanupLogResponse/ListResponse` - 清理日志响应
   - `DiskUsage` - 磁盘使用情况
   - `ServiceStatus` - 服务状态
   - `DatabaseStatus` - 数据库状态
   - `SystemStatusResponse` - 系统状态响应

2. **系统配置 API 实现** (`app/api/v1/settings.py`)
   - `GET /api/v1/settings` - 获取系统配置（按分组返回）
   - `PUT /api/v1/settings` - 批量更新配置
   - `GET /api/v1/settings/item/{key}` - 获取单个配置项
   - `POST /api/v1/settings/init-configs` - 初始化系统配置
   - `POST /api/v1/settings/cleanup` - 手动触发数据清理（支持 dry_run 模拟）
   - `GET /api/v1/settings/cleanup-logs` - 获取清理日志
   - `GET /api/v1/settings/status` - 获取系统状态

3. **特色功能**
   - 配置按分组组织（人脸识别、报警、存储、系统）
   - 数据清理支持模拟运行（dry_run）
   - 清理日志记录详细信息（删除记录数、文件数、释放空间）
   - 系统状态包含：磁盘使用、数据库连接、各表记录数、系统信息
   - 格式化工具函数（字节数、时间长度转可读字符串）

4. **依赖更新**
   - 添加 `psutil>=5.9.0` 用于系统监控

5. **API 测试验证**
   - ✅ 初始化系统配置（已存在时返回提示）
   - ✅ 获取系统配置（按分组：face_recognition、alert、storage）
   - ✅ 更新配置（data_retention_days: 30 → 60）
   - ✅ 获取单个配置项
   - ✅ 数据清理模拟运行（dry_run: true）
   - ✅ 数据清理实际执行（无过期数据）
   - ✅ 获取清理日志
   - ✅ 获取系统状态（数据库连接、9 个表、磁盘空间、系统信息）

---

### 2026-01-19 10:11 - 报警记录 API 开发

**概述**：完成报警记录 API 的完整实现，支持报警的多维度查询、处理/忽略、批量处理、统计分析、趋势数据、CSV 导出

**详细内容**：

1. **报警记录 Schemas 创建**
   - 创建 `app/schemas/alert.py` 定义报警相关数据模型
   - `AlertTypeEnum` - 报警类型枚举（stranger/known/blacklist）
   - `AlertStatusEnum` - 报警状态枚举（pending/processed/ignored）
   - `AlertResponse` - 报警响应（含摄像头、人员、处理人信息）
   - `AlertListResponse` - 报警列表响应（分页）
   - `AlertProcessRequest` / `AlertIgnoreRequest` - 处理/忽略请求
   - `AlertBatchProcessRequest` / `AlertBatchProcessResult` - 批量处理请求和结果
   - `AlertStatistics` - 报警统计数据（按状态、类型、摄像头统计）
   - `AlertTrendItem` / `AlertTrendResponse` - 报警趋势数据
   - `AlertCreateRequest` - 创建报警请求（内部接口）

2. **报警记录 API 实现** (`app/api/v1/alerts.py`)
   - `GET /api/v1/alerts` - 获取报警列表（支持时间范围、摄像头、区域、类型、人员、状态筛选）
   - `GET /api/v1/alerts/statistics` - 获取统计数据（总数、按状态/类型/摄像头统计、今日/本周/本月数量）
   - `GET /api/v1/alerts/trend` - 获取趋势数据（支持 day/week/month 周期）
   - `GET /api/v1/alerts/{alert_id}` - 获取报警详情
   - `PATCH /api/v1/alerts/{alert_id}/process` - 处理报警
   - `PATCH /api/v1/alerts/{alert_id}/ignore` - 忽略报警
   - `POST /api/v1/alerts/batch-process` - 批量处理报警
   - `POST /api/v1/alerts` - 创建报警（内部接口，由视频分析引擎调用）
   - `GET /api/v1/alerts/export/csv` - 导出报警记录为 CSV（仅管理员）

3. **特色功能**
   - 报警响应自动关联摄像头信息（含区域）、人员信息（含分组颜色）、处理人信息
   - 支持按区域筛选（自动查询该区域下所有摄像头的报警）
   - 批量处理支持处理/忽略两种操作，返回成功/失败统计
   - 统计数据包含按摄像头排名（前 10）
   - 趋势数据按日期聚合，区分报警类型

4. **API 测试验证**
   - ✅ 创建报警（5 条：3 stranger、1 known、1 blacklist）
   - ✅ 获取报警列表（按时间倒序，含关联信息）
   - ✅ 获取统计数据（total: 5, pending: 0, processed: 4, ignored: 1）
   - ✅ 处理报警（状态变更为 processed，记录处理人和时间）
   - ✅ 忽略报警（状态变更为 ignored，记录备注）
   - ✅ 批量处理（3 条成功，0 条失败）
   - ✅ 按类型筛选（stranger: 3 条）
   - ✅ 按状态筛选（processed: 4 条）
   - ✅ 获取趋势数据（按天聚合，区分类型）
   - ✅ 报警详情（含完整关联信息）

---

### 2026-01-19 10:04 - 已知人员管理 API 开发

**概述**：完成已知人员管理 API 的完整实现，支持人员的增删改查、人脸图片管理、批量导入等功能

**详细内容**：

1. **人员管理 Schemas 创建**
   - 创建 `app/schemas/person.py` 定义人员相关数据模型
   - `PersonCreate` - 创建人员请求（姓名、工号、分组、部门、电话、备注）
   - `PersonUpdate` - 更新人员请求
   - `PersonStatusUpdate` - 状态更新（在职/离职）
   - `PersonResponse` - 人员响应（含分组信息、人脸数量、主图）
   - `PersonDetailResponse` - 详情响应（含所有人脸图片）
   - `FaceImageResponse` - 人脸图片响应
   - `FaceUploadResponse` - 上传响应
   - `PersonImportRequest/Result` - 批量导入请求和结果

2. **人员管理 API 实现** (`app/api/v1/persons.py`)
   - `GET /api/v1/persons` - 获取人员列表（支持分页、关键词搜索、分组/状态/人脸筛选）
   - `GET /api/v1/persons/all` - 获取所有人员（简化列表，用于下拉选择）
   - `POST /api/v1/persons` - 创建新人员（验证工号唯一性、分组存在性）
   - `GET /api/v1/persons/{person_id}` - 获取人员详情（包含所有人脸图片）
   - `PUT /api/v1/persons/{person_id}` - 更新人员信息
   - `PATCH /api/v1/persons/{person_id}/status` - 更新在职状态
   - `DELETE /api/v1/persons/{person_id}` - 删除人员（同时删除人脸图片文件）
   - `POST /api/v1/persons/{person_id}/faces` - 上传人脸图片
   - `DELETE /api/v1/persons/{person_id}/faces/{face_id}` - 删除人脸图片
   - `PATCH /api/v1/persons/{person_id}/faces/{face_id}/primary` - 设置主图
   - `POST /api/v1/persons/import` - 批量导入人员

3. **特色功能**
   - 人员响应自动包含分组颜色、人脸数量、主图信息
   - 人脸图片上传支持 JPEG/PNG，最大 5MB
   - 第一张上传的图片自动设为主图
   - 删除人员时自动清理关联的人脸图片文件
   - 批量导入支持错误收集和部分成功

4. **API 测试验证**
   - ✅ 创建人员（6 人：3 Employee、1 Visitor、1 VIP、1 Blacklist）
   - ✅ 获取人员列表（分页）
   - ✅ 获取人员详情
   - ✅ 更新人员信息
   - ✅ 分组筛选、关键词搜索
   - ✅ 更新在职状态
   - ✅ 批量导入（3 人成功）
   - ✅ 分组统计正确更新

---

### 2026-01-19 09:58 - 人员分组管理 API 开发

**概述**：完成人员分组管理 API 的完整实现，支持分组的增删改查、报警状态管理、人员统计等功能

**详细内容**：

1. **分组管理 Schemas 创建**
   - 创建 `app/schemas/group.py` 定义分组相关数据模型
   - `GroupCreate` - 创建分组请求（名称、描述、颜色、报警开关、优先级、排序）
   - `GroupUpdate` - 更新分组请求
   - `GroupResponse` - 分组详情响应（含人员数量）
   - `GroupSimpleResponse` - 简化响应（用于下拉选择）
   - `GroupListResponse` - 列表响应（含分页信息）
   - `GroupStatsResponse` - 统计响应

2. **分组管理 API 实现** (`app/api/v1/groups.py`)
   - `GET /api/v1/person-groups` - 获取分组列表（支持分页、关键词搜索、报警状态筛选）
   - `GET /api/v1/person-groups/all` - 获取所有分组（简化列表，用于下拉选择）
   - `GET /api/v1/person-groups/stats` - 获取分组统计信息（含人员数量）
   - `POST /api/v1/person-groups` - 创建新分组（验证名称唯一性）
   - `GET /api/v1/person-groups/{group_id}` - 获取分组详情
   - `PUT /api/v1/person-groups/{group_id}` - 更新分组信息
   - `DELETE /api/v1/person-groups/{group_id}` - 删除分组（支持 force 强制删除）
   - `PATCH /api/v1/person-groups/{group_id}/alert` - 切换报警状态

3. **特色功能**
   - 分组响应自动包含关联人员数量
   - 支持十六进制颜色和颜色名称验证（#RRGGBB、red、blue 等）
   - 删除分组时检查关联人员，支持强制删除模式
   - 独立的报警状态切换接口

4. **API 测试验证**
   - ✅ 获取已有分组（4 个默认分组：Employee、Visitor、VIP、Blacklist）
   - ✅ 获取分组列表（含分页）
   - ✅ 获取分组统计
   - ✅ 创建新分组（Contractor）
   - ✅ 更新分组信息
   - ✅ 切换报警状态
   - ✅ 关键词搜索、报警状态筛选

---

### 2026-01-19 09:50 - 摄像头管理 API 开发

**概述**：完成摄像头管理 API 的完整实现，支持 RTSP 配置、状态管理、连通性测试等功能

**详细内容**：

1. **摄像头管理 Schemas 创建**
   - 创建 `app/schemas/camera.py` 定义摄像头相关数据模型
   - `CameraCreate` - 创建摄像头请求（名称、区域、RTSP地址、认证信息、分辨率、帧率）
   - `CameraUpdate` - 更新摄像头请求
   - `CameraToggleRequest` - 切换启用状态请求
   - `CameraResponse` - 摄像头详情响应（含关联区域信息）
   - `CameraSimpleResponse` - 简化响应（用于下拉选择）
   - `CameraListResponse` - 列表响应（含分页信息）
   - `CameraStatusResponse/CameraStatusListResponse` - 状态响应（含统计）
   - `CameraTestResult` - 连通性测试结果

2. **摄像头管理 API 实现** (`app/api/v1/cameras.py`)
   - `GET /api/v1/cameras` - 获取摄像头列表（支持分页、关键词搜索、区域/状态/启用筛选）
   - `GET /api/v1/cameras/all` - 获取所有摄像头（简化列表，用于下拉选择）
   - `GET /api/v1/cameras/status` - 获取所有摄像头状态（含在线/离线/错误统计）
   - `POST /api/v1/cameras` - 创建新摄像头（验证名称唯一性、区域存在性）
   - `GET /api/v1/cameras/{camera_id}` - 获取摄像头详情（含关联区域）
   - `PUT /api/v1/cameras/{camera_id}` - 更新摄像头配置
   - `DELETE /api/v1/cameras/{camera_id}` - 删除摄像头
   - `POST /api/v1/cameras/{camera_id}/test` - 测试 RTSP 连通性（使用 OpenCV）
   - `PATCH /api/v1/cameras/{camera_id}/toggle` - 启用/停用摄像头分析
   - `PATCH /api/v1/cameras/{camera_id}/status` - 更新摄像头状态（内部接口）

3. **特色功能**
   - 摄像头响应自动包含关联区域详细信息
   - 支持 JSON 格式的扩展配置（ROI、灵敏度等）
   - RTSP 连通性测试自动检测分辨率和帧率
   - 状态接口提供在线/离线/错误数量统计
   - 分辨率格式验证（WIDTHxHEIGHT）

4. **API 测试验证**
   - ✅ 创建摄像头（3 个：Entrance Cam 1、Lobby Cam 1、Parking Cam 1）
   - ✅ 获取摄像头列表（分页）
   - ✅ 获取所有摄像头（简化列表）
   - ✅ 获取摄像头状态（含统计）
   - ✅ 按区域筛选、关键词搜索
   - ✅ 更新摄像头配置（添加 ROI 配置）
   - ✅ 启用/禁用摄像头
   - ✅ 测试 RTSP 连通性

---

### 2026-01-19 09:44 - 摄像头区域管理 API 开发

**概述**：完成摄像头区域管理 API 的完整实现，支持区域的增删改查、树形结构展示、楼栋/楼层筛选

**详细内容**：

1. **区域管理 Schemas 创建**
   - 创建 `app/schemas/zone.py` 定义区域相关数据模型
   - `ZoneCreate` - 创建区域请求（名称、描述、楼栋、楼层、排序）
   - `ZoneUpdate` - 更新区域请求
   - `ZoneResponse` - 区域详情响应（含摄像头数量）
   - `ZoneSimpleResponse` - 简化响应（用于下拉选择）
   - `ZoneListResponse` - 列表响应（含分页信息）
   - `ZoneTreeNode/ZoneTreeResponse` - 树形结构响应

2. **区域管理 API 实现** (`app/api/v1/zones.py`)
   - `GET /api/v1/zones` - 获取区域列表（支持分页、关键词搜索、楼栋/楼层筛选）
   - `GET /api/v1/zones/all` - 获取所有区域（简化列表，用于下拉选择）
   - `GET /api/v1/zones/tree` - 获取区域树（按楼栋-楼层分组）
   - `GET /api/v1/zones/buildings` - 获取楼栋列表
   - `GET /api/v1/zones/floors` - 获取楼层列表（支持楼栋筛选）
   - `POST /api/v1/zones` - 创建新区域（验证同楼栋楼层下名称唯一性）
   - `GET /api/v1/zones/{zone_id}` - 获取区域详情
   - `PUT /api/v1/zones/{zone_id}` - 更新区域信息
   - `DELETE /api/v1/zones/{zone_id}` - 删除区域（支持 force 强制删除）

3. **特色功能**
   - 区域响应自动包含关联摄像头数量（camera_count）
   - 区域树支持按楼栋-楼层两级分组展示
   - 删除区域时检查关联摄像头，支持强制删除模式
   - 创建/更新时验证同一楼栋楼层下名称不重复

4. **API 测试验证**
   - ✅ 创建区域（A Building/1F、B Building/2F）
   - ✅ 获取区域列表（分页）
   - ✅ 获取所有区域（简化列表）
   - ✅ 获取区域树（按楼栋分组）
   - ✅ 获取楼栋/楼层列表
   - ✅ 按楼栋筛选、关键词搜索
   - ✅ 更新区域信息
   - ✅ 删除区域

---

### 2026-01-19 09:39 - 用户管理 API 开发

**概述**：完成用户管理 API 的完整实现，包括增删改查、状态管理、密码重置等功能

**详细内容**：

1. **用户管理 Schemas 创建**
   - 创建 `app/schemas/user.py` 定义用户相关数据模型
   - `UserCreate` - 创建用户请求（用户名、密码、邮箱、手机、角色）
   - `UserUpdate` - 更新用户请求（邮箱、手机、角色）
   - `UserStatusUpdate` - 用户状态更新（启用/禁用）
   - `ResetPasswordRequest` - 密码重置请求
   - `UserDetailResponse` - 用户详情响应（含时间戳）
   - `UserListResponse` - 用户列表响应（含分页信息）

2. **用户管理 API 实现** (`app/api/v1/users.py`)
   - `GET /api/v1/users` - 获取用户列表（支持分页、关键词搜索、角色筛选、状态筛选）
   - `POST /api/v1/users` - 创建新用户（验证用户名唯一性）
   - `GET /api/v1/users/{user_id}` - 获取用户详情
   - `PUT /api/v1/users/{user_id}` - 更新用户信息（禁止修改自己的角色）
   - `PATCH /api/v1/users/{user_id}/status` - 启用/禁用用户（禁止禁用自己）
   - `POST /api/v1/users/{user_id}/reset-password` - 重置用户密码
   - `DELETE /api/v1/users/{user_id}` - 删除用户（禁止删除自己）

3. **权限控制**
   - 所有用户管理接口仅管理员可访问（使用 `require_admin` 依赖）
   - 安全限制：不能修改自己的角色、不能禁用自己、不能删除自己

4. **API 测试验证**
   - ✅ 用户列表查询（分页、筛选）
   - ✅ 创建用户（operator1）
   - ✅ 获取用户详情
   - ✅ 更新用户信息（手机号）
   - ✅ 禁用/启用用户
   - ✅ 重置用户密码

---

### 2026-01-18 16:47 - 阶段二：数据库迁移与认证 API

**概述**：完成数据库迁移、初始数据创建、JWT 认证 API 实现

**详细内容**：

1. **数据库迁移**
   - 配置 Alembic 异步迁移环境
   - 创建初始迁移脚本，生成 10 个数据表
   - 执行迁移：users、cameras、camera_zones、known_persons、person_groups、face_images、alert_logs、system_configs、operation_logs、cleanup_logs

2. **初始数据创建**
   - 创建 `scripts/init_db.py` 初始化脚本
   - 创建默认管理员账户：admin / admin123
   - 创建默认系统配置（人脸阈值、报警冷却、数据保留等）
   - 创建默认人员分组（Employee、Visitor、VIP、Blacklist）

3. **JWT 认证 API 实现**
   - `POST /api/v1/auth/login` - 用户登录，返回 access_token 和 refresh_token
   - `POST /api/v1/auth/logout` - 用户登出
   - `POST /api/v1/auth/refresh` - 刷新 Token
   - `GET /api/v1/auth/me` - 获取当前用户信息
   - `PUT /api/v1/auth/password` - 修改密码

4. **代码文件创建/修改**
   - `app/schemas/auth.py` - 认证相关 Pydantic 模型
   - `app/schemas/common.py` - 通用响应模型
   - `app/api/deps.py` - API 依赖注入（数据库会话、当前用户、权限验证）
   - `app/api/v1/auth.py` - 认证 API 路由
   - `app/core/security.py` - 完善 JWT 生成/验证、bcrypt 密码加密

5. **问题修复**
   - 修复 .env 文件 UTF-8 编码问题
   - 修复 main.py emoji 字符 Windows 控制台编码问题
   - 修复 alert_logs 表 `metadata` 字段命名冲突（改为 `extra_data`）
   - 修复 bcrypt/passlib 兼容性问题（直接使用 bcrypt）

---

### 2026-01-18 04:50 - 阶段一：项目基础设施搭建

**概述**：完成项目目录结构创建、Python 虚拟环境配置、后端依赖安装

**详细内容**：

1. **创建完整项目目录结构**（68 个文件）
   - 后端：`backend/app/` 下创建 api、core、models、schemas、services、engine、websocket、tasks、utils 等模块
   - 前端：`frontend/src/` 下创建 api、components、views、stores、router、composables、utils 等目录
   - 数据：`data/captures/`（报警截图）、`data/faces/`（人脸库）
   - 其他：`logs/`（日志）、`docs/`（文档）

2. **后端代码框架**
   - 创建 9 个 API 路由模块：auth、users、cameras、zones、persons、groups、alerts、settings、logs
   - 创建 5 个数据库模型：user、camera、person、alert、system
   - 创建核心配置：config.py、security.py、database.py
   - 创建 WebSocket 管理器和处理器
   - 创建 Alembic 迁移配置

3. **前端代码框架**
   - 创建 12 个页面组件：login、dashboard、monitor、alerts、persons、cameras、settings、users、logs、zones、groups、profile
   - 创建布局组件：MainLayout、AlertCard、NotificationFeed
   - 创建状态管理：auth、alert、camera stores
   - 创建工具函数和 WebSocket composable

4. **环境配置**
   - 配置 Python 3.14.0 虚拟环境 (`backend/venv/`)
   - 安装 58 个后端依赖包（FastAPI 0.128.0、SQLAlchemy 2.0.45、asyncpg 0.31.0 等）
   - 创建 `.gitignore`、`README.md`、`.env.example`
   - 配置 `.env` 文件（数据库连接、JWT 密钥等）
   - 创建 `video_warning` 数据库

5. **环境检查通过**
   - Python 3.14.0 ✅
   - Node.js 24.9.0 ✅
   - PostgreSQL 17.5 ✅

---

### 2026-01-17 - 完善开发计划细节

**概述**：细化数据库设计、补充 API 接口、前端页面、安全考量

**详细内容**：

1. **数据库模型设计扩展**
   - 新增表：camera_zones（区域）、person_groups（人员分组）、face_images（人脸图片）、operation_logs（操作日志）、cleanup_logs（清理日志）
   - 细化字段：为每个表添加完整字段定义、类型、索引设计
   - 预留 pgvector 扩展支持

2. **API 接口补充**
   - 新增用户管理模块（管理员功能）
   - 新增摄像头区域管理模块
   - 新增人员分组管理模块
   - 新增操作日志查询模块
   - 为每个接口添加 HTTP 方法和路径

3. **前端页面补充**
   - 新增页面：用户管理、区域管理、人员分组、操作日志、个人中心
   - 细化监控页：宫格布局切换、全屏模式
   - 细化报警通知：折叠/展开、未读徽标、声音开关

4. **新增章节**
   - 🔐 安全考量：敏感数据保护、访问控制、前端安全
   - 更新风险提示：增加内存泄漏、并发控制

5. **更新工时估算**：20-29 天

---

### 2026-01-16 - 初始化项目

**概述**：基于 Requirements.md V2.0 制定开发计划

**详细内容**：

1. **创建 todo.md 开发待办清单**
   - 定义 8 个开发阶段
   - 规划技术栈：FastAPI + Vue 3 + PostgreSQL
   - 制定初步工时估算

2. **需求文档 Requirements.md**
   - PostgreSQL 选型理由
   - 前端架构设计（Shadcn-vue + TailwindCSS）
   - 存储策略、性能优化、扩展性设计

---

## 🔐 安全考量

### 敏感数据保护
- [ ] 用户密码使用 bcrypt 加密存储
- [ ] RTSP 密码使用 AES 加密存储
- [ ] JWT Secret 使用强随机字符串
- [ ] 敏感配置通过环境变量注入

### 访问控制
- [ ] JWT Token 过期时间配置（Access: 30分钟，Refresh: 7天）
- [ ] 基于角色的权限控制 (RBAC)
- [ ] API 限流防止暴力破解
- [ ] 操作日志审计追踪

### 前端安全
- [ ] XSS 防护（输入过滤、输出转义）
- [ ] CSRF Token（如使用 Cookie）
- [ ] 敏感操作二次确认

---

## ⚠️ 风险提示

1. **性能瓶颈**：人脸识别为 CPU/GPU 密集型操作，需严格采用多进程架构
2. **存储空间**：截图数据量大，务必实现定期清理机制
3. **断流重连**：RTSP 流不稳定，必须实现健壮的重连逻辑
4. **前端实时性**：WebSocket 需做好心跳检测和断线重连
5. **内存泄漏**：长时间运行需注意视频帧队列、WebSocket 连接的内存管理
6. **并发控制**：多摄像头同时报警时的数据库写入与推送压力

---

## 🚀 下一步行动

待确认后，建议按以下顺序开始开发：

| 阶段 | 内容 | 预计工时 |
|------|------|---------|
| 阶段一 | 项目基础设施搭建（目录结构、环境配置、框架初始化） | 1-2 天 |
| 阶段二 | 数据库设计与基础 API（模型、迁移、核心接口） | 3-4 天 |
| 阶段三 | 视频流处理核心引擎（采集、识别、管道架构） | 4-5 天 |
| 阶段四 | 报警与通知系统（触发、推送、去重） | 2-3 天 |
| 阶段五 | 存储策略实现（截图存储、清理机制） | 1-2 天 |
| 阶段六 | 前端界面开发（全部页面 + 组件） | 6-8 天 |
| 阶段七 | 测试与优化（功能、安全、性能） | 2-3 天 |
| 阶段八 | 部署与文档 | 1-2 天 |
| **合计** | | **20-29 天** |

**请确认此待办清单是否符合您的预期，我将根据您的反馈进行调整后开始开发。**
