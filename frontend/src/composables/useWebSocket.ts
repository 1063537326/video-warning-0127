/**
 * WebSocket 组合式函数
 * 
 * 提供 WebSocket 连接管理、自动重连、消息分发等功能。
 * 适配后端新的消息格式，支持摄像头订阅、引擎状态监听。
 */
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useAlertStore } from '@/stores/alert'
import type {
  WsMessage,
  WsMessageType,
  WsAlertData,
  WsCameraStatusData,
  WsEngineStatusData,
  EngineStatus
} from '@/types'

/** 消息处理器类型 */
type MessageHandler<T = any> = (data: T) => void

/** WebSocket 配置选项 */
export interface WebSocketOptions {
  /** 是否自动连接 */
  autoConnect?: boolean
  /** 重连间隔（毫秒） */
  reconnectInterval?: number
  /** 最大重连次数 */
  maxReconnectAttempts?: number
  /** 心跳间隔（毫秒） */
  heartbeatInterval?: number
}

/**
 * WebSocket 组合式函数
 * 
 * @param url - WebSocket 服务器地址（可选）
 * @param options - 配置选项
 * @returns WebSocket 相关状态和方法
 * 
 * @example
 * ```ts
 * const { isConnected, subscribe, on } = useWebSocket()
 * 
 * // 订阅摄像头报警
 * subscribe([1, 2, 3])
 * 
 * // 监听引擎状态
 * on('engine_status', (data) => {
 *   console.log('引擎状态:', data.status)
 * })
 * ```
 */
