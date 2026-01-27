<script setup lang="ts">
/**
 * 报警卡片组件
 * 
 * 显示单条报警通知的详细信息。
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { AlertNotification } from '@/stores/alert'
import { useAlertStore } from '@/stores/alert'

const props = defineProps<{
  alert: AlertNotification
}>()

const emit = defineEmits<{
  (e: 'dismiss', id: number): void
}>()

const router = useRouter()
const alertStore = useAlertStore()

/**
 * 报警类型样式配置
 */
const typeConfig = computed(() => {
  const configs: Record<string, { label: string; bgClass: string; textClass: string; dotClass: string }> = {
    stranger: {
      label: '陌生人',
      bgClass: 'bg-danger-100 dark:bg-danger-900/40',
      textClass: 'text-danger-700 dark:text-danger-400',
      dotClass: 'bg-danger-500',
    },
    known: {
      label: '已知人员',
      bgClass: 'bg-accent-100 dark:bg-accent-900/40',
      textClass: 'text-accent-700 dark:text-accent-400',
      dotClass: 'bg-accent-500',
    },
    blacklist: {
      label: '黑名单',
      bgClass: 'bg-primary-200 dark:bg-primary-700',
      textClass: 'text-primary-800 dark:text-primary-200',
      dotClass: 'bg-primary-900 dark:bg-primary-300',
    },
  }
  return configs[props.alert.alertType] || configs.stranger
})

/**
 * 格式化时间
 */
const formattedTime = computed(() => {
  const date = new Date(props.alert.createdAt)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  // 1分钟内
  if (diff < 60000) {
    return '刚刚'
  }
  // 1小时内
  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  }
  // 今天
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  // 其他
  return date.toLocaleString('zh-CN', { 
    month: '2-digit', 
    day: '2-digit', 
    hour: '2-digit', 
    minute: '2-digit' 
  })
})

/**
 * 置信度百分比
 */
const confidencePercent = computed(() => {
  return Math.round((props.alert.confidence || 0) * 100)
})

/**
 * 查看详情
 */
const viewDetail = () => {
  router.push({ name: 'alerts', query: { id: props.alert.id } })
  alertStore.hideSidebar()
}

/**
 * 关闭通知
 */
const dismiss = () => {
  emit('dismiss', props.alert.id)
}
</script>

<template>
  <div 
    class="alert-card group"
    :class="{ 'is-unread': !alert.isRead }"
    @click="viewDetail"
  >
    <!-- 未读指示器 -->
    <div 
      v-if="!alert.isRead"
      class="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg"
      :class="typeConfig.dotClass"
    />
    
    <!-- 卡片内容 -->
    <div class="flex gap-3">
      <!-- 缩略图 -->
      <div class="flex-shrink-0 w-14 h-14 rounded-lg overflow-hidden bg-primary-100 dark:bg-primary-700">
        <img 
          v-if="alert.thumbnail"
          :src="alert.thumbnail" 
          :alt="typeConfig.label"
          class="w-full h-full object-cover"
        />
        <div 
          v-else
          class="w-full h-full flex items-center justify-center"
        >
          <svg class="w-6 h-6 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
      </div>

      <!-- 信息 -->
      <div class="flex-1 min-w-0">
        <!-- 类型标签 -->
        <div class="flex items-center gap-2 mb-1">
          <span 
            class="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded"
            :class="[typeConfig.bgClass, typeConfig.textClass]"
          >
            <span class="w-1.5 h-1.5 rounded-full mr-1" :class="typeConfig.dotClass" />
            {{ typeConfig.label }}
          </span>
          <span v-if="alert.personName" class="text-xs text-primary-600 dark:text-primary-300 truncate">
            {{ alert.personName }}
          </span>
        </div>

        <!-- 位置信息 -->
        <p class="text-sm text-primary-900 dark:text-primary-100 truncate">
          {{ alert.cameraName }}
        </p>
        <p v-if="alert.zoneName" class="text-xs text-primary-500 dark:text-primary-400 truncate">
          {{ alert.zoneName }}
        </p>

        <!-- 底部信息 -->
        <div class="flex items-center justify-between mt-1">
          <span class="text-xs text-primary-400 dark:text-primary-500">
            {{ formattedTime }}
          </span>
          <span 
            v-if="confidencePercent > 0"
            class="text-xs text-primary-500 dark:text-primary-400"
          >
            {{ confidencePercent }}%
          </span>
        </div>
      </div>

      <!-- 关闭按钮 -->
      <button 
        @click.stop="dismiss"
        class="flex-shrink-0 p-1 opacity-0 group-hover:opacity-100 hover:bg-primary-100 dark:hover:bg-primary-700 rounded transition-all"
        title="关闭"
      >
        <svg class="w-4 h-4 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.alert-card {
  @apply relative p-3 pl-4 bg-white dark:bg-primary-800 border border-primary-100 dark:border-primary-700 rounded-lg cursor-pointer transition-all duration-200;
}

.alert-card:hover {
  @apply bg-primary-50 dark:bg-primary-700/80 border-primary-200 dark:border-primary-600 shadow-sm;
}

.alert-card.is-unread {
  @apply bg-primary-50/50 dark:bg-primary-800/80;
}
</style>
