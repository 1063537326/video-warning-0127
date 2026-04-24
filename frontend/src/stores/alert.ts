/**
 * 报警状态管理
 * 
 * 管理实时报警通知、未读数量、声音设置等。
 * 支持 base64 编码的图片和 URL 图片。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { alertApi } from '@/api'
import { resolveImageSrc } from '@/utils/image'

/** 报警通知 */
export interface AlertNotification {
  /** 报警 ID */
  id: number
  /** 摄像头 ID */
  cameraId: number
  /** 摄像头名称 */
  cameraName: string
  /** 区域名称 */
  zoneName?: string
  /** 报警类型 */
  alertType: 'stranger' | 'known' | 'blacklist' | 'unidentified'
  /** 人员 ID */
  personId?: number
  /** 人员名称 */
  personName?: string
  /** 分组名称 */
  groupName?: string
  /** 缩略图（支持 URL 或 base64 data URI） */
  thumbnail: string
  /** 全图（支持 URL 或 base64 data URI） */
  fullImage?: string
  /** 置信度（0-1） */
  confidence: number
  /** 创建时间 */
  createdAt: string
  /** 是否已读 */
  isRead?: boolean
  /** 追踪 ID */
  trackId?: string
  /** 报警级别 */
  alertLevel?: 'info' | 'warning' | 'critical'
}

/**
 * 播放报警音效（Web Audio API）
 * 
 * 根据报警级别播放不同模式的音效：
 * - critical: 急促双音（880Hz→440Hz 两次）
 * - warning: 中等单音（660Hz→330Hz）
 * - info: 柔和短音（440Hz）
 * 
 * @param level - 报警级别
 */
function playAlertSound(level: 'critical' | 'warning' | 'info' = 'warning') {
  try {
    const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContext) return;

    const ctx = new AudioContext();
    
    /**
     * 生成一个音调
     */
    const playTone = (freq: number, startTime: number, duration: number, volume: number = 0.3) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, startTime);
      osc.frequency.exponentialRampToValueAtTime(freq / 2, startTime + duration);
      gain.gain.setValueAtTime(volume, startTime);
      gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
      osc.start(startTime);
      osc.stop(startTime + duration);
    };

    switch (level) {
      case 'critical':
        // 急促双音
        playTone(880, ctx.currentTime, 0.12, 0.4);
        playTone(880, ctx.currentTime + 0.18, 0.12, 0.4);
        break;
      case 'warning':
        // 中等单音
        playTone(660, ctx.currentTime, 0.15, 0.3);
        break;
      case 'info':
      default:
        // 柔和短音
        playTone(440, ctx.currentTime, 0.08, 0.15);
        break;
    }
  } catch (error) {
    console.warn('播放报警音效失败:', error)
  }
}

