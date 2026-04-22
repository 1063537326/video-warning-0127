<template>
  <div class="live-stream-container">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <svg class="animate-spin w-8 h-8 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
      <span class="text-gray-400 text-sm mt-2">加载中...</span>
    </div>

    <!-- 错误状态 -->
    <div v-if="error && !loading" class="error-state">
      <svg class="w-10 h-10 mb-2 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
      </svg>
      <span class="text-gray-400 mb-2">视频流暂不可用</span>
      <button 
        @click="retry" 
        class="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
      >
        重试
      </button>
    </div>

    <!-- MJPEG 视频流 -->
    <img 
      v-show="!error && !loading"
      :src="streamUrl" 
      class="live-stream-img"
      @error="handleError"
      @load="handleLoad"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 实时视频流组件
 * 
 * 通过 MJPEG（multipart/x-mixed-replace）协议从后端获取带 AI 标注的实时视频帧，
 * 并以 <img> 标签原生方式渲染。支持自动重试和错误状态展示。
 */
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  /** 摄像头 ID */
  cameraId: number
  /** 是否自动播放（默认 true） */
  autoplay?: boolean
}>()

const error = ref(false)
const loading = ref(true)
const retryCount = ref(0)

/**
 * 计算 MJPEG 流的完整 URL
 * 
 * 附带认证 token 和缓存破坏参数，确保每次重试都获取新连接。
 */
const streamUrl = computed(() => {
  const token = localStorage.getItem('access_token')
  const baseUrl = (import.meta as any).env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1'
  return `${baseUrl}/stream/${props.cameraId}?token=${token}&_t=${Date.now() + retryCount.value}`
})

/** 处理流加载失败 */
function handleError() {
  loading.value = false
  error.value = true
}

/** 处理流加载成功 */
function handleLoad() {
  loading.value = false
  error.value = false
}

/** 重试连接 */
function retry() {
  loading.value = true
  error.value = false
  retryCount.value++
}

/** 监听摄像头切换，自动重新连接 */
watch(() => props.cameraId, () => {
  retry()
})
</script>

<style scoped>
.live-stream-container {
  width: 100%;
  height: 100%;
  background: #1a1a1a;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  border-radius: 4px;
  position: relative;
}

.live-stream-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.error-state,
.loading-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
