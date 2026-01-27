/**
 * API 请求封装
 * 
 * 提供与后端 API 的通信方法。
 */
import axios, { type AxiosError, type AxiosResponse } from 'axios'
import type {
  LoginRequest,
  TokenResponse,
  User,
  Camera,
  Zone,
  Person,
  PersonGroup,
  FaceImage,
  Alert,
  AlertStatistics,
  ConfigGroup,
  SystemStatus,
  OperationLog,
  LogStatistics,
  PaginatedResponse,
  CameraStatusStats,
} from '@/types'

// 创建 axios 实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:329/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token 过期或无效，清除本地存储并跳转登录
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ============ 认证 API ============

export const authApi = {
  /** 登录 */
  login: (data: LoginRequest): Promise<TokenResponse> =>
    api.post('/auth/login', data),

  /** 登出 */
  logout: (): Promise<void> =>
    api.post('/auth/logout'),

  /** 获取当前用户 */
  getCurrentUser: (): Promise<User> =>
    api.get('/auth/me'),

  /** 刷新 Token */
  refreshToken: (refreshToken: string): Promise<TokenResponse> =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),

  /** 修改密码 */
  changePassword: (oldPassword: string, newPassword: string): Promise<void> =>
    api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
}

// ============ 用户管理 API ============

export const userApi = {
  /** 获取用户列表 */
  getList: (params?: { page?: number; page_size?: number; keyword?: string; role?: string; is_active?: boolean }): Promise<PaginatedResponse<User>> =>
    api.get('/users', { params }),

  /** 创建用户 */
  create: (data: { username: string; password: string; email?: string; phone?: string; role?: string }): Promise<User> =>
    api.post('/users', data),

  /** 获取用户详情 */
  get: (id: number): Promise<User> =>
    api.get(`/users/${id}`),

  /** 更新用户 */
  update: (id: number, data: Partial<User>): Promise<User> =>
    api.put(`/users/${id}`, data),

  /** 删除用户 */
  delete: (id: number): Promise<void> =>
    api.delete(`/users/${id}`),

  /** 切换用户状态 */
  toggleStatus: (id: number, isActive: boolean): Promise<User> =>
    api.patch(`/users/${id}/status`, { is_active: isActive }),

  /** 重置密码 */
  resetPassword: (id: number, newPassword: string): Promise<void> =>
    api.post(`/users/${id}/reset-password`, { new_password: newPassword }),
}

// ============ 区域管理 API ============

export const zoneApi = {
  /** 获取区域列表 */
  getList: (params?: { page?: number; page_size?: number; keyword?: string; building?: string }): Promise<PaginatedResponse<Zone>> =>
    api.get('/zones', { params }),

  /** 获取所有区域 */
  getAll: (): Promise<{ items: Zone[] }> =>
    api.get('/zones/all'),

  /** 创建区域 */
  create: (data: { name: string; description?: string; building?: string; floor?: string; sort_order?: number }): Promise<Zone> =>
    api.post('/zones', data),

  /** 获取区域详情 */
  get: (id: number): Promise<Zone> =>
    api.get(`/zones/${id}`),

  /** 更新区域 */
  update: (id: number, data: Partial<Zone>): Promise<Zone> =>
    api.put(`/zones/${id}`, data),

  /** 删除区域 */
  delete: (id: number): Promise<void> =>
    api.delete(`/zones/${id}`),
}

// ============ 摄像头管理 API ============

