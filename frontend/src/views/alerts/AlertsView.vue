<script setup lang="ts">
/**
 * 报警记录页面
 * 
 * 多维度筛选、报警详情、批量处理、导出功能。
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { alertApi, cameraApi, zoneApi } from '@/api'
import type { Alert, Camera, Zone, PaginatedResponse } from '@/types'

// ============ 数据状态 ============

const loading = ref(false)
const alerts = ref<Alert[]>([])
const cameras = ref<Camera[]>([])
const zones = ref<Zone[]>([])
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 0
})

// 筛选条件
const filters = reactive({
  startDate: '',
  endDate: '',
  cameraId: '' as number | '',
  zoneId: '' as number | '',
  alertType: '',
  alertStatus: ''
})

// 批量选择
const selectedIds = ref<number[]>([])
const selectAll = ref(false)

// ============ 弹窗状态 ============

const showDetailModal = ref(false)
const showBatchModal = ref(false)
const currentAlert = ref<Alert | null>(null)
const submitting = ref(false)
const batchAction = ref<'process' | 'ignore'>('process')
const batchRemark = ref('')

// 修正弹窗
const showFixModal = ref(false)
const fixForm = reactive({
  name: '',
  alertId: 0
})

// ============ 方法 ============

/**
 * 加载报警列表
 */
