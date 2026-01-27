/**
 * 视频监控报警系统 - 前端入口
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import { initTheme } from './composables/useTheme'

import './assets/main.css'

// 提前初始化主题，避免页面闪烁
initTheme()

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 初始化认证状态
const authStore = useAuthStore()
authStore.init()

app.mount('#app')