export const cameraApi = {
  /** 获取摄像头列表 */
  getList: (params?: { page?: number; page_size?: number; keyword?: string; zone_id?: number }): Promise<PaginatedResponse<Camera>> =>
    api.get('/cameras', { params }),

  /** 获取所有摄像头 */
  getAll: (): Promise<{ items: Camera[] }> =>
    api.get('/cameras/all'),

  /** 获取摄像头状态 */
  getStatus: (): Promise<{ items: Camera[]; stats: CameraStatusStats }> =>
    api.get('/cameras/status'),

  /** 创建摄像头 */
  create: (data: { name: string; zone_id?: number; rtsp_url: string; rtsp_username?: string; rtsp_password?: string; resolution?: string; fps?: number; config?: Record<string, any> }): Promise<Camera> =>
    api.post('/cameras', data),

  /** 获取摄像头详情 */
  get: (id: number): Promise<Camera> =>
    api.get(`/cameras/${id}`),

  /** 更新摄像头 */
  update: (id: number, data: Partial<Camera>): Promise<Camera> =>
    api.put(`/cameras/${id}`, data),

  /** 删除摄像头 */
  delete: (id: number): Promise<void> =>
    api.delete(`/cameras/${id}`),

  /** 测试连接 */
  test: (id: number): Promise<{ success: boolean; message: string; response_time_ms?: number; resolution_detected?: string; fps_detected?: number }> =>
    api.post(`/cameras/${id}/test`),

  /** 切换分析状态 */
  toggle: (id: number, isEnabled: boolean): Promise<Camera> =>
    api.patch(`/cameras/${id}/toggle`, { is_enabled: isEnabled }),

  /**
   * 启动摄像头分析
   * 
   * 将摄像头添加到视频分析引擎
   */
  startAnalysis: (id: number): Promise<{ success: boolean; message: string; camera_id: number }> =>
    api.post(`/cameras/${id}/start-analysis`),

  /**
   * 停止摄像头分析
   * 
   * 从视频分析引擎移除摄像头
   */
  stopAnalysis: (id: number): Promise<{ success: boolean; message: string; camera_id: number }> =>
    api.post(`/cameras/${id}/stop-analysis`),

  /**
   * 获取摄像头分析状态
   * 
   * 返回摄像头在引擎中的实时状态
   */
  getAnalysisStatus: (id: number): Promise<{
    camera_id: number
    camera_name: string
    is_enabled: boolean
    engine_status: string
    fps?: number
    queue_size?: number
    total_frames?: number
    processed_frames?: number
    last_frame_time?: string
    message?: string
  }> => api.get(`/cameras/${id}/analysis-status`),
}

// ============ 人员分组 API ============

export const groupApi = {
  /** 获取分组列表 */
  getList: (params?: { page?: number; page_size?: number; keyword?: string; alert_enabled?: boolean }): Promise<PaginatedResponse<PersonGroup>> =>
    api.get('/person-groups', { params }),

  /** 获取所有分组 */
  getAll: (): Promise<{ items: PersonGroup[] }> =>
    api.get('/person-groups/all'),

  /** 获取分组统计 */
  getStats: (): Promise<{ items: PersonGroup[] }> =>
    api.get('/person-groups/stats'),

  /** 创建分组 */
  create: (data: { name: string; description?: string; color?: string; alert_enabled?: boolean; alert_priority?: number; sort_order?: number }): Promise<PersonGroup> =>
    api.post('/person-groups', data),

  /** 获取分组详情 */
  get: (id: number): Promise<PersonGroup> =>
    api.get(`/person-groups/${id}`),

  /** 更新分组 */
  update: (id: number, data: Partial<PersonGroup>): Promise<PersonGroup> =>
    api.put(`/person-groups/${id}`, data),

  /** 删除分组 */
  delete: (id: number, force?: boolean): Promise<void> =>
    api.delete(`/person-groups/${id}`, { params: { force } }),

  /** 切换报警状态 */
  toggleAlert: (id: number, enabled: boolean): Promise<PersonGroup> =>
    api.patch(`/person-groups/${id}/alert`, { alert_enabled: enabled }),
}

// ============ 人员管理 API ============

