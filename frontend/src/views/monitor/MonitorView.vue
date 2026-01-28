<script setup lang="ts">
/**
 * 实时监控页面
 * 
 * 多路视频流展示、布局切换、全屏模式、实时告警显示。
 */
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { cameraApi, zoneApi } from '@/api'
import { useWebSocket } from '@/composables/useWebSocket'
import type { Camera, Zone, WsAlertData } from '@/types'
import LiveStream from '@/components/business/LiveStream.vue'
import { type AlertNotification } from '@/stores/alert'

// ============ WebSocket ============

const { 
  isConnected, 
  engineStatus: wsEngineStatus, 
  on, 
  off
} = useWebSocket()

// 本地引擎状态（从 API 获取）
const localEngineStatus = ref<string>('unavailable')

// 合并引擎状态：优先使用 WebSocket 状态，否则使用 API 状态
const engineStatus = computed(() => {
  if (wsEngineStatus.value && wsEngineStatus.value !== 'unavailable') {
    return wsEngineStatus.value
  }
  return localEngineStatus.value
})



// ============ 数据状态 ============

const loading = ref(false)
const cameras = ref<Camera[]>([])
const zones = ref<Zone[]>([])

// 摄像头实时状态（从引擎获取）


// 布局：1, 4, 9, 16 宫格
const layout = ref<1 | 4 | 9 | 16>(4)
const layoutOptions = [
  { value: 1, label: '1 路', icon: '1x1', cols: 1 },
  { value: 4, label: '4 路', icon: '2x2', cols: 2 },
  { value: 9, label: '9 路', icon: '3x3', cols: 3 },
  { value: 16, label: '16 路', icon: '4x4', cols: 4 },
]

// 选中的摄像头（按位置）
const selectedCameras = ref<(Camera | null)[]>(Array(16).fill(null))

// 全屏
const isFullscreen = ref(false)
const monitorContainer = ref<HTMLElement | null>(null)

// 选择摄像头弹窗
const showSelectModal = ref(false)
const selectingSlot = ref(0)
const zoneFilter = ref<number | ''>('')

// 单个放大查看
const showSingleView = ref(false)
const singleViewCamera = ref<Camera | null>(null)

// 实时告警
const recentAlerts = ref<AlertNotification[]>([])
const maxRecentAlerts = 50 // 增加保留数量

// 显示告警面板
const showAlertPanel = ref(true)

// ============ 计算属性 ============

/**
 * 当前布局的列数
 */
const currentCols = computed(() => {
  return layoutOptions.find(l => l.value === layout.value)?.cols || 2
})

/**
 * 当前显示的视频槽位
 */
const visibleSlots = computed(() => {
  return Array.from({ length: layout.value }, (_, i) => i)
})

/**
 * 筛选后的摄像头列表
 */
const filteredCameras = computed(() => {
  if (!zoneFilter.value) return cameras.value
  return cameras.value.filter(c => c.zone_id === zoneFilter.value)
})

/**
 * 在线摄像头数量
 */
const onlineCount = computed(() => {
  return cameras.value.filter(c => c.status === 'online').length
})

// ============ 方法 ============

/**
 * 加载摄像头列表
 */
