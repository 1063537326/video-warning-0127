# 警告列表侧边栏改造 + 监控页图片修复

## 概述

解决两个问题：
1. 实时监控页面的告警图片不显示
2. 右上角报警通知改造为"警告列表"，数据从后端 API 按天加载，分页滚动

---

## 问题 1：图片不显示修复

### 根因

`MonitorView.vue` 和 `stores/websocket.ts` 中的图片解析逻辑有两个 bug：

1. 只处理了 `face_image`，没有 fallback 到 `body_image`（大部分追踪事件只有 body 截图）
2. URL 路径（`/static/captures/...`）被错误地套了 base64 前缀

### 方案

新增 `resolveImageSrc()` 工具函数：

```
输入 → 判断逻辑 → 输出
--------------------------------------
null/空         → ''
'data:...'      → 原样返回
'/static/...'   → 原样返回（URL 路径）
'iVBORw0K...'   → 'data:image/jpeg;base64,' + 输入
```

优先级：`face_image` > `body_image` > `full_image` > 空

### 影响文件

- `frontend/src/utils/image.ts`（新建）
- `frontend/src/views/monitor/MonitorView.vue`
- `frontend/src/stores/websocket.ts`

---

## 问题 2：警告列表侧边栏

### 数据流

```
打开侧边栏
  → GET /api/v1/alerts?date=today&page=1&page_size=25
  → 渲染列表（最新在最上面）

滚动到底部
  → 加载下一页

WebSocket 推送新报警
  → 实时插入列表顶部（去重）

零点跨天
  → setTimeout 精确触发
  → 标记 needsRefresh = true
  → 下次打开时重新拉取新一天数据
```

### UI 变更

| 现在 | 改为 |
|------|------|
| 标题「实时报警」 | 「警告列表」 |
| 数据来源：纯 WebSocket 内存 | 后端 API + WebSocket 实时补充 |
| 刷新即丢失 | 持久化，按天查看 |
| 底部：点击卡片查看详情 · 最多显示最近 100 条 | `2026-04-23 · 共 XX 条` |

### 分页配置

```ts
/** ===== 分页配置（可调整）===== */
const PAGE_SIZE = 25  // 每页加载条数
```

### 零点刷新

```ts
// 计算距离零点的精确毫秒数，设置一次性 setTimeout
const now = new Date()
const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1)
setTimeout(resetToNewDay, midnight.getTime() - now.getTime())
```

### 影响文件

- `frontend/src/stores/alert.ts` — 新增 API 加载、分页状态、跨天逻辑
- `frontend/src/components/business/NotificationFeed.vue` — UI 改造
- 后端 API 不需要改动（`GET /api/v1/alerts` 已支持日期过滤和分页）

---

## 验证

- [ ] 监控页告警图片正常显示（face/body/full 三种来源）
- [ ] 打开侧边栏加载当天数据
- [ ] 滚动到底部自动加载下一页
- [ ] WebSocket 新报警实时插入顶部
- [ ] 跨零点后显示新一天数据
- [ ] 标题显示"警告列表"
