// 摄像头状态管理
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface CameraStatus {
  id: number
  name: string
  status: 'online' | 'offline' | 'error'
  lastHeartbeat: string | null
}

export const useCameraStore = defineStore('camera', () => {
  // 摄像头状态列表
  const cameras = ref<CameraStatus[]>([])

  // 在线摄像头数量
  const onlineCount = computed(() => 
    cameras.value.filter(c => c.status === 'online').length
  )

  // 离线摄像头数量
  const offlineCount = computed(() => 
    cameras.value.filter(c => c.status === 'offline').length
  )

  // 错误摄像头数量
  const errorCount = computed(() => 
    cameras.value.filter(c => c.status === 'error').length
  )

  function setCameras(list: CameraStatus[]) {
    cameras.value = list
  }

  function updateStatus(cameraId: number, status: 'online' | 'offline' | 'error') {
    const camera = cameras.value.find(c => c.id === cameraId)
    if (camera) {
      camera.status = status
      camera.lastHeartbeat = new Date().toISOString()
    }
  }

  return {
    cameras,
    onlineCount,
    offlineCount,
    errorCount,
    setCameras,
    updateStatus
  }
})
