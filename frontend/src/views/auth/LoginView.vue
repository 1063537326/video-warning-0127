<script setup lang="ts">
/**
 * 登录页面
 */
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = computed(() => authStore.loading)

const handleSubmit = async () => {
  error.value = ''
  
  if (!username.value.trim()) {
    error.value = '请输入用户名'
    return
  }
  if (!password.value) {
    error.value = '请输入密码'
    return
  }

  try {
    await authStore.login(username.value.trim(), password.value)
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = '登录失败，请检查网络连接'
    }
  }
}
</script>

<template>
  <div class="min-h-screen flex">
    <!-- 左侧装饰区 -->
    <div class="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-700 via-primary-800 to-primary-900 relative overflow-hidden">
      <!-- 装饰图案 -->
      <div class="absolute inset-0">
        <div class="absolute top-0 left-0 w-96 h-96 bg-primary-600/20 rounded-full -translate-x-1/2 -translate-y-1/2" />
        <div class="absolute bottom-0 right-0 w-[500px] h-[500px] bg-accent-500/10 rounded-full translate-x-1/4 translate-y-1/4" />
        <div class="absolute top-1/2 left-1/2 w-72 h-72 bg-primary-500/10 rounded-full -translate-x-1/2 -translate-y-1/2" />
      </div>
      
      <!-- 内容 -->
      <div class="relative z-10 flex flex-col justify-center px-12 text-white">
        <div class="mb-8">
          <div class="w-16 h-16 bg-white/10 rounded-2xl flex items-center justify-center mb-6 backdrop-blur-sm">
            <svg class="w-8 h-8 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
            </svg>
          </div>
          <h1 class="text-4xl font-bold mb-4">视频监控报警系统</h1>
          <p class="text-lg text-primary-200 leading-relaxed">
            智能人脸识别 · 实时报警推送 · 高效安全管理
          </p>
        </div>
        
        <div class="space-y-4 text-primary-200">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 bg-accent-500/20 rounded-lg flex items-center justify-center">
              <svg class="w-4 h-4 text-accent-300" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
              </svg>
            </div>
            <span>多路摄像头实时监控</span>
          </div>
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 bg-accent-500/20 rounded-lg flex items-center justify-center">
              <svg class="w-4 h-4 text-accent-300" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
              </svg>
            </div>
            <span>AI 人脸识别与比对</span>
          </div>
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 bg-accent-500/20 rounded-lg flex items-center justify-center">
              <svg class="w-4 h-4 text-accent-300" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
              </svg>
            </div>
            <span>WebSocket 实时推送</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧登录区 -->
    <div class="flex-1 flex items-center justify-center p-8 bg-primary-50">
      <div class="w-full max-w-md">
        <!-- 移动端 Logo -->
        <div class="lg:hidden text-center mb-8">
          <div class="w-14 h-14 bg-primary-700 rounded-xl flex items-center justify-center mx-auto mb-4">
            <span class="text-white font-bold text-xl">V</span>
          </div>
          <h1 class="text-2xl font-bold text-primary-900">视频监控报警系统</h1>
        </div>

        <!-- 登录卡片 -->
        <div class="card p-8">
          <div class="text-center mb-8">
            <h2 class="text-2xl font-bold text-primary-900">欢迎回来</h2>
            <p class="text-primary-500 mt-2">请登录您的账户</p>
          </div>

          <!-- 错误提示 -->
          <div 
            v-if="error" 
            class="mb-6 p-4 bg-danger-50 border border-danger-200 rounded-lg text-danger-700 text-sm"
          >
            {{ error }}
          </div>

          <!-- 登录表单 -->
          <form @submit.prevent="handleSubmit" class="space-y-5">
            <!-- 用户名 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1.5">
                用户名
              </label>
              <input
                v-model="username"
                type="text"
                placeholder="请输入用户名"
                class="input"
                :disabled="loading"
                autocomplete="username"
              />
            </div>

            <!-- 密码 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1.5">
                密码
              </label>
              <div class="relative">
                <input
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="请输入密码"
                  class="input pr-10"
                  :disabled="loading"
                  autocomplete="current-password"
                />
                <button
                  type="button"
                  @click="showPassword = !showPassword"
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-primary-400 hover:text-primary-600"
                >
                  <svg v-if="showPassword" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                  <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- 登录按钮 -->
            <button
              type="submit"
              class="btn-primary w-full py-3"
              :disabled="loading"
            >
              <svg v-if="loading" class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>{{ loading ? '登录中...' : '登录' }}</span>
            </button>
          </form>

          <!-- 提示信息 -->
          <div class="mt-6 text-center text-sm text-primary-500">
            <p>默认账户：admin / admin123</p>
          </div>
        </div>

        <!-- 版权信息 -->
        <p class="text-center text-sm text-primary-400 mt-6">
          © 2026 Video Warning System. All rights reserved.
        </p>
      </div>
    </div>
  </div>
</template>