const loadAlerts = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filters.startDate) params.start_date = filters.startDate
    if (filters.endDate) params.end_date = filters.endDate
    if (filters.cameraId) params.camera_id = filters.cameraId
    if (filters.zoneId) params.zone_id = filters.zoneId
    if (filters.alertType) params.alert_type = filters.alertType
    if (filters.alertStatus) params.alert_status = filters.alertStatus

    const res: PaginatedResponse<Alert> = await alertApi.getList(params)
    alerts.value = res.items
    pagination.total = res.total
    pagination.totalPages = res.total_pages
    
    // 清空选择
    selectedIds.value = []
    selectAll.value = false
  } catch (error: any) {
    console.error('加载报警列表失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 加载摄像头和区域
 */
const loadFilters = async () => {
  try {
    const [cameraRes, zoneRes] = await Promise.all([
      cameraApi.getAll(),
      zoneApi.getAll()
    ])
    cameras.value = cameraRes.items
    zones.value = zoneRes.items
  } catch (error) {
    console.error('加载筛选数据失败:', error)
  }
}

/**
 * 搜索
 */
const handleSearch = () => {
  pagination.page = 1
  loadAlerts()
}

/**
 * 重置筛选
 */
const handleReset = () => {
  Object.assign(filters, {
    startDate: '',
    endDate: '',
    cameraId: '',
    zoneId: '',
    alertType: '',
    alertStatus: ''
  })
  handleSearch()
}

/**
 * 切换页码
 */
const handlePageChange = (page: number) => {
  pagination.page = page
  loadAlerts()
}

/**
 * 打开详情弹窗
 */
const openDetailModal = async (alert: Alert) => {
  try {
    const detail = await alertApi.get(alert.id)
    currentAlert.value = detail
    showDetailModal.value = true
  } catch (error) {
    window.alert('加载报警详情失败')
  }
}

/**
 * 处理单个报警
 */
const handleProcess = async (alert: Alert) => {
  if (alert.status !== 'pending') return
  
  try {
    await alertApi.process(alert.id)
    loadAlerts()
  } catch (error: any) {
    window.alert(error.response?.data?.detail || '操作失败')
  }
}

/**
 * 忽略单个报警
 */
const handleIgnore = async (alert: Alert) => {
  if (alert.status !== 'pending') return
  
  try {
    await alertApi.ignore(alert.id)
    loadAlerts()
  } catch (error: any) {
    window.alert(error.response?.data?.detail || '操作失败')
  }
}

/**
 * 切换全选
 */
const handleSelectAll = () => {
  if (selectAll.value) {
    selectedIds.value = alerts.value.filter(a => a.status === 'pending').map(a => a.id)
  } else {
    selectedIds.value = []
  }
}

/**
 * 切换单选
 */
const handleSelect = (id: number) => {
  const index = selectedIds.value.indexOf(id)
  if (index > -1) {
    selectedIds.value.splice(index, 1)
  } else {
    selectedIds.value.push(id)
  }
  selectAll.value = selectedIds.value.length === alerts.value.filter(a => a.status === 'pending').length
}

/**
 * 打开批量处理弹窗
 */
const openBatchModal = (action: 'process' | 'ignore') => {
  if (selectedIds.value.length === 0) {
    window.alert('请先选择要处理的报警')
    return
  }
  batchAction.value = action
  batchRemark.value = ''
  showBatchModal.value = true
}

/**
 * 批量处理
 */
const handleBatchProcess = async () => {
  if (selectedIds.value.length === 0) return

  submitting.value = true
  try {
    const res = await alertApi.batchProcess(selectedIds.value, batchAction.value, batchRemark.value || undefined)
    showBatchModal.value = false
    window.alert(`处理完成：成功 ${res.success_count} 条，失败 ${res.failed_count} 条`)
    loadAlerts()
  } catch (error: any) {
    window.alert(error.response?.data?.detail || '批量处理失败')
  } finally {
    submitting.value = false
  }
}

/**
 * 打开修正弹窗
 */
const openFixModal = (alert: Alert) => {
  fixForm.alertId = alert.id
  fixForm.name = ''
  showFixModal.value = true
}

/**
 * 提交修正
 */
const handleFix = async () => {
  if (!fixForm.name) {
    window.alert('请输入人员姓名')
    return
  }
  
  submitting.value = true
  try {
    await alertApi.feedback(fixForm.alertId, { name: fixForm.name })
    showFixModal.value = false
    showDetailModal.value = false // 同时也关闭详情
    window.alert('修正成功，已注册为已知人员')
    loadAlerts()
  } catch (error: any) {
    window.alert(error.response?.data?.detail || '修正失败')
  } finally {
    submitting.value = false
  }
}

/**
 * 导出 CSV
 */
const handleExport = async () => {
  try {
    const params: any = {}
    if (filters.startDate) params.start_date = filters.startDate
    if (filters.endDate) params.end_date = filters.endDate
    if (filters.cameraId) params.camera_id = filters.cameraId
    if (filters.alertType) params.alert_type = filters.alertType
    if (filters.alertStatus) params.alert_status = filters.alertStatus

    const blob = await alertApi.exportCsv(params)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `alerts_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    window.alert('导出失败')
  }
}

/**
 * 获取报警类型标签
 */
const getAlertTypeLabel = (type: string) => {
  switch (type) {
    case 'stranger': return '陌生人'
    case 'known': return '已知人员'
    case 'blacklist': return '黑名单'
    default: return type
  }
}

/**
 * 获取报警类型样式
 */
const getAlertTypeBadge = (type: string) => {
  switch (type) {
    case 'stranger': return 'badge-warning'
    case 'known': return 'badge-accent'
    case 'blacklist': return 'badge-danger'
    default: return 'badge-primary'
  }
}

/**
 * 获取状态标签
 */
const getStatusLabel = (status: string) => {
  switch (status) {
    case 'pending': return '待处理'
    case 'processed': return '已处理'
    case 'ignored': return '已忽略'
    default: return status
  }
}

/**
 * 获取状态样式
 */
const getStatusBadge = (status: string) => {
  switch (status) {
    case 'pending': return 'badge-danger'
    case 'processed': return 'badge-success'
    case 'ignored': return 'badge-primary'
    default: return 'badge-primary'
  }
}

/**
 * 格式化时间
 */
const formatTime = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
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

/**
 * 待处理数量
 */
const pendingCount = computed(() => {
  return alerts.value.filter(a => a.status === 'pending').length
})

// ============ 生命周期 ============

onMounted(() => {
  loadAlerts()
  loadFilters()
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-primary-900">报警记录</h2>
        <p class="text-primary-500 mt-1">查看和处理系统报警</p>
      </div>
      <div class="flex items-center gap-3">
        <button 
          @click="loadAlerts" 
          class="btn-secondary"
          :disabled="loading"
        >
          <svg 
            class="w-5 h-5" 
            :class="{ 'animate-spin': loading }" 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
        <button @click="handleExport" class="btn-secondary">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          导出 CSV
        </button>
      </div>
    </div>

    <!-- 搜索筛选 -->
    <div class="card">
      <div class="card-body">
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <!-- 开始日期 -->
          <div>
            <label class="block text-xs text-primary-500 mb-1">开始日期</label>
            <input v-model="filters.startDate" type="date" class="input" />
          </div>
          <!-- 结束日期 -->
          <div>
            <label class="block text-xs text-primary-500 mb-1">结束日期</label>
            <input v-model="filters.endDate" type="date" class="input" />
          </div>
          <!-- 区域 -->
          <div>
            <label class="block text-xs text-primary-500 mb-1">区域</label>
            <select v-model="filters.zoneId" class="input">
              <option value="">全部</option>
              <option v-for="z in zones" :key="z.id" :value="z.id">{{ z.name }}</option>
            </select>
          </div>
          <!-- 摄像头 -->
          <div>
            <label class="block text-xs text-primary-500 mb-1">摄像头</label>
            <select v-model="filters.cameraId" class="input">
              <option value="">全部</option>
              <option v-for="c in cameras" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <!-- 报警类型 -->
          <div>
            <label class="block text-xs text-primary-500 mb-1">报警类型</label>
            <select v-model="filters.alertType" class="input">
              <option value="">全部</option>
              <option value="stranger">陌生人</option>
              <option value="known">已知人员</option>
              <option value="blacklist">黑名单</option>
            </select>
          </div>
          <!-- 状态 -->
          <div>
            <label class="block text-xs text-primary-500 mb-1">状态</label>
            <select v-model="filters.alertStatus" class="input">
              <option value="">全部</option>
              <option value="pending">待处理</option>
              <option value="processed">已处理</option>
              <option value="ignored">已忽略</option>
            </select>
          </div>
        </div>
        <div class="flex items-center gap-3 mt-4">
          <button @click="handleSearch" class="btn-primary">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            搜索
          </button>
          <button @click="handleReset" class="btn-ghost">重置</button>
        </div>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedIds.length > 0" class="card bg-accent-50 border-accent-200">
      <div class="card-body py-3 flex items-center justify-between">
        <span class="text-accent-700">
          已选择 <strong>{{ selectedIds.length }}</strong> 条报警
        </span>
        <div class="flex items-center gap-2">
          <button @click="openBatchModal('process')" class="btn-primary btn-sm">批量处理</button>
          <button @click="openBatchModal('ignore')" class="btn-secondary btn-sm">批量忽略</button>
          <button @click="selectedIds = []; selectAll = false" class="btn-ghost btn-sm">取消选择</button>
        </div>
      </div>
    </div>

    <!-- 报警列表 -->
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
        <div v-if="alerts.length === 0" class="text-center py-20">
          <svg class="w-16 h-16 mx-auto text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <p class="mt-4 text-primary-500">暂无报警记录</p>
        </div>

        <table v-else class="table">
          <thead>
            <tr>
              <th class="w-10">
                <input
                  type="checkbox"
                  :checked="selectAll"
                  :disabled="pendingCount === 0"
                  @change="selectAll = !selectAll; handleSelectAll()"
                  class="rounded border-primary-300"
                />
              </th>
              <th>截图</th>
              <th>报警类型</th>
              <th>摄像头</th>
              <th>人员</th>
              <th>置信度</th>
              <th>时间</th>
              <th>状态</th>
              <th class="w-36">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="alert in alerts" :key="alert.id">
              <td>
                <input
                  type="checkbox"
                  :checked="selectedIds.includes(alert.id)"
                  :disabled="alert.status !== 'pending'"
                  @change="handleSelect(alert.id)"
                  class="rounded border-primary-300"
                />
              </td>
              <td>
                <div
                  class="w-12 h-12 rounded-lg overflow-hidden bg-primary-100 cursor-pointer"
                  @click="openDetailModal(alert)"
                >
                  <img
                    v-if="alert.face_image_url || alert.body_image_url || alert.full_image_url"
                    :src="alert.face_image_url || alert.body_image_url || alert.full_image_url"
                    class="w-full h-full object-cover"
                    alt=""
                  />
                  <div v-else class="w-full h-full flex items-center justify-center text-primary-400">
                    <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                </div>
              </td>
              <td>
                <span :class="getAlertTypeBadge(alert.alert_type)">
                  {{ getAlertTypeLabel(alert.alert_type) }}
                </span>
              </td>
              <td>
                <div class="text-sm">
                  <div class="font-medium text-primary-900">{{ alert.camera?.name || '-' }}</div>
                  <div class="text-xs text-primary-400">{{ alert.camera?.zone_name || '' }}</div>
                </div>
              </td>
              <td>
                <div v-if="alert.person" class="text-sm">
                  <div class="font-medium text-primary-900">{{ alert.person.name }}</div>
                  <div
                    v-if="alert.person.group_name"
                    class="text-xs px-1.5 py-0.5 rounded inline-block mt-0.5"
                    :style="{ backgroundColor: (alert.person.group_color || '#3B82F6') + '20', color: alert.person.group_color || '#3B82F6' }"
                  >
                    {{ alert.person.group_name }}
                  </div>
                </div>
                <span v-else class="text-primary-400">-</span>
              </td>
              <td>
                <span v-if="alert.confidence" class="text-sm">
                  {{ (alert.confidence * 100).toFixed(1) }}%
                </span>
                <span v-else class="text-primary-400">-</span>
              </td>
              <td class="text-sm text-primary-500">
                {{ formatTime(alert.created_at) }}
              </td>
              <td>
                <span :class="getStatusBadge(alert.status)">
                  {{ getStatusLabel(alert.status) }}
                </span>
              </td>
              <td>
                <div class="flex items-center gap-2">
                  <button 
                    @click="openDetailModal(alert)" 
                    class="text-primary-600 hover:text-primary-700"
                    title="查看详情"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </button>
                  <button 
                    v-if="alert.status === 'pending'"
                    @click="handleProcess(alert)" 
                    class="text-success-600 hover:text-success-700"
                    title="处理"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </button>
                  <button 
                    v-if="alert.status === 'pending'"
                    @click="handleIgnore(alert)" 
                    class="text-primary-400 hover:text-primary-600"
                    title="忽略"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                  </button>
                  <button
                    v-if="alert.alert_type === 'stranger'"
                    @click="openFixModal(alert)"
                    class="text-accent-600 hover:text-accent-700"
                    title="修正/注册"
                  >
                   <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
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

    <!-- 报警详情弹窗 -->
    <Teleport to="body">
      <div v-if="showDetailModal && currentAlert" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showDetailModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 animate-fade-in max-h-[90vh] overflow-y-auto">
          <div class="px-6 py-4 border-b border-primary-100 sticky top-0 bg-white flex items-center justify-between">
            <h3 class="text-lg font-semibold text-primary-900">报警详情</h3>
            <button @click="showDetailModal = false" class="text-primary-400 hover:text-primary-600">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="p-6">
            <!-- 截图对比 -->
            <div class="grid grid-cols-2 gap-4 mb-6">
              <div>
                <p class="text-sm text-primary-500 mb-2">人脸截图</p>
                <div class="aspect-square rounded-lg overflow-hidden bg-primary-100">
                  <img
                    v-if="currentAlert.face_image_url"
                    :src="currentAlert.face_image_url"
                    class="w-full h-full object-cover"
                    alt=""
                  />
                  <div v-else class="w-full h-full flex items-center justify-center text-primary-400">
                    无截图
                  </div>
                </div>
              </div>
              <div>
                <p class="text-sm text-primary-500 mb-2">全景截图</p>
                <div class="aspect-square rounded-lg overflow-hidden bg-primary-100">
                  <img
                    v-if="currentAlert.full_image_url"
                    :src="currentAlert.full_image_url"
                    class="w-full h-full object-cover"
                    alt=""
                  />
                  <div v-else class="w-full h-full flex items-center justify-center text-primary-400">
                    无截图
                  </div>
                </div>
              </div>
            </div>

            <!-- 历史抓拍 -->
            <div v-if="currentAlert.image_history && currentAlert.image_history.length > 0" class="mb-6">
              <p class="text-sm text-primary-500 mb-2">过程抓拍 ({{ currentAlert.image_history.length }})</p>
              <div class="flex gap-2 overflow-x-auto pb-2">
                <div v-for="(img, index) in currentAlert.image_history" :key="index" class="w-24 h-24 flex-shrink-0 rounded-lg overflow-hidden bg-primary-100 relative">
                  <!-- 这里假设 image_history 中的 path 是相对路径或需要转换，建议后端直接给 URL 或前端处理 -->
                  <!-- 假设后端已处理好 URL prefix -->
                  <img :src="img.url || img.path" class="w-full h-full object-cover" />
                  <div class="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[10px] px-1 truncate">
                    {{ new Date(img.timestamp * 1000).toLocaleTimeString() }}
                    <span v-if="img.score">S:{{ img.score.toFixed(2) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 报警信息 -->
            <div class="space-y-3 text-sm">
              <div class="flex justify-between py-2 border-b border-primary-100">
                <span class="text-primary-500">报警类型</span>
                <span :class="getAlertTypeBadge(currentAlert.alert_type)">
                  {{ getAlertTypeLabel(currentAlert.alert_type) }}
                </span>
              </div>
              <div class="flex justify-between py-2 border-b border-primary-100">
                <span class="text-primary-500">摄像头</span>
                <span class="text-primary-900">{{ currentAlert.camera?.name || '-' }}</span>
              </div>
              <div v-if="currentAlert.person" class="flex justify-between py-2 border-b border-primary-100">
                <span class="text-primary-500">识别人员</span>
                <span class="text-primary-900">{{ currentAlert.person.name }}</span>
              </div>
              <div v-if="currentAlert.confidence" class="flex justify-between py-2 border-b border-primary-100">
                <span class="text-primary-500">置信度</span>
                <span class="text-primary-900">{{ (currentAlert.confidence * 100).toFixed(1) }}%</span>
              </div>
              <div class="flex justify-between py-2 border-b border-primary-100">
                <span class="text-primary-500">报警时间</span>
                <span class="text-primary-900">{{ new Date(currentAlert.created_at).toLocaleString() }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-primary-100">
                <span class="text-primary-500">状态</span>
                <span :class="getStatusBadge(currentAlert.status)">
                  {{ getStatusLabel(currentAlert.status) }}
                </span>
              </div>
              <div v-if="currentAlert.processor" class="flex justify-between py-2 border-b border-primary-100">
                <span class="text-primary-500">处理人</span>
                <span class="text-primary-900">{{ currentAlert.processor.username }}</span>
              </div>
              <div v-if="currentAlert.processed_at" class="flex justify-between py-2 border-b border-primary-100">
                <span class="text-primary-500">处理时间</span>
                <span class="text-primary-900">{{ new Date(currentAlert.processed_at).toLocaleString() }}</span>
              </div>
              <div v-if="currentAlert.process_remark" class="flex justify-between py-2 border-b border-primary-100">
                <span class="text-primary-500">处理备注</span>
                <span class="text-primary-900">{{ currentAlert.process_remark }}</span>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div v-if="currentAlert.status === 'pending'" class="flex justify-end gap-3 mt-6 pt-4 border-t border-primary-100">
              <button @click="handleIgnore(currentAlert); showDetailModal = false" class="btn-secondary">忽略</button>
              <button @click="handleProcess(currentAlert); showDetailModal = false" class="btn-primary">处理</button>
              <button 
                v-if="currentAlert.alert_type === 'stranger'"
                @click="openFixModal(currentAlert)" 
                class="btn-accent"
              >修正/注册</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 修正弹窗 -->
    <Teleport to="body">
      <div v-if="showFixModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showFixModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 animate-fade-in">
          <div class="px-6 py-4 border-b border-primary-100">
            <h3 class="text-lg font-semibold text-primary-900">
              修正人员信息
            </h3>
          </div>
          <div class="p-6">
            <p class="text-primary-600 mb-4 text-sm">
              将该报警记录中的陌生人注册为已知人员。
            </p>
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">姓名 <span class="text-danger-500">*</span></label>
              <input v-model="fixForm.name" type="text" class="input" placeholder="请输入姓名" />
            </div>
            <div class="flex justify-end gap-3 mt-6">
              <button @click="showFixModal = false" class="btn-secondary">取消</button>
              <button @click="handleFix" :disabled="submitting" class="btn-primary">
                {{ submitting ? '提交中...' : '提交' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 批量处理弹窗 -->
    <Teleport to="body">
      <div v-if="showBatchModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showBatchModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 animate-fade-in">
          <div class="px-6 py-4 border-b border-primary-100">
            <h3 class="text-lg font-semibold text-primary-900">
              批量{{ batchAction === 'process' ? '处理' : '忽略' }}
            </h3>
          </div>
          <div class="p-6">
            <p class="text-primary-600 mb-4">
              确定要{{ batchAction === 'process' ? '处理' : '忽略' }}选中的 <strong>{{ selectedIds.length }}</strong> 条报警吗？
            </p>
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">备注（选填）</label>
              <textarea v-model="batchRemark" class="input" rows="2" placeholder="添加处理备注..." />
            </div>
            <div class="flex justify-end gap-3 mt-6">
              <button @click="showBatchModal = false" class="btn-secondary">取消</button>
              <button @click="handleBatchProcess" :disabled="submitting" class="btn-primary">
                {{ submitting ? '处理中...' : '确认' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
