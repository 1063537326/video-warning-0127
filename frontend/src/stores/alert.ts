/**
 * 报警状态管理
 * 
 * 管理实时报警通知、未读数量、声音设置等。
 * 支持 base64 编码的图片和 URL 图片。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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
  alertType: 'stranger' | 'known' | 'blacklist'
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
 * 播放报警音效 (使用 Web Audio API 生成 Beep 声)
 */
function playAlertSound() {
  try {
    const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContext) return;

    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, ctx.currentTime); // A5
    osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.1); // Drop to A4

    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);

    osc.start();
    osc.stop(ctx.currentTime + 0.1);
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

    // 播放报警音效
    if (soundEnabled.value) {
      playAlertSound()
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
    // 打开侧边栏时标记所有为已读
    if (sidebarVisible.value) {
      markAllAsRead()
    }
  }

  /**
   * 打开侧边栏
   */
  function showSidebar() {
    sidebarVisible.value = true
    markAllAsRead()
  }

  /**
   * 关闭侧边栏
   */
  function hideSidebar() {
    sidebarVisible.value = false
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
  }
})
