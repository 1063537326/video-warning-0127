<script setup lang="ts">
/**
 * 主布局组件
 * 
 * 包含侧边栏导航、顶部栏、主题切换功能和实时报警通知。
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAlertStore } from '@/stores/alert'
import { useTheme } from '@/composables/useTheme'
import { useWebSocket } from '@/composables/useWebSocket'
import { engineApi } from '@/api'
import NotificationFeed from '@/components/business/NotificationFeed.vue'

// 主题
const { themeMode, cycleTheme } = useTheme()

// 报警通知
const alertStore = useAlertStore()

// WebSocket 连接
const { isConnected, engineStatus: wsEngineStatus } = useWebSocket()

// 本地引擎状态（通过 API 获取）
const localEngineStatus = ref<string>('unavailable')

// 合并引擎状态：优先使用 WebSocket 状态（如果有效），否则使用 API 状态
const engineStatus = computed(() => {
  if (wsEngineStatus.value && wsEngineStatus.value !== 'unavailable') {
    return wsEngineStatus.value
  }
  return localEngineStatus.value
})

/**
 * 加载引擎状态
 */
const loadEngineStatus = async () => {
  try {
    const data = await engineApi.getStatus()
    localEngineStatus.value = data.status || 'unavailable'
  } catch (error) {
    console.error('获取引擎状态失败:', error)
    localEngineStatus.value = 'unavailable'
  }
}

// 定时刷新引擎状态
let engineStatusTimer: ReturnType<typeof setInterval> | null = null

// 图标 (使用 SVG)
const icons: Record<string, string> = {
  dashboard: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" /></svg>`,
  monitor: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" /></svg>`,
  alert: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" /></svg>`,
  person: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" /></svg>`,
  group: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 7.125C2.25 6.504 2.754 6 3.375 6h6c.621 0 1.125.504 1.125 1.125v3.75c0 .621-.504 1.125-1.125 1.125h-6a1.125 1.125 0 0 1-1.125-1.125v-3.75ZM14.25 8.625c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v8.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 0 1-1.125-1.125v-8.25ZM3.75 16.125c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v2.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 0 1-1.125-1.125v-2.25Z" /></svg>`,
  camera: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" /></svg>`,
  zone: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" /></svg>`,
  user: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" /></svg>`,
  log: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>`,
  settings: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg>`,
  menu: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" /></svg>`,
  logout: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 9V5.25A2.25 2.25 0 0 1 10.5 3h6a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 16.5 21h-6a2.25 2.25 0 0 1-2.25-2.25V15m-3 0-3-3m0 0 3-3m-3 3H15" /></svg>`,
  // 主题图标
  sun: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" /></svg>`,
  moon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" /></svg>`,
  computer: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25" /></svg>`,
  // 通知图标
  bell: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" /></svg>`,
}

const route = useRoute()
const authStore = useAuthStore()

const sidebarCollapsed = ref(false)
const userMenuOpen = ref(false)

// 导航菜单类型
interface NavItem {
  name?: string
  label?: string
  icon?: string
  divider?: boolean
  adminOnly?: boolean
}

// 导航菜单
const navItems = computed<NavItem[]>(() => [
  { name: 'dashboard', label: '仪表盘', icon: 'dashboard' },
  { name: 'monitor', label: '实时监控', icon: 'monitor' },
  { name: 'alerts', label: '报警管理', icon: 'alert' },
  { divider: true },
  { name: 'persons', label: '人员管理', icon: 'person' },
  { name: 'groups', label: '人员分组', icon: 'group' },
  { divider: true },
  { name: 'cameras', label: '摄像头管理', icon: 'camera' },
  { name: 'zones', label: '区域管理', icon: 'zone' },
  { divider: true, adminOnly: true },
  { name: 'users', label: '用户管理', icon: 'user', adminOnly: true },
  { name: 'logs', label: '操作日志', icon: 'log', adminOnly: true },
  { name: 'settings', label: '系统设置', icon: 'settings', adminOnly: true },
].filter(item => !item.adminOnly || authStore.isAdmin))

const isActive = (name?: string) => name && route.name === name

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const handleLogout = async () => {
  await authStore.logout()
}

