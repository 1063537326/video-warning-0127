/**
 * WebSocket 全局状态管理（Pinia Store）
 * 
 * 提供全应用唯一的 WebSocket 连接，避免多组件各自创建连接。
 * 所有组件通过 `useWebSocketStore()` 共享同一连接实例。
 * 
 * 功能：
 * - 自动连接与断线重连（指数退避）
 * - 心跳保活（25s 间隔）
 * - 摄像头订阅管理
 * - 消息分发（按类型注册 handler）
 * - 内置报警消息处理（自动写入 alertStore）
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAlertStore } from '@/stores/alert'
import { resolveThumbnail, resolveImageSrc } from '@/utils/image'
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

export const useWebSocketStore = defineStore('websocket', () => {
  // ============ 状态 ============

  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const clientId = ref<string | null>(null)
  const lastMessage = ref<WsMessage | null>(null)
  const reconnectAttempts = ref(0)
  const engineStatus = ref<EngineStatus>('unavailable')
  const subscribedCameras = ref<Set<number>>(new Set())

  // ============ 配置 ============

  const MAX_RECONNECT_ATTEMPTS = 10
  const RECONNECT_INTERVAL = 5000
  const HEARTBEAT_INTERVAL = 25000

  // ============ 内部变量 ============

  let reconnectTimer: number | null = null
  let heartbeatTimer: number | null = null
  const handlers: Map<string, Set<MessageHandler>> = new Map()

  // ============ 核心方法 ============

  /**
   * 获取 WebSocket 连接 URL
   * 
   * 根据环境变量构建 URL，并附带 JWT Token 用于认证。
   */
  function getWsUrl(): string {
    const WS_URL = (import.meta as any).env.VITE_WS_URL || 'ws://localhost:8001/ws'
    const token = localStorage.getItem('access_token')
    let baseUrl = WS_URL
    if (token) {
      baseUrl += `?token=${encodeURIComponent(token)}`
    }
    return baseUrl
  }

  /**
   * 建立 WebSocket 连接
   * 
   * 如果已有活跃连接则跳过。连接成功后自动启动心跳和恢复订阅。
   */
  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }

    const connectUrl = getWsUrl()

    try {
      ws.value = new WebSocket(connectUrl)

      ws.value.onopen = () => {
        isConnected.value = true
        reconnectAttempts.value = 0
        console.log('[WebSocket] 已连接')
        startHeartbeat()

        // 恢复之前的摄像头订阅
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
   * 断开 WebSocket 连接
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
   * 发送消息到服务端
   */
  function send(data: any) {
    if (ws.value && isConnected.value) {
      ws.value.send(JSON.stringify(data))
    }
  }

  // ============ 消息处理 ============

  /**
   * 处理收到的消息，分发到对应的 handler
   */
  function handleMessage(message: WsMessage) {
    const { type, data } = message

    // 触发类型处理器
    const typeHandlers = handlers.get(type)
    if (typeHandlers) {
      typeHandlers.forEach(handler => handler(data))
    }

    // 触发全局处理器
    const allHandlers = handlers.get('*')
    if (allHandlers) {
      allHandlers.forEach(handler => handler(message))
    }

    // 内置处理逻辑
    switch (type) {
      case 'connect':
        clientId.value = data.client_id
        console.log('[WebSocket] 分配客户端 ID:', data.client_id)
        break

      case 'pong':
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
   * 处理报警消息，写入 alertStore
   */
  function handleAlertMessage(data: WsAlertData) {
    const alertStore = useAlertStore()
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
      thumbnail: resolveThumbnail(data.face_image, data.body_image, data.full_image),
      fullImage: resolveImageSrc(data.full_image) || '',
      createdAt: data.timestamp || new Date().toISOString(),
      trackId: data.track_id,
      alertLevel: data.alert_level,
    })

    alertStore.addToast({
      id: alertId,
      cameraId: data.camera_id,
      cameraName: data.camera_name,
      zoneName: data.zone_name,
      alertType: data.alert_type,
      personId: data.person_id,
      personName: data.person_name,
      confidence: data.confidence || 0,
      thumbnail: resolveThumbnail(data.face_image, data.body_image, data.full_image),
      fullImage: resolveImageSrc(data.full_image) || '',
      createdAt: data.timestamp || new Date().toISOString(),
      trackId: data.track_id,
      alertLevel: data.alert_level,
    })
  }

  /** 处理摄像头状态消息 */
  function handleCameraStatusMessage(data: WsCameraStatusData) {
    console.log('[WebSocket] 摄像头状态更新:', data.camera_name, data.status)
  }

  /** 处理引擎状态消息 */
  function handleEngineStatusMessage(data: WsEngineStatusData) {
    engineStatus.value = data.status as EngineStatus
    console.log('[WebSocket] 引擎状态更新:', data.status)
  }

  /** 处理系统通知消息 */
  function handleNotificationMessage(data: any) {
    console.log('[WebSocket] 系统通知:', data)
  }

  // ============ 心跳 ============

  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = window.setInterval(() => {
      if (isConnected.value) {
        send({ type: 'ping' })
      }
    }, HEARTBEAT_INTERVAL)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  // ============ 重连 ============

  function scheduleReconnect() {
    if (reconnectTimer) return
    if (reconnectAttempts.value >= MAX_RECONNECT_ATTEMPTS) {
      console.log('[WebSocket] 达到最大重连次数，停止重连')
      return
    }

    reconnectAttempts.value++
    const delay = RECONNECT_INTERVAL * Math.min(reconnectAttempts.value, 5)
    console.log(`[WebSocket] ${delay / 1000}秒后尝试重连 (${reconnectAttempts.value}/${MAX_RECONNECT_ATTEMPTS})`)

    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  // ============ 订阅管理 ============

  /** 订阅摄像头报警 */
  function subscribe(cameraIds: number[]) {
    cameraIds.forEach(id => subscribedCameras.value.add(id))
    if (isConnected.value) {
      send({ type: 'subscribe', data: { camera_ids: cameraIds } })
    }
  }

  /** 取消订阅摄像头 */
  function unsubscribe(cameraIds: number[]) {
    cameraIds.forEach(id => subscribedCameras.value.delete(id))
    if (isConnected.value) {
      send({ type: 'unsubscribe', data: { camera_ids: cameraIds } })
    }
  }

  /** 订阅所有摄像头 */
  function subscribeAll(cameraIds: number[]) {
    subscribe(cameraIds)
  }

  /** 取消所有订阅 */
  function unsubscribeAll() {
    unsubscribe(Array.from(subscribedCameras.value))
  }

  // ============ 消息 Handler 注册 ============

  /**
   * 注册消息处理器
   * 
   * @param type - 消息类型，'*' 表示所有类型
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
   */
  function off(type: string, handler?: MessageHandler) {
    if (handler) {
      handlers.get(type)?.delete(handler)
    } else {
      handlers.delete(type)
    }
  }

  /** 重置重连计数 */
  function resetReconnect() {
    reconnectAttempts.value = 0
  }

  return {
    // 状态
    ws,
    isConnected,
    clientId,
    lastMessage,
    reconnectAttempts,
    engineStatus,
    subscribedCameras: computed(() => Array.from(subscribedCameras.value)),
    // 连接
    connect,
    disconnect,
    send,
    // 订阅
    subscribe,
    unsubscribe,
    subscribeAll,
    unsubscribeAll,
    // Handler
    on,
    off,
    resetReconnect,
  }
})