export const useAlertStore = defineStore('alert', () => {
  // 实时报警通知列表
  const notifications = ref<AlertNotification[]>([])

  // 顶部 Toast 通知列表
  const toasts = ref<AlertNotification[]>([])

  // 侧边栏显示状态
  const sidebarVisible = ref(false)

  // 声音开关（从本地存储读取）
  const soundEnabled = ref(localStorage.getItem('alert-sound') !== 'false')

  // 最大通知数量
  const maxNotifications = 100

  // ============ 分页/API 加载状态 ============

  /** ===== 分页配置（可在此处调整每页条数）===== */
  const PAGE_SIZE = 25

  /** 当前页码 */
  const currentPage = ref(1)
  /** 总条数（后端返回） */
  const totalCount = ref(0)
  /** 总页数 */
  const totalPages = ref(0)
  /** 是否正在加载 */
  const isLoading = ref(false)
  /** 是否已加载全部 */
  const allLoaded = computed(() => currentPage.value >= totalPages.value)
  /** 当前日期标记（用于跨天检测） */
  const currentDateStr = ref(getTodayStr())
  /** 是否需要刷新（跨天标记） */
  const needsRefresh = ref(false)
  /** 跨天定时器 ID */
  let midnightTimer: number | null = null

  /**
   * 未读数量
   */
  const unreadCount = computed(() =>
    notifications.value.filter(n => !n.isRead).length
  )

  /**
   * 报警类型标签
   */
  const alertTypeLabels: Record<string, string> = {
    stranger: '陌生人',
    known: '已知人员',
    blacklist: '黑名单',
  }

  /**
   * 报警类型颜色
   */
  const alertTypeColors: Record<string, string> = {
    stranger: 'danger',
    known: 'accent',
    blacklist: 'primary',
  }

  /**
   * 添加通知
   */
  function addNotification(alert: AlertNotification) {
    // 检查是否重复或需要合并 (基于 trackId)
    if (alert.trackId) {
      const existingIndex = notifications.value.findIndex(n => n.trackId === alert.trackId)
      if (existingIndex > -1) {
        // 更新现有记录
        const existing = notifications.value[existingIndex]
        notifications.value[existingIndex] = {
          ...existing,
          ...alert,
          // 保留 ID 如果新的没传 (通常不会)
          id: alert.id || existing.id,
          // 标记为未读以引起注意? 或者取决于逻辑
          isRead: false,
          createdAt: alert.createdAt // 更新时间
        }
        // 移到顶部?
        if (existingIndex > 0) {
          const item = notifications.value.splice(existingIndex, 1)[0];
          notifications.value.unshift(item);
        }
        return
      }
    }

    // 检查 ID 重复
    const exists = notifications.value.some(n => n.id === alert.id)
    if (exists) return

    notifications.value.unshift({
      ...alert,
      isRead: false,
    })

    // 限制列表长度
    if (notifications.value.length > maxNotifications) {
      notifications.value = notifications.value.slice(0, maxNotifications)
    }

    // 播放报警音效（根据级别区分）
    if (soundEnabled.value) {
      playAlertSound(alert.alertLevel || 'warning')
    }
  }

  /**
   * 添加 Toast 通知
   */
  function addToast(alert: AlertNotification) {
    // 1. 检查是否存在相同 trackId 的 Toast
    if (alert.trackId) {
      const existingIndex = toasts.value.findIndex(n => n.trackId === alert.trackId)

      if (existingIndex > -1) {
        const existing = toasts.value[existingIndex]

        // 场景 A: 降级 (已知人员覆盖陌生人)
        if (alert.alertType === 'known') {
          // 移除旧的陌生人/未识别警告
          toasts.value.splice(existingIndex, 1)
          // 可选：添加一条临时的"已确认"提示，或者直接静默
          console.log(`[Toast] Body alert ${alert.trackId} resolved as known person`)
          return
        }

        // 场景 B: 升级/更新 (陌生人背影 -> 陌生人正脸)
        // 直接原地更新，保持 ID 不变以免组件重绘闪烁 (或者更新 ID 以触发动画，这里选择更新内容)
        toasts.value[existingIndex] = {
          ...existing,
          ...alert,
          id: existing.id, // 保持 UI 稳定
          // 如果新的是 face image，它会自动覆盖 thumbnail
        }
        return
      }

      // 场景 C: 已知人员且之前没有 body alert -> 不需要 Toast (User asked for Log/Archive only)
      if (alert.alertType === 'known') {
        return
      }
    }

    // 2. 检查 ID 重复 (fallback)
    if (toasts.value.some(n => n.id === alert.id)) return

    toasts.value.unshift(alert)

    // 限制 Toast 数量，防止遮挡太多 (用户虽说常驻，但为了性能和视线，还是保留一个上限，或者调大)
    if (toasts.value.length > 50) {
      toasts.value.pop()
    }
  }

  /**
   * 移除 Toast
   */
  function removeToast(id: number) {
    const index = toasts.value.findIndex(n => n.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  /**
   * 移除通知
   */
  function removeNotification(id: number) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  /**
   * 清空所有通知
   */
  function clearAll() {
    notifications.value = []
  }

  /**
   * 标记所有为已读
   */
  function markAllAsRead() {
    notifications.value.forEach(n => {
      n.isRead = true
    })
  }

  /**
   * 标记单条为已读
   */
  function markAsRead(id: number) {
    const notification = notifications.value.find(n => n.id === id)
    if (notification) {
      notification.isRead = true
    }
  }

  /**
   * 切换声音开关
   */
  function toggleSound() {
    soundEnabled.value = !soundEnabled.value
    localStorage.setItem('alert-sound', soundEnabled.value.toString())
  }

  /**
   * 切换侧边栏显示
   */
  function toggleSidebar() {
    sidebarVisible.value = !sidebarVisible.value
    if (sidebarVisible.value) {
      onSidebarOpen()
    }
  }

  /**
   * 打开侧边栏
   */
  function showSidebar() {
    sidebarVisible.value = true
    onSidebarOpen()
  }

  /**
   * 侧边栏打开时的统一处理
   */
  function onSidebarOpen() {
    markAllAsRead()
    // 每次打开都重新加载第 1 页（保证数据最新）
    loadAlerts(1, true)
    // 启动跨天检测
    scheduleMidnightRefresh()
  }

  /**
   * 关闭侧边栏
   */
  function hideSidebar() {
    sidebarVisible.value = false
  }

  // ============ API 加载 ============

  /**
   * 获取今天的日期字符串（YYYY-MM-DD）
   */
  function getTodayStr(): string {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }

  /**
   * 从后端 API 加载报警列表
   *
   * @param page - 页码
   * @param reset - 是否重置列表（true = 重新加载第 1 页）
   */
  async function loadAlerts(page: number = 1, reset: boolean = false) {
    if (isLoading.value) return
    isLoading.value = true

    try {
      const today = getTodayStr()
      const startDate = `${today}T00:00:00`

      const response = await alertApi.getList({
        page,
        page_size: PAGE_SIZE,
        start_date: startDate,
      })

      // 将后端 Alert 转为 AlertNotification
      const items: AlertNotification[] = (response.items || []).map((a: any) => ({
        id: a.id,
        cameraId: a.camera_id,
        cameraName: a.camera?.name || '未知摄像头',
        zoneName: a.camera?.zone_name,
        alertType: a.alert_type || 'stranger',
        personId: a.person_id,
        personName: a.person?.name,
        groupName: a.person?.group_name,
        thumbnail: resolveImageSrc(a.face_image_url) || resolveImageSrc(a.body_image_url) || resolveImageSrc(a.full_image_url) || '',
        fullImage: resolveImageSrc(a.full_image_url) || '',
        confidence: a.confidence || 0,
        createdAt: a.created_at,
        isRead: true,
        trackId: a.track_id,
        alertLevel: a.alert_level,
      }))

      if (reset) {
        notifications.value = items
      } else {
        // 追加（去重）
        const existingIds = new Set(notifications.value.map(n => n.id))
        const newItems = items.filter(i => !existingIds.has(i.id))
        notifications.value.push(...newItems)
      }

      currentPage.value = response.page || page
      totalCount.value = response.total || 0
      totalPages.value = response.total_pages || 0
      currentDateStr.value = today
      needsRefresh.value = false
    } catch (error) {
      console.error('[AlertStore] 加载报警列表失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 加载下一页（滚动到底部时调用）
   */
  async function loadMore() {
    if (allLoaded.value || isLoading.value) return
    await loadAlerts(currentPage.value + 1, false)
  }

  /**
   * 设置跨天定时器
   *
   * 计算距离零点的精确毫秒数，设置一次性 setTimeout。
   * 触发后清空列表，标记需要刷新。
   */
  function scheduleMidnightRefresh() {
    if (midnightTimer) {
      clearTimeout(midnightTimer)
      midnightTimer = null
    }

    const now = new Date()
    const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1)
    const msUntilMidnight = midnight.getTime() - now.getTime()

    midnightTimer = window.setTimeout(() => {
      // 跨天：重置数据
      notifications.value = []
      currentPage.value = 1
      totalCount.value = 0
      totalPages.value = 0
      needsRefresh.value = true
      currentDateStr.value = getTodayStr()

      // 如果侧边栏正在打开，立即重新加载
      if (sidebarVisible.value) {
        loadAlerts(1, true)
      }

      // 设置下一个零点定时器
      scheduleMidnightRefresh()
    }, msUntilMidnight)
  }

  /**
   * 获取报警类型标签
   */
  function getTypeLabel(type: string): string {
    return alertTypeLabels[type] || type
  }

  /**
   * 获取报警类型颜色
   */
  function getTypeColor(type: string): string {
    return alertTypeColors[type] || 'primary'
  }

  /**
   * 获取报警级别颜色
   */
  function getLevelColor(level?: string): string {
    switch (level) {
      case 'critical': return 'danger'
      case 'warning': return 'warning'
      case 'info': return 'info'
      default: return 'primary'
    }
  }

  return {
    notifications,
    sidebarVisible,
    soundEnabled,
    unreadCount,
    addNotification,
    removeNotification,
    clearAll,
    markAllAsRead,
    markAsRead,
    toggleSound,
    toggleSidebar,
    showSidebar,
    hideSidebar,
    getTypeLabel,
    getTypeColor,
    getLevelColor,
    // Toast
    toasts,
    addToast,
    removeToast,
    // API 加载
    isLoading,
    totalCount,
    allLoaded,
    currentDateStr,
    loadAlerts,
    loadMore,
    scheduleMidnightRefresh,
  }
})