// ============ 生命周期 ============

onMounted(() => {
  // 初始化时获取引擎状态
  loadEngineStatus()
  // 每 5 秒刷新一次引擎状态
  engineStatusTimer = setInterval(loadEngineStatus, 5000)
})

onUnmounted(() => {
  // 清理定时器
  if (engineStatusTimer) {
    clearInterval(engineStatusTimer)
    engineStatusTimer = null
  }
})
</script>

<template>
  <div class="flex h-screen bg-primary-50 dark:bg-primary-900 transition-colors">
    <!-- 侧边栏 -->
    <aside 
      :class="[
        'flex flex-col bg-white dark:bg-primary-800 border-r border-primary-100 dark:border-primary-700 transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-64'
      ]"
    >
      <!-- Logo -->
      <div class="h-16 flex items-center px-4 border-b border-primary-100 dark:border-primary-700">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-primary-700 dark:bg-accent-600 rounded-lg flex items-center justify-center">
            <span class="text-white font-bold text-sm">V</span>
          </div>
          <span 
            v-if="!sidebarCollapsed" 
            class="font-semibold text-primary-900 dark:text-primary-100 whitespace-nowrap"
          >
            视频监控系统
          </span>
        </div>
      </div>

      <!-- 导航菜单 -->
      <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
        <template v-for="(item, index) in navItems" :key="index">
          <!-- 分隔线 -->
          <div v-if="item.divider" class="my-2 border-t border-primary-100 dark:border-primary-700/50" />
          
          <!-- 导航项 -->
          <router-link
            v-else
            :to="{ name: item.name! }"
            :class="[
              'nav-item',
              isActive(item.name) && 'active'
            ]"
            :title="sidebarCollapsed ? item.label : ''"
          >
            <span class="w-5 h-5 flex-shrink-0" v-html="icons[item.icon!]" />
            <span v-if="!sidebarCollapsed" class="truncate">{{ item.label }}</span>
          </router-link>
        </template>
      </nav>

      <!-- 底部用户信息 -->
      <div class="p-3 border-t border-primary-100 dark:border-primary-700">
        <div 
          class="nav-item cursor-pointer"
          @click="userMenuOpen = !userMenuOpen"
        >
          <div class="w-8 h-8 bg-primary-200 dark:bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0">
            <span class="text-primary-700 dark:text-primary-200 font-medium text-sm">
              {{ authStore.username.charAt(0).toUpperCase() }}
            </span>
          </div>
          <div v-if="!sidebarCollapsed" class="flex-1 min-w-0">
            <p class="text-sm font-medium text-primary-900 dark:text-primary-100 truncate">{{ authStore.username }}</p>
            <p class="text-xs text-primary-500 dark:text-primary-400">{{ authStore.isAdmin ? '管理员' : '操作员' }}</p>
          </div>
        </div>

        <!-- 用户菜单 -->
        <div v-if="userMenuOpen && !sidebarCollapsed" class="mt-2 space-y-1">
          <router-link :to="{ name: 'profile' }" class="nav-item">
            <span class="w-5 h-5" v-html="icons.user" />
            <span>个人中心</span>
          </router-link>
          <button @click="handleLogout" class="nav-item w-full text-danger-600 hover:bg-danger-50 dark:text-danger-400 dark:hover:bg-danger-900/30">
            <span class="w-5 h-5" v-html="icons.logout" />
            <span>退出登录</span>
          </button>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 顶部栏 -->
      <header class="h-16 bg-white dark:bg-primary-800 border-b border-primary-100 dark:border-primary-700 flex items-center px-4 gap-4">
        <!-- 折叠按钮 -->
        <button 
          @click="toggleSidebar"
          class="p-2 hover:bg-primary-100 dark:hover:bg-primary-700 rounded-lg transition-colors"
        >
          <span class="w-5 h-5 block text-primary-600 dark:text-primary-300" v-html="icons.menu" />
        </button>

        <!-- 页面标题 -->
        <h1 class="text-lg font-semibold text-primary-900 dark:text-primary-100">
          {{ route.meta.title }}
        </h1>

        <div class="flex-1" />

        <!-- 右侧操作区 -->
        <div class="flex items-center gap-2">
          <!-- 引擎状态指示器 -->
          <div 
            class="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium"
            :class="{
              'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400': engineStatus === 'running',
              'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400': engineStatus === 'starting' || engineStatus === 'stopping',
              'bg-primary-100 text-primary-600 dark:bg-primary-700 dark:text-primary-300': engineStatus === 'stopped',
              'bg-danger-100 text-danger-700 dark:bg-danger-900/30 dark:text-danger-400': engineStatus === 'error',
              'bg-primary-100 text-primary-500 dark:bg-primary-700 dark:text-primary-400': engineStatus === 'unavailable'
            }"
            :title="'引擎状态: ' + engineStatus"
          >
            <span 
              class="w-2 h-2 rounded-full animate-pulse"
              :class="{
                'bg-success-500': engineStatus === 'running',
                'bg-warning-500': engineStatus === 'starting' || engineStatus === 'stopping',
                'bg-primary-400': engineStatus === 'stopped',
                'bg-danger-500': engineStatus === 'error',
                'bg-primary-300 dark:bg-primary-500': engineStatus === 'unavailable'
              }"
            />
            <span class="hidden sm:inline">
              {{ engineStatus === 'running' ? '引擎运行中' : 
                 engineStatus === 'starting' ? '引擎启动中' :
                 engineStatus === 'stopping' ? '引擎停止中' :
                 engineStatus === 'stopped' ? '引擎已停止' :
                 engineStatus === 'error' ? '引擎异常' : '引擎不可用' }}
            </span>
          </div>

          <!-- 报警通知按钮 -->
          <button 
            @click="alertStore.toggleSidebar"
            class="relative p-2 hover:bg-primary-100 dark:hover:bg-primary-700 rounded-lg transition-colors"
            title="报警通知"
          >
            <span class="w-5 h-5 block text-primary-600 dark:text-primary-300" v-html="icons.bell" />
            <!-- 未读数量徽章 -->
            <span 
              v-if="alertStore.unreadCount > 0"
              class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center px-1 text-[10px] font-bold bg-danger-500 text-white rounded-full"
            >
              {{ alertStore.unreadCount > 99 ? '99+' : alertStore.unreadCount }}
            </span>
            <!-- WebSocket 连接状态指示器 -->
            <span 
              class="absolute bottom-1 right-1 w-2 h-2 rounded-full"
              :class="isConnected ? 'bg-success-500' : 'bg-primary-300 dark:bg-primary-600'"
              :title="isConnected ? '已连接' : '未连接'"
            />
          </button>

          <!-- 主题切换按钮 -->
          <button 
            @click="cycleTheme"
            class="p-2 hover:bg-primary-100 dark:hover:bg-primary-700 rounded-lg transition-colors relative group"
            :title="themeMode === 'light' ? '浅色模式' : themeMode === 'dark' ? '深色模式' : '跟随系统'"
          >
            <!-- 浅色模式图标 -->
            <span 
              v-if="themeMode === 'light'" 
              class="w-5 h-5 block text-warning-500" 
              v-html="icons.sun" 
            />
            <!-- 深色模式图标 -->
            <span 
              v-else-if="themeMode === 'dark'" 
              class="w-5 h-5 block text-primary-400" 
              v-html="icons.moon" 
            />
            <!-- 系统模式图标 -->
            <span 
              v-else 
              class="w-5 h-5 block text-primary-500 dark:text-primary-400" 
              v-html="icons.computer" 
            />
            <!-- 提示气泡 -->
            <span class="absolute -bottom-8 left-1/2 -translate-x-1/2 px-2 py-1 text-xs bg-primary-800 dark:bg-primary-600 text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
              {{ themeMode === 'light' ? '浅色' : themeMode === 'dark' ? '深色' : '系统' }}
            </span>
          </button>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="flex-1 overflow-auto p-6 bg-primary-50 dark:bg-primary-900">
        <router-view />
      </main>
    </div>

    <!-- 报警通知侧边栏 -->
    <NotificationFeed />
    
    <!-- 全局 Toast 通知 -->
    <ToastContainer />
  </div>
</template>