export function useWebSocket(url?: string, options?: WebSocketOptions) {
  const {
    autoConnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10,
    heartbeatInterval = 25000,  // 25秒发送心跳，小于服务端30秒超时
  } = options || {}

  // 获取 WebSocket URL (removed unused variable)

  // 状态
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const clientId = ref<string | null>(null)
  const lastMessage = ref<WsMessage | null>(null)
  const reconnectAttempts = ref(0)
  const engineStatus = ref<EngineStatus>('unavailable')
  const subscribedCameras = ref<Set<number>>(new Set())

  // 计时器
  let reconnectTimer: number | null = null
  let heartbeatTimer: number | null = null

  // 消息处理器
  const handlers: Map<string, Set<MessageHandler>> = new Map()

  // Alert Store
  const alertStore = useAlertStore()

  /**
   * 获取默认 WebSocket URL
   * 
   * 根据当前页面协议自动选择 ws 或 wss，
   * 并附加 token 用于身份验证。
   */
  function getDefaultWsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_WS_HOST || window.location.host
    const token = localStorage.getItem('access_token')

    let baseUrl = `${protocol}//${host}/ws`
    if (token) {
      baseUrl += `?token=${encodeURIComponent(token)}`
    }
    return baseUrl
  }

  /**
   * 连接 WebSocket
   */
  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }

    // 重新生成 URL（token 可能已更新）
    const connectUrl = url || getDefaultWsUrl()

    try {
      ws.value = new WebSocket(connectUrl)

      ws.value.onopen = () => {
        isConnected.value = true
        reconnectAttempts.value = 0
        console.log('[WebSocket] 已连接')

        // 启动心跳
        startHeartbeat()

        // 重新订阅摄像头
        if (subscribedCameras.value.size > 0) {
          subscribe(Array.from(subscribedCameras.value))
        }
      }

      ws.value.onmessage = (event) => {
        try {
          const message: WsMessage = JSON.parse(event.data)
          lastMessage.value = message
          handleMessage(message)
        } catch (error) {
          console.error('[WebSocket] 消息解析失败:', error)
        }
      }

      ws.value.onclose = (event) => {
        isConnected.value = false
        clientId.value = null
        stopHeartbeat()
        console.log('[WebSocket] 连接关闭:', event.code, event.reason)

        // 非正常关闭时尝试重连
        if (event.code !== 1000) {
          scheduleReconnect()
        }
      }

      ws.value.onerror = (error) => {
        console.error('[WebSocket] 连接错误:', error)
      }
    } catch (error) {
      console.error('[WebSocket] 创建连接失败:', error)
      scheduleReconnect()
    }
  }

  /**
   * 处理收到的消息
   */
  function handleMessage(message: WsMessage) {
    const { type, data } = message

    // 触发对应类型的处理器
    const typeHandlers = handlers.get(type)
    if (typeHandlers) {
      typeHandlers.forEach(handler => handler(data))
    }

    // 触发全局处理器
    const allHandlers = handlers.get('*')
    if (allHandlers) {
      allHandlers.forEach(handler => handler(message))
    }

    // 内置处理
    switch (type) {
      case 'connect':
        // 保存客户端 ID
        clientId.value = data.client_id
        console.log('[WebSocket] 分配客户端 ID:', data.client_id)
        break

      case 'pong':
        // 心跳响应，无需处理
        break

      case 'alert':
        handleAlertMessage(data as WsAlertData)
        break

      case 'camera_status':
        handleCameraStatusMessage(data as WsCameraStatusData)
        break

      case 'engine_status':
        handleEngineStatusMessage(data as WsEngineStatusData)
        break

      case 'notification':
        handleNotificationMessage(data)
        break

      case 'error':
        console.error('[WebSocket] 服务端错误:', data)
        break
    }
  }

  /**
   * 处理报警消息
   */
  function handleAlertMessage(data: WsAlertData) {
    // 生成临时 ID（如果后端没有返回）
    const alertId = data.id || Date.now()

    alertStore.addNotification({
      id: alertId,
      cameraId: data.camera_id,
      cameraName: data.camera_name,
      zoneName: data.zone_name,
      alertType: data.alert_type,
      personId: data.person_id,
      personName: data.person_name,
      confidence: data.confidence || 0,
      // 优先使用 face_image，其次 body_image，最后 full_image
      thumbnail: data.face_image ? (data.face_image.startsWith('/') ? data.face_image : `data:image/jpeg;base64,${data.face_image}`)
        : data.body_image ? (data.body_image.startsWith('/') ? data.body_image : `data:image/jpeg;base64,${data.body_image}`)
          : data.full_image ? (data.full_image.startsWith('/') ? data.full_image : `data:image/jpeg;base64,${data.full_image}`)
            : '',
      // 同理处理 fullImage
      fullImage: data.full_image ? (data.full_image.startsWith('/') ? data.full_image : `data:image/jpeg;base64,${data.full_image}`) : '',
      createdAt: data.timestamp || new Date().toISOString(),
      trackId: data.track_id,
      alertLevel: data.alert_level,
    })

    // 添加 Toast 通知 (常驻)
    alertStore.addToast({
      id: alertId,
      cameraId: data.camera_id,
      cameraName: data.camera_name,
      zoneName: data.zone_name,
      alertType: data.alert_type,
      personId: data.person_id,
      personName: data.person_name,
      confidence: data.confidence || 0,
      thumbnail: data.face_image ? `data:image/jpeg;base64,${data.face_image}` : '',
      fullImage: data.full_image ? `data:image/jpeg;base64,${data.full_image}` : '',
      createdAt: data.timestamp || new Date().toISOString(),
      trackId: data.track_id,
      alertLevel: data.alert_level,
    })
  }

  /**
   * 处理摄像头状态消息
   */
  function handleCameraStatusMessage(data: WsCameraStatusData) {
    // 可以在这里触发摄像头状态更新事件
    console.log('[WebSocket] 摄像头状态更新:', data.camera_name, data.status)
  }

  /**
   * 处理引擎状态消息
   */
  function handleEngineStatusMessage(data: WsEngineStatusData) {
    engineStatus.value = data.status as EngineStatus
    console.log('[WebSocket] 引擎状态更新:', data.status)
  }

  /**
   * 处理系统通知消息
   */
  function handleNotificationMessage(data: any) {
    // 可以在这里显示系统通知
    console.log('[WebSocket] 系统通知:', data)
  }

  /**
   * 启动心跳
   */
  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = window.setInterval(() => {
      if (isConnected.value) {
        send({ type: 'ping' })
      }
    }, heartbeatInterval)
  }

  /**
   * 停止心跳
   */
  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  /**
   * 计划重连
   */
  function scheduleReconnect() {
    if (reconnectTimer) return
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      console.log('[WebSocket] 达到最大重连次数，停止重连')
      return
    }

    reconnectAttempts.value++
    const delay = reconnectInterval * Math.min(reconnectAttempts.value, 5)
    console.log(`[WebSocket] ${delay / 1000}秒后尝试重连 (${reconnectAttempts.value}/${maxReconnectAttempts})`)

    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  /**
   * 断开连接
   */
  function disconnect() {
    stopHeartbeat()
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws.value) {
      ws.value.close(1000, '用户断开连接')
      ws.value = null
    }
    isConnected.value = false
    clientId.value = null
  }

  /**
   * 发送消息
   * 
   * @param data - 要发送的数据
   */
  function send(data: any) {
    if (ws.value && isConnected.value) {
      ws.value.send(JSON.stringify(data))
    }
  }

  /**
   * 订阅摄像头
   * 
   * @param cameraIds - 摄像头 ID 数组
   */
  function subscribe(cameraIds: number[]) {
    cameraIds.forEach(id => subscribedCameras.value.add(id))
    if (isConnected.value) {
      send({
        type: 'subscribe',
        data: { camera_ids: cameraIds }
      })
    }
  }

  /**
   * 取消订阅摄像头
   * 
   * @param cameraIds - 摄像头 ID 数组
   */
  function unsubscribe(cameraIds: number[]) {
    cameraIds.forEach(id => subscribedCameras.value.delete(id))
    if (isConnected.value) {
      send({
        type: 'unsubscribe',
        data: { camera_ids: cameraIds }
      })
    }
  }

  /**
   * 订阅所有摄像头
   * 
   * 注意：需要先从 API 获取摄像头列表
   * 
   * @param cameraIds - 所有摄像头 ID 数组
   */
  function subscribeAll(cameraIds: number[]) {
    subscribe(cameraIds)
  }

  /**
   * 取消所有订阅
   */
  function unsubscribeAll() {
    const ids = Array.from(subscribedCameras.value)
    unsubscribe(ids)
  }

  /**
   * 注册消息处理器
   * 
   * @param type - 消息类型，'*' 表示接收所有消息
   * @param handler - 处理函数
   * @returns 取消注册的函数
   */
  function on<T = any>(type: WsMessageType | '*', handler: MessageHandler<T>): () => void {
    if (!handlers.has(type)) {
      handlers.set(type, new Set())
    }
    handlers.get(type)!.add(handler as MessageHandler)

    return () => {
      handlers.get(type)?.delete(handler as MessageHandler)
    }
  }

  /**
   * 移除消息处理器
   * 
   * @param type - 消息类型
   * @param handler - 处理函数（可选，不传则移除该类型所有处理器）
   */
  function off(type: string, handler?: MessageHandler) {
    if (handler) {
      handlers.get(type)?.delete(handler)
    } else {
      handlers.delete(type)
    }
  }

  /**
   * 重置重连计数
   */
  function resetReconnect() {
    reconnectAttempts.value = 0
  }

  // 自动连接
  onMounted(() => {
    if (autoConnect) {
      connect()
    }
  })

  // 清理
  onUnmounted(() => {
    disconnect()
    handlers.clear()
  })

  return {
    /** WebSocket 实例 */
    ws,
    /** 是否已连接 */
    isConnected,
    /** 客户端 ID */
    clientId,
    /** 最后收到的消息 */
    lastMessage,
    /** 重连尝试次数 */
    reconnectAttempts,
    /** 引擎状态 */
    engineStatus,
    /** 已订阅的摄像头 */
    subscribedCameras: computed(() => Array.from(subscribedCameras.value)),
    /** 连接 */
    connect,
    /** 断开连接 */
    disconnect,
    /** 发送消息 */
    send,
    /** 订阅摄像头 */
    subscribe,
    /** 取消订阅摄像头 */
    unsubscribe,
    /** 订阅所有摄像头 */
    subscribeAll,
    /** 取消所有订阅 */
    unsubscribeAll,
    /** 注册消息处理器 */
    on,
    /** 移除消息处理器 */
    off,
    /** 重置重连计数 */
    resetReconnect,
  }
}

/**
 * 创建全局 WebSocket 实例
 * 
 * 用于在非组件环境中使用 WebSocket。
 */
export function createGlobalWebSocket(options?: WebSocketOptions) {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  // ... 类似的实现，但不依赖生命周期钩子
  return { ws, isConnected }
}
