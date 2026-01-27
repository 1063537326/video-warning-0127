/**
 * 视频监控报警系统 - 类型定义
 */

// ============ 通用类型 ============

/** 分页响应 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/** API 错误响应 */
export interface ApiError {
  detail: string
  status_code?: number
}

// ============ 用户相关 ============

/** 用户角色 */
export type UserRole = 'admin' | 'operator'

/** 用户信息 */
export interface User {
  id: number
  username: string
  email?: string
  phone?: string
  role: UserRole
  is_active: boolean
  last_login_at?: string
  created_at: string
  updated_at: string
}

/** 登录请求 */
export interface LoginRequest {
  username: string
  password: string
}

/** Token 响应 */
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// ============ 摄像头相关 ============

/** 摄像头状态 */
export type CameraStatus = 'online' | 'offline' | 'error'

/** 摄像头区域 */
export interface Zone {
  id: number
  name: string
  description?: string
  building?: string
  floor?: string
  sort_order: number
  camera_count: number
  created_at: string
  updated_at: string
}

/** 摄像头 */
export interface Camera {
  id: number
  name: string
  zone_id?: number
  zone?: ZoneSimple
  rtsp_url: string
  rtsp_username?: string
  rtsp_password?: string
  resolution?: string
  fps?: number
  status: CameraStatus
  is_analyzing: boolean
  config?: Record<string, any>
  last_seen_at?: string
  created_at: string
  updated_at: string
}

/** 简化区域 */
export interface ZoneSimple {
  id: number
  name: string
}

/** 摄像头状态统计 */
export interface CameraStatusStats {
  online: number
  offline: number
  error: number
  total: number
}

// ============ 人员相关 ============

/** 人员状态 */
export type PersonStatus = 'active' | 'inactive'

/** 人员分组 */
export interface PersonGroup {
  id: number
  name: string
  description?: string
  color?: string
  alert_enabled: boolean
  alert_priority: number
  sort_order: number
  person_count: number
  created_at: string
  updated_at: string
}

/** 人脸图片 */
export interface FaceImage {
  id: number
  person_id?: number
  image_path: string
  image_url?: string
  quality_score?: number
  is_primary: boolean
  created_at: string
}

/** 已知人员 */
export interface Person {
  id: number
  name: string
  employee_id?: string
  group_id?: number
  group?: GroupSimple
  department?: string
  phone?: string
  is_active: boolean
  remark?: string
  face_count: number
  primary_face?: {
    id: number
    image_url?: string
  }
  created_at: string
  updated_at: string
}

/** 简化分组 */
export interface GroupSimple {
  id: number
  name: string
  color?: string
}

// ============ 报警相关 ============

/** 报警类型 */
export type AlertType = 'stranger' | 'known' | 'blacklist'

/** 报警状态 */
export type AlertStatus = 'pending' | 'processed' | 'ignored'

/** 报警级别 */
export type AlertLevel = 'info' | 'warning' | 'critical'

/** 报警记录 */
export interface Alert {
  id: number
  camera_id: number
  camera?: CameraSimple
  alert_type: AlertType
  person_id?: number
  person?: PersonSimple
  confidence?: number
  face_image_path?: string
  face_image_url?: string
  full_image_path?: string
  full_image_url?: string
  body_image_path?: string
  body_image_url?: string
  face_bbox?: { x: number; y: number; w: number; h: number }
  status: AlertStatus
  processed_by?: number
  processor?: UserSimple
  processed_at?: string
  process_remark?: string
  extra_data?: Record<string, any>
  track_id?: string
  alert_level?: AlertLevel
  best_body_image_path?: string
  image_history?: any[]
  is_reviewed?: boolean
  created_at: string
}

/** 简化摄像头 */
export interface CameraSimple {
  id: number
  name: string
  zone_id?: number
  zone_name?: string
}

/** 简化人员 */
export interface PersonSimple {
  id: number
  name: string
  employee_id?: string
  group_id?: number
  group_name?: string
  group_color?: string
}

/** 简化用户 */
export interface UserSimple {
  id: number
  username: string
}

/** 报警统计 */
export interface AlertStatistics {
  total: number
  pending: number
  processed: number
  ignored: number
  by_type: Record<string, number>
  by_camera: Array<{ camera_id: number; camera_name: string; count: number }>
  today_count: number
  week_count: number
  month_count: number
}