export const personApi = {
  /** 获取人员列表 */
  getList: (params?: { page?: number; page_size?: number; keyword?: string; group_id?: number; is_active?: boolean; has_face?: boolean }): Promise<PaginatedResponse<Person>> =>
    api.get('/persons', { params }),

  /** 获取所有人员 */
  getAll: (): Promise<{ items: Person[] }> =>
    api.get('/persons/all'),

  /** 创建人员 */
  create: (data: { name: string; employee_id?: string; group_id?: number; department?: string; phone?: string; remark?: string; is_active?: boolean }): Promise<Person> =>
    api.post('/persons', data),

  /** 获取人员详情 */
  get: (id: number): Promise<Person & { face_images: FaceImage[] }> =>
    api.get(`/persons/${id}`),

  /** 更新人员 */
  update: (id: number, data: Partial<Person>): Promise<Person> =>
    api.put(`/persons/${id}`, data),

  /** 删除人员 */
  delete: (id: number): Promise<void> =>
    api.delete(`/persons/${id}`),

  /** 更新状态 */
  updateStatus: (id: number, isActive: boolean): Promise<Person> =>
    api.patch(`/persons/${id}/status`, { is_active: isActive }),

  /** 上传人脸 */
  uploadFace: (id: number, file: File): Promise<any> => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/persons/${id}/faces`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  /** 删除人脸 */
  deleteFace: (personId: number, faceId: number): Promise<void> =>
    api.delete(`/persons/${personId}/faces/${faceId}`),

  /** 设置主图 */
  setPrimaryFace: (personId: number, faceId: number): Promise<void> =>
    api.patch(`/persons/${personId}/faces/${faceId}/primary`),
}

// ============ 报警管理 API ============

export const alertApi = {
  /** 获取报警列表 */
  getList: (params?: { page?: number; page_size?: number; start_date?: string; end_date?: string; camera_id?: number; zone_id?: number; alert_type?: string; person_id?: number; alert_status?: string }): Promise<PaginatedResponse<Alert>> =>
    api.get('/alerts', { params }),

  /** 获取报警统计 */
  getStatistics: (params?: { start_date?: string; end_date?: string }): Promise<AlertStatistics> =>
    api.get('/alerts/statistics', { params }),

  /** 获取报警趋势 */
  getTrend: (period?: string): Promise<{ items: any[]; period: string }> =>
    api.get('/alerts/trend', { params: { period } }),

  /** 获取报警详情 */
  get: (id: number): Promise<Alert> =>
    api.get(`/alerts/${id}`),

  /** 人工反馈/修正 */
  feedback: (id: number, data: { name: string; person_id?: number }): Promise<void> =>
    api.post(`/alerts/${id}/feedback`, data),

  /** 处理报警 */
  process: (id: number, remark?: string): Promise<Alert> =>
    api.patch(`/alerts/${id}/process`, { remark }),

  /** 忽略报警 */
  ignore: (id: number, remark?: string): Promise<Alert> =>
    api.patch(`/alerts/${id}/ignore`, { remark }),

  /** 批量处理 */
  batchProcess: (alertIds: number[], action: 'process' | 'ignore', remark?: string): Promise<{ success_count: number; failed_count: number; failed_ids: number[] }> =>
    api.post('/alerts/batch-process', { alert_ids: alertIds, action, remark }),

  /** 导出 CSV */
  exportCsv: (params?: { start_date?: string; end_date?: string; camera_id?: number; alert_type?: string; alert_status?: string }): Promise<Blob> =>
    api.get('/alerts/export/csv', { params, responseType: 'blob' }),
}

// ============ 系统配置 API ============

export const settingsApi = {
  /** 获取系统配置 */
  getConfig: (): Promise<{ groups: ConfigGroup[] }> =>
    api.get('/settings'),

  /** 更新配置 */
  updateConfig: (items: Array<{ config_key: string; config_value: string }>): Promise<{ success_count: number; failed_count: number }> =>
    api.put('/settings', { items }),

  /** 获取系统状态 */
  getStatus: (): Promise<SystemStatus> =>
    api.get('/settings/status'),

  /** 触发清理 */
  triggerCleanup: (params: { cleanup_type: string; days_to_keep: number; dry_run?: boolean }): Promise<any> =>
    api.post('/settings/cleanup', params),

  /** 获取清理日志 */
  getCleanupLogs: (params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<any>> =>
    api.get('/settings/cleanup-logs', { params }),
}

// ============ 操作日志 API ============

export const logApi = {
  /** 获取日志列表 */
  getList: (params?: { page?: number; page_size?: number; user_id?: number; action?: string; target_type?: string; start_date?: string; end_date?: string }): Promise<PaginatedResponse<OperationLog>> =>
    api.get('/operation-logs', { params }),

  /** 获取日志统计 */
  getStatistics: (params?: { start_date?: string; end_date?: string }): Promise<LogStatistics> =>
    api.get('/operation-logs/statistics', { params }),

  /** 获取操作类型 */
  getActionTypes: (): Promise<{ items: Array<{ value: string; label: string }> }> =>
    api.get('/operation-logs/actions'),

  /** 获取目标类型 */
  getTargetTypes: (): Promise<{ items: Array<{ value: string; label: string }> }> =>
    api.get('/operation-logs/target-types'),

  /** 获取日志详情 */
  get: (id: number): Promise<OperationLog> =>
    api.get(`/operation-logs/${id}`),
}

// ============ 引擎状态 API ============

export const engineApi = {
  /**
   * 获取引擎状态
   * 
   * 返回引擎运行状态、摄像头数量、人脸库信息等
   */
  getStatus: (): Promise<{
    status: string
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
  }> => api.get('/engine/status'),

  /**
   * 获取引擎管理的所有摄像头状态
   * 
   * 返回每个摄像头的运行状态、帧率、队列大小等信息
   */
  getCameras: (): Promise<Array<{
    camera_id: number
    camera_name: string
    status: string
    fps: number
    queue_size: number
    total_frames: number
    processed_frames: number
    last_frame_time?: string
  }>> => api.get('/engine/cameras'),
}

// ============ 健康检查 API ============

export const healthApi = {
  /**
   * 健康检查
   */
  check: (): Promise<{
    status: string
    app: string
    version: string
    engine_status: string
    websocket_clients: number
  }> => axios.get(
    (import.meta.env.VITE_API_BASE_URL || 'http://localhost:329') + '/health'
  ).then(res => res.data),
}

export default api
