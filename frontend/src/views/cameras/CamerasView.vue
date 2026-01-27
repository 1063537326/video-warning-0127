<script setup lang="ts">
/**
 * 摄像头管理页面
 * 
 * 管理摄像头的增删改查、RTSP配置、连通性测试。
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { cameraApi, zoneApi } from '@/api'
import type { Camera, Zone, PaginatedResponse } from '@/types'

// ============ 数据状态 ============

const loading = ref(false)
const cameras = ref<Camera[]>([])
const zones = ref<Zone[]>([])
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 0
})
const keyword = ref('')
const zoneFilter = ref<number | ''>('')
const statusFilter = ref('')

// ============ 弹窗状态 ============

const showFormModal = ref(false)
const showDeleteModal = ref(false)
const showTestModal = ref(false)
const isEditing = ref(false)
const currentCamera = ref<Camera | null>(null)
const formData = reactive({
  name: '',
  zone_id: '' as number | '',
  rtsp_url: '',
  rtsp_username: '',
  rtsp_password: '',
  resolution: '1920x1080',
  fps: 25
})
const submitting = ref(false)
const formError = ref('')

// 测试连接状态
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string; resolution_detected?: string; fps_detected?: number; response_time_ms?: number } | null>(null)

// 分析状态弹窗
const showAnalysisModal = ref(false)
const analysisStatus = ref<{
  camera_id: number
  camera_name: string
  is_enabled: boolean
  engine_status: string
  fps?: number
  queue_size?: number
  total_frames?: number
  processed_frames?: number
  message?: string
} | null>(null)
const loadingAnalysis = ref(false)

// ============ 方法 ============

/**
 * 加载摄像头列表
 */