// ============ 系统配置相关 ============

/** 配置项 */
export interface ConfigItem {
  id: number
  config_key: string
  config_value?: string
  value_type: string
  description?: string
  updated_at: string
  updated_by?: number
}

/** 配置分组 */
export interface ConfigGroup {
  group_name: string
  group_label: string
  items: ConfigItem[]
}

/** 磁盘使用 */
export interface DiskUsage {
  path: string
  total_bytes: number
  used_bytes: number
  free_bytes: number
  usage_percent: number
  total_formatted: string
  used_formatted: string
  free_formatted: string
}

/** 数据库状态 */
export interface DatabaseStatus {
  connected: boolean
  version?: string
  tables_count: number
  total_records: Record<string, number>
}

/** 系统状态 */
export interface SystemStatus {
  app_name: string
  app_version: string
  environment: string
  uptime_seconds: number
  uptime_formatted: string
  current_time: string
  disk_usage: DiskUsage[]
  database: DatabaseStatus
  services: Array<{ name: string; status: string; uptime_formatted?: string }>
  system_info: Record<string, any>
}

// ============ 操作日志相关 ============

/** 操作日志 */
export interface OperationLog {
  id: number
  user_id?: number
  user?: UserSimple
  action: string
  action_label: string
  target_type?: string
  target_type_label: string
  target_id?: number
  details?: Record<string, any>
  ip_address?: string
  user_agent?: string
  created_at: string
}

/** 操作日志统计 */
export interface LogStatistics {
  total: number
  by_action: Record<string, number>
  by_target_type: Record<string, number>
  by_user: Array<{ user_id: number; username: string; count: number }>
  today_count: number
  week_count: number
}

// ============ WebSocket 相关 ============

/** WebSocket 消息类型 */
export type WsMessageType =
  | 'connect'       // 连接成功
  | 'disconnect'    // 断开连接
  | 'heartbeat'     // 心跳
  | 'pong'          // 心跳响应
  | 'error'         // 错误
  | 'alert'         // 报警
  | 'camera_status' // 摄像头状态
  | 'notification'  // 系统通知
  | 'engine_status' // 引擎状态

/** WebSocket 消息 */
export interface WsMessage<T = any> {
  type: WsMessageType
  data: T
  timestamp?: string
}

/** WebSocket 报警数据 */
export interface WsAlertData {
  id?: number
  alert_id?: number        // 报警 ID
  camera_id: number
  camera_name: string
  zone_name?: string
  alert_type: AlertType
  person_id?: number
  person_name?: string
  group_name?: string
  confidence: number
  similarity?: number      // 相似度
  face_image?: string      // base64 编码的人脸图片
  full_image?: string      // base64 编码的全图
  track_id?: string
  alert_level?: AlertLevel
  body_image?: string      // base64 编码的全身图片

  timestamp: string
}

/** WebSocket 摄像头状态数据 */
export interface WsCameraStatusData {
  camera_id: number
  camera_name: string
  status: 'online' | 'offline' | 'error' | 'connecting'
  fps?: number
  queue_size?: number
  total_frames?: number
  processed_frames?: number
  message?: string
}

/** WebSocket 引擎状态数据 */
export interface WsEngineStatusData {
  status: 'stopped' | 'starting' | 'running' | 'stopping' | 'error'
  camera_count: number
  running_camera_count: number
  message?: string
}

// ============ 引擎相关 ============

/** 引擎状态枚举 */
export type EngineStatus = 'stopped' | 'starting' | 'running' | 'stopping' | 'error' | 'unavailable'

/** 引擎统计信息 */
export interface EngineStats {
  status: EngineStatus
  camera_count: number
  running_camera_count: number
  message?: string
  recognizer?: {
    is_loaded: boolean
    database: {
      person_count: number
      embedding_count: number
      similarity_threshold: number
    }
    config: {
      similarity_threshold: number
      alert_on_stranger: boolean
      alert_cooldown: number
    }
  }
}

/** 引擎摄像头状态 */
export interface EngineCameraStatus {
  camera_id: number
  camera_name: string
  status: string
  fps: number
  queue_size: number
  total_frames: number
  processed_frames: number
  last_frame_time?: string
}
