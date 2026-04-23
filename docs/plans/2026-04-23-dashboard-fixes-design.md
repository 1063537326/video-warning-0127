# 仪表盘 Bug 修复 + 报警管理分页 + 人员头像方案

## 概述

本文档覆盖 5 个任务的排查结论和修复方案。

---

## 任务 1：仪表盘摄像头显示 0/0

### 根因

**双重字段不匹配**：

| 层级 | 问题 |
|------|------|
| 数据获取 | `cameraStats.value = cameraRes.stats` — 后端返回的是**顶级对象**，没有 `.stats` 嵌套 |
| 字段映射 | 模板用 `cameraStats?.online`，后端字段名是 `online_count` |

后端 `GET /cameras/status` 返回：

```json
{
  "items": [...],
  "online_count": 1,
  "offline_count": 0,
  "error_count": 0,
  "total": 1
}
```

### 修复

#### [MODIFY] [DashboardView.vue](file:///d:/MX_Projects/works/video-warning-0127/frontend/src/views/dashboard/DashboardView.vue)

1. **第 63 行**：`cameraStats.value = cameraRes.stats` → `cameraStats.value = cameraRes`
2. **第 361 行**：`cameraStats?.online` → `cameraStats?.online_count`
3. **第 361 行**：`cameraStats?.total` → `cameraStats?.total`（这个不用改）

同时更新 `CameraStatusStats` 类型定义，使字段名与后端一致。

#### [MODIFY] [types/index.ts](file:///d:/MX_Projects/works/video-warning-0127/frontend/src/types/index.ts)

```diff
 export interface CameraStatusStats {
-  online: number
-  offline: number
-  error: number
+  online_count: number
+  offline_count: number
+  error_count: number
   total: number
 }
```

---

## 任务 2：报警趋势图空白

### 根因

**前后端字段名不匹配**：

| 前端期望 | 后端实际返回 |
|----------|--------------|
| `item.stranger` | `item.stranger_count` |
| `item.known` | `item.known_count` |
| `item.blacklist` | `item.blacklist_count` |

前端发送 `period='7d'`，后端接受 `day/week/month`。但因为后端 `else` 分支默认走 `week`（7天），所以 period 参数本身不是空数据的原因。空数据的原因是**字段名对不上**，`item.stranger` 全是 `undefined`，被 `|| 0` 替换成 0，导致图表全是 0。

### 修复

#### [MODIFY] [DashboardView.vue](file:///d:/MX_Projects/works/video-warning-0127/frontend/src/views/dashboard/DashboardView.vue)

1. **第 46 行** period 映射：`'7d'` → `'week'`，`'30d'` → `'month'`，`'90d'` 暂映射为 `'month'`（后端不支持 90d）
2. **第 121-124 行** 字段映射：

```diff
-  const strangerData = trendData.value.map(item => item.stranger || 0)
-  const knownData = trendData.value.map(item => item.known || 0)
-  const blacklistData = trendData.value.map(item => item.blacklist || 0)
+  const strangerData = trendData.value.map(item => item.stranger_count || 0)
+  const knownData = trendData.value.map(item => item.known_count || 0)
+  const blacklistData = trendData.value.map(item => item.blacklist_count || 0)
```

3. 需要在 `loadTrendData` 和 UI 中做 period 值的映射转换。

---

## 任务 3：仪表盘其他隐藏问题

排查结论：

- ✅ 报警统计卡片（待处理、今日报警、已知人员）：字段正确
- ✅ 系统状态卡片（运行时间、数据库、磁盘、CPU、内存）：字段正确
- ✅ 报警类型分布饼图：字段正确（`by_type.stranger` 等）
- ⚠️ 快捷入口路由名对齐：确认 router 定义中 name 一致（已正确）
- ⚠️ 饼图空数据：当 `alertStats.total === 0` 时饼图显示空白区域，无提示文字 → 小优化

### 修复

在饼图区域添加空数据状态判断：当 `alertStats.total === 0` 时显示"暂无数据"。

---

## 任务 4：报警管理每页改 20 条

### 修复

#### [MODIFY] [AlertsView.vue](file:///d:/MX_Projects/works/video-warning-0127/frontend/src/views/alerts/AlertsView.vue)

```diff
 const pagination = reactive({
   page: 1,
-  pageSize: 10,
+  pageSize: 20,
   total: 0,
   totalPages: 0
 })
```

一行改动。

---

## 任务 5：人员头像为空 — 排查结论

### B 方案排查结果

| 检查项 | 结果 |
|--------|------|
| `face_images` 表数据 | **0 行** — 完全没有记录 |
| `known_persons` 表数据 | 3 个人存在 |
| 后端 `build_person_response` 逻辑 | 正确 — 遍历 `face_images` 找 `is_primary` 或第一张 |
| 前端 `person.primary_face?.image_url` | 正确 — 用 `getStaticUrl()` 拼接 |

> [!IMPORTANT]
> **结论：问题不在代码逻辑，而是数据库中根本没有 face_images 记录。**
> 
> 人员可能是通过系统外部（如直接操作 CompreFace）注册的，或者导入时没有同步上传人脸图片。
> 本地 `face_images` 表为空，所以 `primary_face` 永远是 `null`。

### 推荐方案

需要从 CompreFace 同步人脸照片到本地系统。提供以下 3 种方案：

#### 方案 A：一次性同步脚本（推荐 ✅）

写一个后端管理命令/API，遍历 CompreFace 中所有 subject，下载其人脸图片，保存到本地 `data/faces/`，并在 `face_images` 表中创建记录。

- **优点**：一次性解决，不改变现有工作流
- **缺点**：只是初始化，后续新增需要手动同步
- **CompreFace API**：`GET /api/v1/recognition/faces?subject={name}` 获取人脸列表，`GET /api/v1/recognition/faces/{image_id}/img` 下载图片

#### 方案 B：双写机制

修改人员创建/上传流程，同时写本地 `face_images` 表和 CompreFace。现有代码已经部分实现（`upload_face_image` 函数已有双写逻辑），但数据库中为空说明之前没有通过这个接口上传过。

- **优点**：从此往后自动同步
- **缺点**：不解决历史数据

#### 方案 C：A + B 结合（最完善 ✅✅）

1. 先用一次性脚本同步 CompreFace 现有数据
2. 确保后续通过系统上传人脸时双写正常工作

### 头像选择策略

当一个人有多张照片时，选择"最具代表性"的方案：

| 策略 | 方法 | 复杂度 |
|------|------|--------|
| **第一张** | 直接取 CompreFace 返回的第一张 | ⭐ |
| **质量评分最高** | CompreFace 不返回质量分，需要额外调 detect API 获取 `box.probability` | ⭐⭐ |
| **自动设为主图** | 同步时第一张自动 `is_primary=True`，用户可在系统中手动切换 | ⭐（推荐） |

---

## 验证计划

### 自动验证
- TypeScript 编译无错误
- 浏览器访问仪表盘，摄像头显示 1/1，趋势图有数据

### 手动验证
- 报警管理页面确认每页 20 条
- 人员管理页面确认头像显示