const loadCameras = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (keyword.value) params.keyword = keyword.value
    if (zoneFilter.value) params.zone_id = zoneFilter.value
    if (statusFilter.value) params.status = statusFilter.value

    const res: PaginatedResponse<Camera> = await cameraApi.getList(params)
    cameras.value = res.items
    pagination.total = res.total
    pagination.totalPages = res.total_pages
  } catch (error: any) {
    console.error('加载摄像头列表失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 加载区域列表
 */
const loadZones = async () => {
  try {
    const res = await zoneApi.getAll()
    // API 返回直接数组或 { items: [...] } 格式
    zones.value = Array.isArray(res) ? res : (res.items || [])
  } catch (error) {
    console.error('加载区域列表失败:', error)
  }
}

/**
 * 搜索
 */
const handleSearch = () => {
  pagination.page = 1
  loadCameras()
}

/**
 * 切换页码
 */
const handlePageChange = (page: number) => {
  pagination.page = page
  loadCameras()
}

/**
 * 打开新增弹窗
 */
const openCreateModal = () => {
  isEditing.value = false
  currentCamera.value = null
  Object.assign(formData, {
    name: '',
    zone_id: '',
    rtsp_url: '',
    rtsp_username: '',
    rtsp_password: '',
    resolution: '1920x1080',
    fps: 25
  })
  formError.value = ''
  showFormModal.value = true
}

/**
 * 打开编辑弹窗
 */
const openEditModal = (camera: Camera) => {
  isEditing.value = true
  currentCamera.value = camera
  Object.assign(formData, {
    name: camera.name,
    zone_id: camera.zone_id || '',
    rtsp_url: camera.rtsp_url,
    rtsp_username: camera.rtsp_username || '',
    rtsp_password: camera.rtsp_password || '',
    resolution: camera.resolution || '1920x1080',
    fps: camera.fps || 25
  })
  formError.value = ''
  showFormModal.value = true
}

/**
 * 提交表单
 */
const handleSubmit = async () => {
  if (!formData.name.trim()) {
    formError.value = '请输入摄像头名称'
    return
  }
  if (!formData.rtsp_url.trim()) {
    formError.value = '请输入RTSP地址'
    return
  }

  submitting.value = true
  formError.value = ''

  try {
    const data = {
      name: formData.name.trim(),
      zone_id: formData.zone_id || undefined,
      rtsp_url: formData.rtsp_url.trim(),
      rtsp_username: formData.rtsp_username.trim() || undefined,
      rtsp_password: formData.rtsp_password.trim() || undefined,
      resolution: formData.resolution,
      fps: formData.fps
    }

    if (isEditing.value && currentCamera.value) {
      await cameraApi.update(currentCamera.value.id, data)
    } else {
      await cameraApi.create(data)
    }

    showFormModal.value = false
    loadCameras()
  } catch (error: any) {
    formError.value = error.response?.data?.detail || '操作失败，请重试'
  } finally {
    submitting.value = false
  }
}

/**
 * 打开删除确认弹窗
 */
const openDeleteModal = (camera: Camera) => {
  currentCamera.value = camera
  showDeleteModal.value = true
}

/**
 * 确认删除
 */
const handleDelete = async () => {
  if (!currentCamera.value) return

  submitting.value = true
  try {
    await cameraApi.delete(currentCamera.value.id)
    showDeleteModal.value = false
    loadCameras()
  } catch (error: any) {
    alert(error.response?.data?.detail || '删除失败，请重试')
  } finally {
    submitting.value = false
  }
}

/**
 * 打开测试弹窗
 */
const openTestModal = (camera: Camera) => {
  currentCamera.value = camera
  testResult.value = null
  showTestModal.value = true
}

/**
 * 测试摄像头连接
 */
const handleTest = async () => {
  if (!currentCamera.value) return

  testing.value = true
  testResult.value = null

  try {
    const res = await cameraApi.test(currentCamera.value.id)
    testResult.value = res
  } catch (error: any) {
    testResult.value = {
      success: false,
      message: error.response?.data?.detail || '测试失败'
    }
  } finally {
    testing.value = false
  }
}

/**
 * 切换分析状态
 */
const handleToggle = async (camera: Camera) => {
  try {
    const newState = !camera.is_enabled
    await cameraApi.toggle(camera.id, newState)
    // 更新本地状态
    camera.is_enabled = newState
    loadCameras()
  } catch (error: any) {
    alert(error.response?.data?.detail || '操作失败')
  }
}

/**
 * 打开分析状态弹窗
 */
const openAnalysisModal = async (camera: Camera) => {
  currentCamera.value = camera
  analysisStatus.value = null
  showAnalysisModal.value = true
  await loadAnalysisStatus(camera.id)
}

/**
 * 加载分析状态
 */
const loadAnalysisStatus = async (cameraId: number) => {
  loadingAnalysis.value = true
  try {
    const res = await cameraApi.getAnalysisStatus(cameraId)
    analysisStatus.value = res
  } catch (error: any) {
    analysisStatus.value = {
      camera_id: cameraId,
      camera_name: currentCamera.value?.name || '',
      is_enabled: false,
      engine_status: 'error',
      message: error.response?.data?.detail || '获取状态失败'
    }
  } finally {
    loadingAnalysis.value = false
  }
}

/**
 * 启动分析
 */
const handleStartAnalysis = async () => {
  if (!currentCamera.value) return
  
  loadingAnalysis.value = true
  try {
    const res = await cameraApi.startAnalysis(currentCamera.value.id)
    if (res.success) {
      await loadAnalysisStatus(currentCamera.value.id)
      loadCameras()
    } else {
      alert(res.message)
    }
  } catch (error: any) {
    alert(error.response?.data?.detail || '启动失败')
  } finally {
    loadingAnalysis.value = false
  }
}

/**
 * 停止分析
 */
const handleStopAnalysis = async () => {
  if (!currentCamera.value) return
  
  loadingAnalysis.value = true
  try {
    const res = await cameraApi.stopAnalysis(currentCamera.value.id)
    if (res.success) {
      await loadAnalysisStatus(currentCamera.value.id)
      loadCameras()
    } else {
      alert(res.message)
    }
  } catch (error: any) {
    alert(error.response?.data?.detail || '停止失败')
  } finally {
    loadingAnalysis.value = false
  }
}

/**
 * 获取引擎状态文本
 */
const getEngineStatusText = (status: string) => {
  switch (status) {
    case 'running': return '运行中'
    case 'connecting': return '连接中'
    case 'stopped': return '已停止'
    case 'error': return '错误'
    case 'not_running': return '未运行'
    case 'unavailable': return '不可用'
    default: return status
  }
}

/**
 * 获取引擎状态样式
 */
const getEngineStatusClass = (status: string) => {
  switch (status) {
    case 'running': return 'text-success-600 bg-success-100'
    case 'connecting': return 'text-warning-600 bg-warning-100'
    case 'stopped': case 'not_running': return 'text-primary-600 bg-primary-100'
    case 'error': case 'unavailable': return 'text-danger-600 bg-danger-100'
    default: return 'text-primary-600 bg-primary-100'
  }
}

/**
 * 获取状态徽章类
 */
const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'online': return 'badge-success'
    case 'offline': return 'badge-primary'
    case 'error': return 'badge-danger'
    default: return 'badge-primary'
  }
}

