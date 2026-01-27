/**
 * 认证状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'
import { authApi } from '@/api'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const loading = ref(false)

  // 计算属性
  const isLoggedIn = computed(() => !!accessToken.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const username = computed(() => user.value?.username || '')

  // 初始化 - 从本地存储恢复
  const init = () => {
    const storedToken = localStorage.getItem('access_token')
    const storedRefresh = localStorage.getItem('refresh_token')
    const storedUser = localStorage.getItem('user')

    if (storedToken) {
      accessToken.value = storedToken
    }
    if (storedRefresh) {
      refreshToken.value = storedRefresh
    }
    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser)
      } catch {
        user.value = null
      }
    }
  }

  // 登录
  const login = async (username: string, password: string) => {
    loading.value = true
    try {
      const response = await authApi.login({ username, password })
      
      // 保存 token
      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)

      // 获取用户信息
      const userInfo = await authApi.getCurrentUser()
      user.value = userInfo
      localStorage.setItem('user', JSON.stringify(userInfo))

      // 跳转到首页
      router.push('/')
      
      return true
    } catch (error: any) {
      console.error('Login failed:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 登出
  const logout = async () => {
    try {
      await authApi.logout()
    } catch {
      // 忽略登出 API 错误
    } finally {
      // 清除状态
      user.value = null
      accessToken.value = null
      refreshToken.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      
      // 跳转到登录页
      router.push('/login')
    }
  }

  // 刷新用户信息
  const refreshUser = async () => {
    if (!accessToken.value) return
    
    try {
      const userInfo = await authApi.getCurrentUser()
      user.value = userInfo
      localStorage.setItem('user', JSON.stringify(userInfo))
    } catch {
      // Token 无效，登出
      await logout()
    }
  }

  // 修改密码
  const changePassword = async (oldPassword: string, newPassword: string) => {
    await authApi.changePassword(oldPassword, newPassword)
  }

  return {
    // 状态
    user,
    accessToken,
    loading,
    // 计算属性
    isLoggedIn,
    isAdmin,
    username,
    // 方法
    init,
    login,
    logout,
    refreshUser,
    changePassword,
  }
})
