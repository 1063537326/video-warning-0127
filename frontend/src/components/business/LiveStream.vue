<template>
  <div class="live-stream-container" v-loading="loading">
    <div v-if="error" class="error-state">
      <el-icon class="text-4xl mb-2 text-gray-500"><VideoCameraFilled /></el-icon>
      <span class="text-gray-400 mb-2">视频流暂不可用</span>
      <el-button type="primary" size="small" @click="retry">重试</el-button>
    </div>
    <img 
      v-else
      :src="streamUrl" 
      class="live-stream-img"
      @error="handleError"
      @load="handleLoad"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { VideoCameraFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  cameraId: number
  autoplay?: boolean
}>()

const error = ref(false)
const loading = ref(true)
const retryCount = ref(0)

const streamUrl = computed(() => {
  const token = localStorage.getItem('access_token')
  // Assume API base URL logic is similar to api/index.ts
  const baseUrl = (import.meta as any).env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1'
  // MJPEG stream endpoint
  return `${baseUrl}/stream/${props.cameraId}?token=${token}&_t=${Date.now() + retryCount.value}`
})

function handleError() {
  loading.value = false
  error.value = true
}

function handleLoad() {
  loading.value = false
  error.value = false
}

function retry() {
  loading.value = true
  error.value = false
  retryCount.value++
}

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

.error-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
</style>