/**
 * 获取状态文本
 */
const getStatusText = (status: string) => {
  switch (status) {
    case 'online': return '在线'
    case 'offline': return '离线'
    case 'error': return '错误'
    default: return '未知'
  }
}

/**
 * 分页范围
 */
const pageRange = computed(() => {
  const range: number[] = []
  const start = Math.max(1, pagination.page - 2)
  const end = Math.min(pagination.totalPages, pagination.page + 2)
  for (let i = start; i <= end; i++) {
    range.push(i)
  }
  return range
})

// ============ 生命周期 ============

onMounted(() => {
  loadCameras()
  loadZones()
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-primary-900">摄像头管理</h2>
        <p class="text-primary-500 mt-1">配置和管理监控摄像头</p>
      </div>
      <button @click="openCreateModal" class="btn-primary">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        新增摄像头
      </button>
    </div>

    <!-- 搜索筛选 -->
    <div class="card">
      <div class="card-body">
        <div class="flex flex-wrap gap-4">
          <div class="flex-1 min-w-[200px]">
            <input
              v-model="keyword"
              type="text"
              placeholder="搜索摄像头名称..."
              class="input"
              @keyup.enter="handleSearch"
            />
          </div>
          <div class="w-40">
            <select v-model="zoneFilter" class="input" @change="handleSearch">
              <option value="">全部区域</option>
              <option v-for="z in zones" :key="z.id" :value="z.id">{{ z.name }}</option>
            </select>
          </div>
          <div class="w-32">
            <select v-model="statusFilter" class="input" @change="handleSearch">
              <option value="">全部状态</option>
              <option value="online">在线</option>
              <option value="offline">离线</option>
              <option value="error">错误</option>
            </select>
          </div>
          <button @click="handleSearch" class="btn-secondary">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            搜索
          </button>
        </div>
      </div>
    </div>

    <!-- 摄像头列表 -->
    <div class="card">
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="flex items-center gap-3 text-primary-500">
          <svg class="animate-spin w-6 h-6" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span>加载中...</span>
        </div>
      </div>

      <template v-else>
        <div v-if="cameras.length === 0" class="text-center py-20">
          <svg class="w-16 h-16 mx-auto text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <p class="mt-4 text-primary-500">暂无摄像头数据</p>
          <button @click="openCreateModal" class="btn-primary mt-4">新增第一个摄像头</button>
        </div>

        <table v-else class="table">
          <thead>
            <tr>
              <th>摄像头名称</th>
              <th>所属区域</th>
              <th>RTSP地址</th>
              <th>分辨率</th>
              <th>状态</th>
              <th>分析</th>
              <th class="w-40">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="camera in cameras" :key="camera.id">
              <td>
                <div class="font-medium text-primary-900">{{ camera.name }}</div>
              </td>
              <td>{{ camera.zone?.name || '-' }}</td>
              <td>
                <div class="max-w-[200px] truncate text-sm text-primary-500" :title="camera.rtsp_url">
                  {{ camera.rtsp_url }}
                </div>
              </td>
              <td class="text-sm">{{ camera.resolution || '-' }}</td>
              <td>
                <span :class="getStatusBadgeClass(camera.status)">
                  {{ getStatusText(camera.status) }}
                </span>
              </td>
              <td>
                <div class="flex items-center gap-2">
                  <button
                    @click="handleToggle(camera)"
                    :class="[
                      'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                      camera.is_enabled ? 'bg-success-500' : 'bg-primary-200'
                    ]"
                    :title="camera.is_enabled ? '点击停用' : '点击启用'"
                  >
                    <span
                      :class="[
                        'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                        camera.is_enabled ? 'translate-x-6' : 'translate-x-1'
                      ]"
                    />
                  </button>
                  <button
                    @click="openAnalysisModal(camera)"
                    class="text-xs text-accent-600 hover:text-accent-700 underline"
                    title="查看分析状态"
                  >
                    详情
                  </button>
                </div>
              </td>
              <td>
                <div class="flex items-center gap-2">
                  <button 
                    @click="openTestModal(camera)" 
                    class="text-success-600 hover:text-success-700"
                    title="测试连接"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </button>
                  <button 
                    @click="openEditModal(camera)" 
                    class="text-accent-600 hover:text-accent-700"
                    title="编辑"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button 
                    @click="openDeleteModal(camera)" 
                    class="text-danger-600 hover:text-danger-700"
                    title="删除"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 分页 -->
        <div v-if="pagination.totalPages > 1" class="card-footer flex items-center justify-between">
          <div class="text-sm text-primary-500">
            共 {{ pagination.total }} 条记录，第 {{ pagination.page }}/{{ pagination.totalPages }} 页
          </div>
          <div class="flex items-center gap-1">
            <button
              :disabled="pagination.page === 1"
              @click="handlePageChange(pagination.page - 1)"
              class="btn-ghost btn-sm"
            >上一页</button>
            <button
              v-for="p in pageRange"
              :key="p"
              @click="handlePageChange(p)"
              :class="['btn-sm', p === pagination.page ? 'btn-primary' : 'btn-ghost']"
            >{{ p }}</button>
            <button
              :disabled="pagination.page === pagination.totalPages"
              @click="handlePageChange(pagination.page + 1)"
              class="btn-ghost btn-sm"
            >下一页</button>
          </div>
        </div>
      </template>
    </div>

    <!-- 新增/编辑弹窗 -->
    <Teleport to="body">
      <div v-if="showFormModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showFormModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 animate-fade-in max-h-[90vh] overflow-y-auto">
          <div class="px-6 py-4 border-b border-primary-100 sticky top-0 bg-white">
            <h3 class="text-lg font-semibold text-primary-900">
              {{ isEditing ? '编辑摄像头' : '新增摄像头' }}
            </h3>
          </div>
          <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
            <div v-if="formError" class="p-3 bg-danger-50 text-danger-700 text-sm rounded-lg">
              {{ formError }}
            </div>
            <!-- 摄像头名称 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">
                摄像头名称 <span class="text-danger-500">*</span>
              </label>
              <input v-model="formData.name" type="text" class="input" placeholder="如：大堂入口摄像头" />
            </div>
            <!-- 所属区域 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">所属区域</label>
              <select v-model="formData.zone_id" class="input">
                <option value="">不选择</option>
                <option v-for="z in zones" :key="z.id" :value="z.id">{{ z.name }}</option>
              </select>
            </div>
            <!-- RTSP地址 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">
                RTSP地址 <span class="text-danger-500">*</span>
              </label>
              <input v-model="formData.rtsp_url" type="text" class="input" placeholder="rtsp://192.168.1.100:554/stream" />
              <p class="text-xs text-primary-400 mt-1">支持 rtsp:// 或 rtmp:// 协议</p>
            </div>
            <!-- 认证信息 -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-primary-700 mb-1">用户名</label>
                <input v-model="formData.rtsp_username" type="text" class="input" placeholder="可选" />
              </div>
              <div>
                <label class="block text-sm font-medium text-primary-700 mb-1">密码</label>
                <input v-model="formData.rtsp_password" type="password" class="input" placeholder="可选" />
              </div>
            </div>
            <!-- 分辨率和帧率 -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-primary-700 mb-1">分辨率</label>
                <select v-model="formData.resolution" class="input">
                  <option value="1920x1080">1920x1080 (1080p)</option>
                  <option value="1280x720">1280x720 (720p)</option>
                  <option value="640x480">640x480 (480p)</option>
                  <option value="3840x2160">3840x2160 (4K)</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-primary-700 mb-1">帧率 (FPS)</label>
                <input v-model.number="formData.fps" type="number" class="input" min="1" max="60" />
              </div>
            </div>
            <!-- 按钮 -->
            <div class="flex justify-end gap-3 pt-4">
              <button type="button" @click="showFormModal = false" class="btn-secondary">取消</button>
              <button type="submit" :disabled="submitting" class="btn-primary">
                {{ submitting ? '提交中...' : (isEditing ? '保存' : '创建') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- 删除确认弹窗 -->
    <Teleport to="body">
      <div v-if="showDeleteModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showDeleteModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 animate-fade-in">
          <div class="p-6 text-center">
            <div class="w-12 h-12 mx-auto bg-danger-100 rounded-full flex items-center justify-center">
              <svg class="w-6 h-6 text-danger-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-primary-900">确认删除</h3>
            <p class="mt-2 text-primary-500">
              确定要删除摄像头「{{ currentCamera?.name }}」吗？此操作不可撤销。
            </p>
            <div class="flex justify-center gap-3 mt-6">
              <button @click="showDeleteModal = false" class="btn-secondary">取消</button>
              <button @click="handleDelete" :disabled="submitting" class="btn-danger">
                {{ submitting ? '删除中...' : '确认删除' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 测试连接弹窗 -->
    <Teleport to="body">
      <div v-if="showTestModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showTestModal = false" />
        <div class="relative bg-white dark:bg-primary-800 rounded-xl shadow-xl w-full max-w-sm mx-4 animate-fade-in">
          <div class="px-6 py-4 border-b border-primary-100 dark:border-primary-700">
            <h3 class="text-lg font-semibold text-primary-900 dark:text-primary-100">测试摄像头连接</h3>
          </div>
          <div class="p-6">
            <div class="text-center mb-4">
              <p class="text-primary-700 dark:text-primary-200 font-medium">{{ currentCamera?.name }}</p>
              <p class="text-sm text-primary-500 dark:text-primary-400 truncate">{{ currentCamera?.rtsp_url }}</p>
            </div>

            <!-- 测试结果 -->
            <div v-if="testResult" :class="[
              'p-4 rounded-lg mb-4',
              testResult.success ? 'bg-success-50 dark:bg-success-900/30' : 'bg-danger-50 dark:bg-danger-900/30'
            ]">
              <div class="flex items-center gap-2">
                <svg v-if="testResult.success" class="w-5 h-5 text-success-600 dark:text-success-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <svg v-else class="w-5 h-5 text-danger-600 dark:text-danger-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span :class="testResult.success ? 'text-success-700 dark:text-success-300' : 'text-danger-700 dark:text-danger-300'">
                  {{ testResult.success ? '连接成功' : '连接失败' }}
                </span>
              </div>
              <p class="text-sm mt-2 text-primary-600 dark:text-primary-300">{{ testResult.message }}</p>
              <div v-if="testResult.success" class="text-xs text-primary-500 dark:text-primary-400 mt-2 space-y-1">
                <p v-if="testResult.resolution_detected">检测分辨率: {{ testResult.resolution_detected }}</p>
                <p v-if="testResult.fps_detected">检测帧率: {{ testResult.fps_detected }} FPS</p>
                <p v-if="testResult.response_time_ms">响应时间: {{ testResult.response_time_ms }} ms</p>
              </div>
            </div>

            <div class="flex justify-center gap-3">
              <button @click="showTestModal = false" class="btn-secondary">关闭</button>
              <button @click="handleTest" :disabled="testing" class="btn-primary">
                <svg v-if="testing" class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {{ testing ? '测试中...' : '开始测试' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 分析状态弹窗 -->
    <Teleport to="body">
      <div v-if="showAnalysisModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showAnalysisModal = false" />
        <div class="relative bg-white dark:bg-primary-800 rounded-xl shadow-xl w-full max-w-md mx-4 animate-fade-in">
          <div class="px-6 py-4 border-b border-primary-100 dark:border-primary-700">
            <h3 class="text-lg font-semibold text-primary-900 dark:text-primary-100">分析状态详情</h3>
          </div>
          <div class="p-6">
            <div class="text-center mb-4">
              <p class="text-primary-700 dark:text-primary-200 font-medium">{{ currentCamera?.name }}</p>
            </div>

            <!-- 加载中 -->
            <div v-if="loadingAnalysis" class="flex items-center justify-center py-8">
              <svg class="animate-spin w-8 h-8 text-primary-500" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>

            <!-- 状态详情 -->
            <div v-else-if="analysisStatus" class="space-y-4">
              <!-- 引擎状态 -->
              <div class="flex items-center justify-between p-3 bg-primary-50 dark:bg-primary-700/50 rounded-lg">
                <span class="text-primary-600 dark:text-primary-300">引擎状态</span>
                <span 
                  class="px-2 py-1 text-xs font-medium rounded"
                  :class="getEngineStatusClass(analysisStatus.engine_status)"
                >
                  {{ getEngineStatusText(analysisStatus.engine_status) }}
                </span>
              </div>

              <!-- 数据库状态 -->
              <div class="flex items-center justify-between p-3 bg-primary-50 dark:bg-primary-700/50 rounded-lg">
                <span class="text-primary-600 dark:text-primary-300">启用状态</span>
                <span 
                  class="px-2 py-1 text-xs font-medium rounded"
                  :class="analysisStatus.is_enabled ? 'text-success-600 bg-success-100' : 'text-primary-600 bg-primary-100'"
                >
                  {{ analysisStatus.is_enabled ? '已启用' : '已停用' }}
                </span>
              </div>

              <!-- 运行中的详细信息 -->
              <template v-if="analysisStatus.engine_status === 'running'">
                <div class="grid grid-cols-2 gap-3">
                  <div class="p-3 bg-primary-50 dark:bg-primary-700/50 rounded-lg text-center">
                    <p class="text-2xl font-bold text-primary-900 dark:text-primary-100">
                      {{ analysisStatus.fps?.toFixed(1) || '0' }}
                    </p>
                    <p class="text-xs text-primary-500 dark:text-primary-400">FPS</p>
                  </div>
                  <div class="p-3 bg-primary-50 dark:bg-primary-700/50 rounded-lg text-center">
                    <p class="text-2xl font-bold text-primary-900 dark:text-primary-100">
                      {{ analysisStatus.queue_size || 0 }}
                    </p>
                    <p class="text-xs text-primary-500 dark:text-primary-400">队列大小</p>
                  </div>
                  <div class="p-3 bg-primary-50 dark:bg-primary-700/50 rounded-lg text-center">
                    <p class="text-2xl font-bold text-primary-900 dark:text-primary-100">
                      {{ analysisStatus.total_frames || 0 }}
                    </p>
                    <p class="text-xs text-primary-500 dark:text-primary-400">总帧数</p>
                  </div>
                  <div class="p-3 bg-primary-50 dark:bg-primary-700/50 rounded-lg text-center">
                    <p class="text-2xl font-bold text-primary-900 dark:text-primary-100">
                      {{ analysisStatus.processed_frames || 0 }}
                    </p>
                    <p class="text-xs text-primary-500 dark:text-primary-400">已处理</p>
                  </div>
                </div>
              </template>

              <!-- 错误信息 -->
              <div v-if="analysisStatus.message" class="p-3 bg-warning-50 dark:bg-warning-900/30 rounded-lg">
                <p class="text-sm text-warning-700 dark:text-warning-300">{{ analysisStatus.message }}</p>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex justify-center gap-3 mt-6">
              <button @click="showAnalysisModal = false" class="btn-secondary">关闭</button>
              <button 
                v-if="analysisStatus?.engine_status !== 'running'"
                @click="handleStartAnalysis" 
                :disabled="loadingAnalysis"
                class="btn-primary"
              >
                <svg v-if="loadingAnalysis" class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                启动分析
              </button>
              <button 
                v-else
                @click="handleStopAnalysis" 
                :disabled="loadingAnalysis"
                class="btn-danger"
              >
                <svg v-if="loadingAnalysis" class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                停止分析
              </button>
              <button 
                @click="loadAnalysisStatus(currentCamera!.id)" 
                :disabled="loadingAnalysis"
                class="btn-ghost"
                title="刷新状态"
              >
                <svg class="w-5 h-5" :class="{ 'animate-spin': loadingAnalysis }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
