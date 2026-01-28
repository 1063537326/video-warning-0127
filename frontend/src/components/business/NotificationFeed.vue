<script setup lang="ts">
/**
 * 报警通知侧边栏组件
 * 
 * 展示实时报警通知列表，支持滑入动画、声音控制等功能。
 */
import { computed } from 'vue'
import { useAlertStore } from '@/stores/alert'
import AlertCard from './AlertCard.vue'

const alertStore = useAlertStore()

/**
 * 是否有通知
 */
const hasNotifications = computed(() => alertStore.notifications.length > 0)

/**
 * 关闭侧边栏
 */
const closeSidebar = () => {
  alertStore.hideSidebar()
}

/**
 * 清空所有通知
 */
const clearAll = () => {
  alertStore.clearAll()
}

/**
 * 移除单条通知
 */
const dismissNotification = (id: number) => {
  alertStore.removeNotification(id)
}

/**
 * 切换声音
 */
const toggleSound = () => {
  alertStore.toggleSound()
}

// 监听 ESC 键关闭侧边栏
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && alertStore.sidebarVisible) {
    closeSidebar()
  }
}

// 挂载时添加键盘监听
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', handleKeydown)
}
</script>

<template>
  <Teleport to="body">
    <!-- 遮罩层 -->
    <Transition name="fade">
      <div 
        v-if="alertStore.sidebarVisible"
        class="fixed inset-0 bg-black/20 dark:bg-black/40 z-40"
        @click="closeSidebar"
      />
    </Transition>

    <!-- 侧边栏 -->
    <Transition name="slide">
      <aside 
        v-if="alertStore.sidebarVisible"
        class="notification-sidebar"
      >
        <!-- 头部 -->
        <div class="sidebar-header">
          <div class="flex items-center gap-2">
            <h3 class="text-lg font-semibold text-primary-900 dark:text-primary-100">实时报警</h3>
            <span 
              v-if="alertStore.unreadCount > 0"
              class="px-2 py-0.5 text-xs font-medium bg-danger-500 text-white rounded-full"
            >
              {{ alertStore.unreadCount > 99 ? '99+' : alertStore.unreadCount }}
            </span>
          </div>
          
          <div class="flex items-center gap-1">
            <!-- 声音开关 -->
            <button 
              @click="toggleSound"
              class="p-2 hover:bg-primary-100 dark:hover:bg-primary-700 rounded-lg transition-colors"
              :title="alertStore.soundEnabled ? '关闭声音' : '开启声音'"
            >
              <svg 
                v-if="alertStore.soundEnabled"
                class="w-5 h-5 text-primary-600 dark:text-primary-300" 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
              <svg 
                v-else
                class="w-5 h-5 text-primary-400" 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" clip-rule="evenodd" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
              </svg>
            </button>

            <!-- 清空按钮 -->
            <button 
              v-if="hasNotifications"
              @click="clearAll"
              class="p-2 hover:bg-primary-100 dark:hover:bg-primary-700 rounded-lg transition-colors"
              title="清空所有"
            >
              <svg class="w-5 h-5 text-primary-600 dark:text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>

            <!-- 关闭按钮 -->
            <button 
              @click="closeSidebar"
              class="p-2 hover:bg-primary-100 dark:hover:bg-primary-700 rounded-lg transition-colors"
              title="关闭"
            >
              <svg class="w-5 h-5 text-primary-600 dark:text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 通知列表 -->
        <div class="sidebar-content">
          <!-- 空状态 -->
          <div 
            v-if="!hasNotifications"
            class="flex flex-col items-center justify-center h-full text-center px-6"
          >
            <div class="w-16 h-16 bg-primary-100 dark:bg-primary-700 rounded-full flex items-center justify-center mb-4">
              <svg class="w-8 h-8 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </div>
            <p class="text-primary-600 dark:text-primary-300 font-medium">暂无报警通知</p>
            <p class="text-sm text-primary-400 mt-1">系统正常运行中</p>
          </div>

          <!-- 通知列表 -->
          <TransitionGroup 
            v-else
            name="list" 
            tag="div"
            class="space-y-2 p-4"
          >
            <AlertCard
              v-for="alert in alertStore.notifications"
              :key="alert.id"
              :alert="alert"
              @dismiss="dismissNotification"
            />
          </TransitionGroup>
        </div>

        <!-- 底部提示 -->
        <div class="sidebar-footer">
          <p class="text-xs text-primary-400 dark:text-primary-500 text-center">
            点击卡片查看详情 · 最多显示最近 100 条
          </p>
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.notification-sidebar {
  @apply fixed right-0 top-0 bottom-0 w-80 bg-white dark:bg-primary-800 border-l border-primary-100 dark:border-primary-700 shadow-lg z-50 flex flex-col;
}

.sidebar-header {
  @apply flex items-center justify-between px-4 py-3 border-b border-primary-100 dark:border-primary-700;
}

.sidebar-content {
  @apply flex-1 overflow-y-auto;
}

.sidebar-footer {
  @apply px-4 py-3 border-t border-primary-100 dark:border-primary-700;
}

/* 侧边栏滑入动画 */
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

/* 遮罩层淡入动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 列表项动画 */
.list-enter-active {
  transition: all 0.3s ease-out;
}

.list-leave-active {
  transition: all 0.2s ease-in;
}

.list-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

.list-move {
  transition: transform 0.3s ease;
}
</style>
