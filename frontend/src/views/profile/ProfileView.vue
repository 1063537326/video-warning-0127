<script setup lang="ts">
/**
 * 个人中心页面
 * 
 * 查看个人信息、修改密码。
 */
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api'

const authStore = useAuthStore()

// ============ 数据状态 ============

const user = computed(() => authStore.user)

// 修改密码
const showPasswordModal = ref(false)
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const submitting = ref(false)
const formError = ref('')

// ============ 方法 ============

/**
 * 打开修改密码弹窗
 */
const openPasswordModal = () => {
  passwordForm.value = {
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
  formError.value = ''
  showPasswordModal.value = true
}

/**
 * 修改密码
 */
const handleChangePassword = async () => {
  const { oldPassword, newPassword, confirmPassword } = passwordForm.value

  // 验证
  if (!oldPassword) {
    formError.value = '请输入当前密码'
    return
  }
  if (!newPassword) {
    formError.value = '请输入新密码'
    return
  }
  if (newPassword.length < 6) {
    formError.value = '新密码长度不能少于6位'
    return
  }
  if (newPassword !== confirmPassword) {
    formError.value = '两次输入的密码不一致'
    return
  }

  submitting.value = true
  formError.value = ''

  try {
    await authApi.changePassword(oldPassword, newPassword)
    showPasswordModal.value = false
    alert('密码修改成功，请重新登录')
    authStore.logout()
  } catch (error: any) {
    formError.value = error.response?.data?.detail || '修改失败，请检查当前密码是否正确'
  } finally {
    submitting.value = false
  }
}

/**
 * 获取角色标签
 */
const getRoleLabel = (role?: string) => {
  return role === 'admin' ? '管理员' : '操作员'
}

/**
 * 格式化日期
 */
const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="max-w-2xl mx-auto space-y-6 animate-fade-in">
    <!-- 页面标题 -->
    <div>
      <h2 class="text-2xl font-bold text-primary-900">个人中心</h2>
      <p class="text-primary-500 mt-1">查看和管理您的账户信息</p>
    </div>

    <!-- 用户头像和基本信息 -->
    <div class="card">
      <div class="card-body">
        <div class="flex items-center gap-6">
          <!-- 头像 -->
          <div class="w-20 h-20 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
            <span class="text-3xl font-bold text-white">
              {{ user?.username?.charAt(0).toUpperCase() || 'U' }}
            </span>
          </div>
          <!-- 信息 -->
          <div class="flex-1">
            <h3 class="text-xl font-semibold text-primary-900">{{ user?.username }}</h3>
            <p class="text-primary-500 mt-1">{{ user?.email || '未设置邮箱' }}</p>
            <span :class="[
              'inline-flex items-center gap-1 mt-2 px-2.5 py-1 rounded-full text-xs font-medium',
              user?.role === 'admin' ? 'bg-accent-100 text-accent-700' : 'bg-primary-100 text-primary-700'
            ]">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              {{ getRoleLabel(user?.role) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 详细信息 -->
    <div class="card">
      <div class="card-header">
        <h3 class="font-semibold text-primary-900">账户信息</h3>
      </div>
      <div class="card-body space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-primary-500 mb-1">用户名</label>
            <p class="font-medium text-primary-900">{{ user?.username }}</p>
          </div>
          <div>
            <label class="block text-sm text-primary-500 mb-1">角色</label>
            <p class="font-medium text-primary-900">{{ getRoleLabel(user?.role) }}</p>
          </div>
          <div>
            <label class="block text-sm text-primary-500 mb-1">邮箱</label>
            <p class="font-medium text-primary-900">{{ user?.email || '未设置' }}</p>
          </div>
          <div>
            <label class="block text-sm text-primary-500 mb-1">电话</label>
            <p class="font-medium text-primary-900">{{ user?.phone || '未设置' }}</p>
          </div>
          <div>
            <label class="block text-sm text-primary-500 mb-1">最后登录</label>
            <p class="font-medium text-primary-900">{{ formatDate(user?.last_login_at) }}</p>
          </div>
          <div>
            <label class="block text-sm text-primary-500 mb-1">注册时间</label>
            <p class="font-medium text-primary-900">{{ formatDate(user?.created_at) }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 安全设置 -->
    <div class="card">
      <div class="card-header">
        <h3 class="font-semibold text-primary-900">安全设置</h3>
      </div>
      <div class="card-body">
        <div class="flex items-center justify-between">
          <div>
            <h4 class="font-medium text-primary-900">登录密码</h4>
            <p class="text-sm text-primary-500 mt-0.5">定期修改密码可以提高账户安全性</p>
          </div>
          <button @click="openPasswordModal" class="btn-secondary">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
            修改密码
          </button>
        </div>
      </div>
    </div>

    <!-- 登录活动 -->
    <div class="card">
      <div class="card-header">
        <h3 class="font-semibold text-primary-900">账户状态</h3>
      </div>
      <div class="card-body">
        <div class="flex items-center gap-3">
          <div :class="[
            'w-3 h-3 rounded-full',
            user?.is_active ? 'bg-success-500' : 'bg-danger-500'
          ]" />
          <span class="text-primary-900">
            账户状态: {{ user?.is_active ? '正常' : '已禁用' }}
          </span>
        </div>
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <Teleport to="body">
      <div v-if="showPasswordModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showPasswordModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 animate-fade-in">
          <div class="px-6 py-4 border-b border-primary-100">
            <h3 class="text-lg font-semibold text-primary-900">修改密码</h3>
          </div>
          <form @submit.prevent="handleChangePassword" class="p-6 space-y-4">
            <div v-if="formError" class="p-3 bg-danger-50 text-danger-700 text-sm rounded-lg">
              {{ formError }}
            </div>
            <!-- 当前密码 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">
                当前密码 <span class="text-danger-500">*</span>
              </label>
              <input
                v-model="passwordForm.oldPassword"
                type="password"
                class="input"
                placeholder="请输入当前密码"
              />
            </div>
            <!-- 新密码 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">
                新密码 <span class="text-danger-500">*</span>
              </label>
              <input
                v-model="passwordForm.newPassword"
                type="password"
                class="input"
                placeholder="请输入新密码（至少6位）"
              />
            </div>
            <!-- 确认密码 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">
                确认新密码 <span class="text-danger-500">*</span>
              </label>
              <input
                v-model="passwordForm.confirmPassword"
                type="password"
                class="input"
                placeholder="请再次输入新密码"
              />
            </div>
            <!-- 按钮 -->
            <div class="flex justify-end gap-3 pt-4">
              <button type="button" @click="showPasswordModal = false" class="btn-secondary">取消</button>
              <button type="submit" :disabled="submitting" class="btn-primary">
                {{ submitting ? '提交中...' : '确认修改' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>