const loadCameras = async () => {
  loading.value = true
  try {
    const [cameraRes, zoneRes] = await Promise.all([
      cameraApi.getAll(),
      zoneApi.getAll()
    ])
    
    // API 可能返回 { items: [...] } 或直接返回数组
    const cameraList = Array.isArray(cameraRes) ? cameraRes : (cameraRes.items || [])
    const zoneList = Array.isArray(zoneRes) ? zoneRes : (zoneRes.items || [])
    
    cameras.value = cameraList
    zones.value = zoneList

    // 自动填充前 N 个在线或启用分析的摄像头
    const onlineCameras = cameraList.filter((c: any) => c.status === 'online' || c.is_enabled)
    onlineCameras.slice(0, layout.value).forEach((camera: any, index: number) => {
      selectedCameras.value[index] = camera
    })
  } catch (error) {
    console.error('加载摄像头失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 切换布局
 */
const changeLayout = (newLayout: 1 | 4 | 9 | 16) => {
  layout.value = newLayout
}

/**
 * 打开摄像头选择弹窗
 */
const openSelectModal = (slotIndex: number) => {
  selectingSlot.value = slotIndex
  zoneFilter.value = ''
  showSelectModal.value = true
}

/**
 * 选择摄像头
 */
const selectCamera = (camera: Camera) => {
  selectedCameras.value[selectingSlot.value] = camera
  showSelectModal.value = false
}

/**
 * 清空槽位
 */
const clearSlot = (slotIndex: number) => {
  selectedCameras.value[slotIndex] = null
}

/**
 * 单个放大
 */
const openSingleView = (camera: Camera) => {
  singleViewCamera.value = camera
  showSingleView.value = true
}

/**
 * 切换全屏
 */
const toggleFullscreen = async () => {
  if (!monitorContainer.value) return

  try {
    if (!document.fullscreenElement) {
      await monitorContainer.value.requestFullscreen()
      isFullscreen.value = true
    } else {
      await document.exitFullscreen()
      isFullscreen.value = false
    }
  } catch (error) {
    console.error('全屏切换失败:', error)
  }
}

/**
 * 监听全屏变化
 */


/**
 * 获取状态颜色
 */
const getStatusColor = (status: string) => {
  switch (status) {
    case 'online': return 'bg-success-500'
    case 'offline': return 'bg-primary-400'
    case 'error': return 'bg-danger-500'
    default: return 'bg-primary-400'
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
 * 移除本地告警
 */
/**
 * 清空告警
 */
const clearAlerts = () => {
  recentAlerts.value = []
}

/**
 * 获取摄像头 FPS
 */
const getCameraFps = (_id: number) => {
  return 0
}


/**
 * 格式化时间
 */
const formatTime = (time: Date | string) => {
  if (!time) return '-'
  const d = new Date(time)
  return d.toLocaleTimeString('zh-CN', { hour12: false })
}

/**
 * 获取报警类型颜色
 */
const getAlertTypeColor = (type: string) => {
  switch (type) {
    case 'stranger': return 'bg-danger-500'
    case 'known': return 'bg-accent-500'
    case 'blacklist': return 'bg-primary-900'
    default: return 'bg-gray-500'
  }
}

/**
 * 获取报警类型文本
 */
const getAlertTypeText = (type: string) => {
  switch (type) {
    case 'stranger': return '陌生人'
    case 'known': return '已知人员'
    case 'blacklist': return '黑名单'
    default: return '未知'
  }
}

/**
 * 处理告警消息
 */
const handleAlertMessage = (data: WsAlertData) => {
  // 转换 WsAlertData 到 AlertNotification
  // 注意 WsAlertData 是 snake_case, AlertNotification 是 camelCase
  const alertItem: AlertNotification = {
    id: data.alert_id || data.id || Date.now(),
    cameraId: data.camera_id,
    cameraName: data.camera_name || '未知摄像头',
    zoneName: data.zone_name,
    alertType: data.alert_type as 'stranger' | 'known' | 'blacklist',
    personId: data.person_id,
    personName: data.person_name || (data.alert_type === 'stranger' ? '陌生人' : '未知'),
    groupName: data.group_name,
    thumbnail: data.face_image 
      ? (data.face_image.startsWith('data:') ? data.face_image : `data:image/jpeg;base64,${data.face_image}`)
      : '',
    fullImage: data.full_image
      ? (data.full_image.startsWith('data:') ? data.full_image : `data:image/jpeg;base64,${data.full_image}`)
      : undefined,
    confidence: data.confidence || data.similarity || 0,
    createdAt: data.timestamp || new Date().toISOString(),
    trackId: data.track_id,
    alertLevel: data.alert_level || 'info'
  }

  // Merge logic based on trackId
  if (alertItem.trackId) {
    const existingIndex = recentAlerts.value.findIndex(a => a.trackId === alertItem.trackId)
    if (existingIndex > -1) {
      const existing = recentAlerts.value[existingIndex]
      // Update existing alert
      recentAlerts.value[existingIndex] = {
        ...existing,
        ...alertItem,
        id: existing.id, // Keep original ID/key
        thumbnail: alertItem.thumbnail || existing.thumbnail,
      }
      // Move to top
      if (existingIndex > 0) {
        const item = recentAlerts.value.splice(existingIndex, 1)[0]
        recentAlerts.value.unshift(item)
      }
      return
    }
  }

  // Add new alert
  recentAlerts.value.unshift(alertItem)
  
  // Limit size
  if (recentAlerts.value.length > maxRecentAlerts) {
    recentAlerts.value = recentAlerts.value.slice(0, maxRecentAlerts)
  }
}

// ============ 生命周期 ============

onMounted(() => {
  loadCameras()
  on('alert', handleAlertMessage)
})

onUnmounted(() => {
  off('alert', handleAlertMessage)
})
</script>

<template>
  <div 
    ref="monitorContainer"
    :class="[
      'h-full flex flex-col',
      isFullscreen ? 'bg-black p-4' : ''
    ]"
  >
    <!-- 顶部工具栏 -->
    <div :class="[
      'flex items-center justify-between mb-4',
      isFullscreen ? 'text-white' : ''
    ]">
      <div class="flex items-center gap-4">
        <h2 :class="['text-2xl font-bold', isFullscreen ? 'text-white' : 'text-primary-900']">
          实时监控
        </h2>
        <div class="flex items-center gap-2 text-sm">
          <span :class="isFullscreen ? 'text-primary-300' : 'text-primary-500'">
            摄像头:
          </span>
          <span class="text-success-500 font-medium">{{ onlineCount }}</span>
          <span :class="isFullscreen ? 'text-primary-400' : 'text-primary-400'">/</span>
          <span :class="isFullscreen ? 'text-primary-300' : 'text-primary-600'">{{ cameras.length }}</span>
        </div>
        <!-- WebSocket 连接状态 -->
        <div class="flex items-center gap-1.5">
          <div :class="['w-2 h-2 rounded-full', isConnected ? 'bg-success-500' : 'bg-danger-500']" />
          <span :class="['text-xs', isFullscreen ? 'text-primary-300' : 'text-primary-500']">
            {{ isConnected ? '实时连接' : '连接断开' }}
          </span>
        </div>
        <!-- 引擎状态 -->
        <div v-if="engineStatus" class="flex items-center gap-1.5">
          <div :class="[
            'w-2 h-2 rounded-full',
            engineStatus === 'running' ? 'bg-success-500 animate-pulse' : 
            engineStatus === 'stopped' ? 'bg-primary-400' : 'bg-warning-500'
          ]" />
          <span :class="['text-xs', isFullscreen ? 'text-primary-300' : 'text-primary-500']">
            引擎{{ engineStatus === 'running' ? '运行中' : engineStatus === 'stopped' ? '已停止' : '启动中' }}
          </span>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <!-- 布局切换 -->
        <div :class="[
          'flex items-center rounded-lg p-1',
          isFullscreen ? 'bg-white/10' : 'bg-primary-100'
        ]">
          <button
            v-for="opt in layoutOptions"
            :key="opt.value"
            @click="changeLayout(opt.value as 1 | 4 | 9 | 16)"
            :class="[
              'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
              layout === opt.value
                ? (isFullscreen ? 'bg-white text-primary-900' : 'bg-white text-primary-900 shadow-sm')
                : (isFullscreen ? 'text-white/70 hover:text-white' : 'text-primary-500 hover:text-primary-700')
            ]"
          >
            {{ opt.label }}
          </button>
        </div>

        <!-- 刷新 -->
        <button
          @click="loadCameras"
          :class="[
            'p-2 rounded-lg transition-colors',
            isFullscreen ? 'text-white/70 hover:text-white hover:bg-white/10' : 'text-primary-500 hover:text-primary-700 hover:bg-primary-100'
          ]"
          title="刷新"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>

        <!-- 告警面板切换 -->
        <button
          @click="showAlertPanel = !showAlertPanel"
          :class="[
            'p-2 rounded-lg transition-colors relative',
            isFullscreen ? 'text-white/70 hover:text-white hover:bg-white/10' : 'text-primary-500 hover:text-primary-700 hover:bg-primary-100',
            showAlertPanel ? 'bg-accent-100 text-accent-600' : ''
          ]"
          title="告警面板"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <!-- 告警数量徽章 -->
          <span
            v-if="recentAlerts.length > 0"
            class="absolute -top-1 -right-1 w-4 h-4 bg-danger-500 text-white text-xs rounded-full flex items-center justify-center"
          >
            {{ recentAlerts.length > 9 ? '9+' : recentAlerts.length }}
          </span>
        </button>

        <!-- 全屏切换 -->
        <button
          @click="toggleFullscreen"
          :class="[
            'p-2 rounded-lg transition-colors',
            isFullscreen ? 'text-white/70 hover:text-white hover:bg-white/10' : 'text-primary-500 hover:text-primary-700 hover:bg-primary-100'
          ]"
          :title="isFullscreen ? '退出全屏' : '全屏'"
        >
          <svg v-if="!isFullscreen" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
          <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 主内容区：视频网格 + 告警面板 -->
    <div class="flex-1 min-h-0 flex gap-4">
      <!-- 视频网格 -->
      <div :class="['flex-1 min-w-0', showAlertPanel ? '' : '']">
        <div v-if="loading" class="h-full flex items-center justify-center">
          <div :class="['flex items-center gap-3', isFullscreen ? 'text-white/70' : 'text-primary-500']">
            <svg class="animate-spin w-6 h-6" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span>加载中...</span>
          </div>
        </div>

        <div
          v-else
          class="grid gap-2 h-full"
          :style="{ gridTemplateColumns: `repeat(${currentCols}, 1fr)` }"
        >
        <!-- 视频槽位 -->
        <div
          v-for="slotIndex in visibleSlots"
          :key="slotIndex"
          :class="[
            'relative rounded-lg overflow-hidden',
            isFullscreen ? 'bg-gray-900' : 'bg-primary-900'
          ]"
        >
          <!-- 有摄像头 -->
          <template v-if="selectedCameras[slotIndex]">
            <div class="absolute inset-0">
              <!-- MJPEG 视频流 -->
              <!-- MJPEG 视频流 -->
              <LiveStream
                v-if="selectedCameras[slotIndex]!.status === 'online'"
                :camera-id="selectedCameras[slotIndex]!.id"
                class="w-full h-full bg-black"
              />
              <!-- 离线或错误状态占位 -->
              <div 
                v-else
                class="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary-800 to-primary-900"
              >
                <div class="text-center">
                  <svg class="w-16 h-16 mx-auto text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                  </svg>
                  <p class="text-primary-400 text-sm mt-2">信号丢失</p>
                </div>
              </div>
            </div>

            <!-- 顶部信息栏 -->
            <div class="absolute top-0 left-0 right-0 p-2 bg-gradient-to-b from-black/70 to-transparent">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <!-- 状态指示灯 -->
                  <div :class="['w-2 h-2 rounded-full', getStatusColor(selectedCameras[slotIndex]!.status)]" />
                  <span class="text-white text-sm font-medium truncate max-w-[150px]">
                    {{ selectedCameras[slotIndex]!.name }}
                  </span>
                </div>
                <!-- 分析状态 -->
                <span
                  v-if="selectedCameras[slotIndex]!.is_analyzing"
                  class="text-xs bg-success-500/80 text-white px-1.5 py-0.5 rounded"
                >
                  分析中
                </span>
              </div>
              <p v-if="selectedCameras[slotIndex]!.zone" class="text-white/60 text-xs mt-0.5">
                {{ selectedCameras[slotIndex]!.zone?.name }}
              </p>
            </div>

            <!-- 底部工具栏 -->
            <div class="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/70 to-transparent opacity-0 hover:opacity-100 transition-opacity">
              <div class="flex items-center justify-between">
                <span class="text-white/60 text-xs">
                  {{ selectedCameras[slotIndex]!.resolution || '-' }} · 
                  <span class="text-success-400">{{ getCameraFps(selectedCameras[slotIndex]!.id) }}</span> FPS
                </span>
                <div class="flex items-center gap-1">
                  <!-- 放大 -->
                  <button
                    @click="openSingleView(selectedCameras[slotIndex]!)"
                    class="p-1 text-white/70 hover:text-white hover:bg-white/20 rounded"
                    title="放大"
                  >
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                    </svg>
                  </button>
                  <!-- 更换 -->
                  <button
                    @click="openSelectModal(slotIndex)"
                    class="p-1 text-white/70 hover:text-white hover:bg-white/20 rounded"
                    title="更换摄像头"
                  >
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                  </button>
                  <!-- 移除 -->
                  <button
                    @click="clearSlot(slotIndex)"
                    class="p-1 text-white/70 hover:text-danger-400 hover:bg-white/20 rounded"
                    title="移除"
                  >
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </template>

          <!-- 无摄像头 - 空槽位 -->
          <template v-else>
            <button
              @click="openSelectModal(slotIndex)"
              class="w-full h-full flex flex-col items-center justify-center gap-2 text-primary-500 hover:text-primary-400 hover:bg-primary-800/50 transition-colors"
            >
              <svg class="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 4v16m8-8H4" />
              </svg>
              <span class="text-sm">添加摄像头</span>
            </button>
          </template>
        </div>
      </div>
      </div>

      <!-- 右侧告警面板 -->
      <div
        v-if="showAlertPanel"
        :class="[
          'w-80 flex flex-col rounded-lg overflow-hidden',
          isFullscreen ? 'bg-gray-900' : 'bg-white border border-primary-200'
        ]"
      >
        <!-- 面板标题 -->
        <div :class="[
          'px-4 py-3 flex items-center justify-between border-b',
          isFullscreen ? 'border-gray-700' : 'border-primary-100'
        ]">
          <div class="flex items-center gap-2">
            <svg :class="['w-5 h-5', isFullscreen ? 'text-warning-400' : 'text-warning-500']" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span :class="['font-medium', isFullscreen ? 'text-white' : 'text-primary-900']">
              实时告警
            </span>
            <span :class="[
              'text-xs px-1.5 py-0.5 rounded',
              isFullscreen ? 'bg-warning-500/20 text-warning-400' : 'bg-warning-100 text-warning-700'
            ]">
              {{ recentAlerts.length }}
            </span>
          </div>
          <button
            v-if="recentAlerts.length > 0"
            @click="clearAlerts"
            :class="[
              'text-xs px-2 py-1 rounded',
              isFullscreen ? 'text-primary-400 hover:text-white hover:bg-white/10' : 'text-primary-500 hover:text-primary-700 hover:bg-primary-100'
            ]"
          >
            清空
          </button>
        </div>

        <!-- 告警列表 -->
        <div class="flex-1 overflow-y-auto">
          <div v-if="recentAlerts.length === 0" class="h-full flex flex-col items-center justify-center p-6">
            <svg :class="['w-12 h-12', isFullscreen ? 'text-gray-600' : 'text-primary-300']" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p :class="['mt-2 text-sm', isFullscreen ? 'text-gray-500' : 'text-primary-400']">
              暂无告警
            </p>
          </div>

          <div v-else class="divide-y" :class="isFullscreen ? 'divide-gray-700' : 'divide-primary-100'">
            <div
              v-for="alert in recentAlerts"
              :key="alert.id"
              :class="[
                'p-3 hover:bg-opacity-50 transition-colors cursor-pointer',
                isFullscreen ? 'hover:bg-gray-800' : 'hover:bg-primary-50'
              ]"
            >
              <div class="flex gap-3">
                <!-- 人脸图片 -->
                <div class="w-12 h-12 rounded-lg overflow-hidden bg-primary-200 flex-shrink-0">
                  <img
                    v-if="alert.thumbnail"
                    :src="alert.thumbnail"
                    class="w-full h-full object-cover"
                    alt="人脸"
                  />
                  <div v-else class="w-full h-full flex items-center justify-center">
                    <svg class="w-6 h-6 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                </div>

                <!-- 告警信息 -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span :class="[
                      'text-xs px-1.5 py-0.5 rounded text-white',
                      getAlertTypeColor(alert.alertType)
                    ]">
                      {{ getAlertTypeText(alert.alertType) }}
                    </span>
                    <span :class="['text-xs', isFullscreen ? 'text-gray-500' : 'text-primary-400']">
                      {{ formatTime(alert.createdAt) }}
                    </span>
                  </div>
                  <p :class="['font-medium truncate mt-1', isFullscreen ? 'text-white' : 'text-primary-900']">
                    {{ alert.personName }}
                  </p>
                  <p :class="['text-xs truncate', isFullscreen ? 'text-gray-400' : 'text-primary-500']">
                    {{ alert.cameraName }}
                    <span v-if="alert.confidence > 0" class="ml-1">
                      · 相似度 {{ (alert.confidence * 100).toFixed(0) }}%
                    </span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部统计 -->
        <div :class="[
          'px-4 py-2 text-xs border-t',
          isFullscreen ? 'border-gray-700 text-gray-500' : 'border-primary-100 text-primary-500'
        ]">
          实时监控中 · 最近 {{ maxRecentAlerts }} 条告警
        </div>
      </div>
    </div>

    <!-- 摄像头选择弹窗 -->
    <Teleport to="body">
      <div v-if="showSelectModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showSelectModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 animate-fade-in max-h-[80vh] flex flex-col">
          <div class="px-6 py-4 border-b border-primary-100 flex items-center justify-between">
            <h3 class="text-lg font-bold text-primary-900">选择摄像头</h3>
            <button @click="showSelectModal = false" class="text-primary-400 hover:text-primary-600">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div class="p-4 border-b border-primary-100">
            <div class="flex gap-2">
              <input 
                v-model="zoneFilter"
                type="text"
                placeholder="搜索区域..."
                class="flex-1 px-3 py-2 border border-primary-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-500/50"
              />
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-4">
             <div v-if="loading" class="text-center py-8 text-primary-500">加载中...</div>
             <div v-else class="grid gap-2">
               <div 
                 v-for="camera in filteredCameras"
                 :key="camera.id"
                 @click="selectCamera(camera)"
                 :class="[
                   'p-3 rounded-lg border cursor-pointer transition-colors flex items-center justify-between',
                   camera.status === 'online' ? 'bg-white border-primary-200 hover:border-accent-500' : 'bg-gray-50 border-gray-200 opacity-60'
                 ]"
               >
                 <div class="flex items-center gap-3">
                   <div :class="['w-2 h-2 rounded-full', getStatusColor(camera.status)]" />
                   <div>
                     <p class="font-medium text-primary-900">{{ camera.name }}</p>
                     <p class="text-xs text-primary-500">
                       {{ camera.zone?.name || '未分配区域' }}
                     </p>
                   </div>
                 </div>
                 <div class="text-xs text-primary-400">
                   <span v-if="camera.is_analyzing" class="text-success-600 mr-2">分析中</span>
                   {{ getStatusText(camera.status) }}
                 </div>
               </div>
             </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 单个视频放大查看 -->
    <Teleport to="body">
      <div v-if="showSingleView && singleViewCamera" class="fixed inset-0 z-[60] bg-black flex flex-col">
         <div class="h-14 flex items-center justify-between px-4 bg-gray-900 border-b border-gray-800">
           <div class="flex items-center gap-3">
             <div :class="['w-2.5 h-2.5 rounded-full', getStatusColor(singleViewCamera.status)]" />
             <h3 class="text-white font-medium text-lg">{{ singleViewCamera.name }}</h3>
             <span class="text-white/50 text-sm border-l border-white/20 pl-3">
               {{ singleViewCamera.zone?.name }}
             </span>
           </div>
           <button @click="showSingleView = false" class="text-white/70 hover:text-white p-2 rounded-lg hover:bg-white/10">
             <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
             </svg>
           </button>
         </div>
         <div class="flex-1 relative">
           <LiveStream
             v-if="singleViewCamera.status === 'online'"
             :camera-id="singleViewCamera.id"
             class="w-full h-full object-contain"
           />
           <div v-else class="w-full h-full flex flex-col items-center justify-center text-white/50">
             <svg class="w-16 h-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
             </svg>
             <p>摄像头离线</p>
           </div>
         </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* 确保全屏时占满 */
:fullscreen {
  background: black;
}
</style>
