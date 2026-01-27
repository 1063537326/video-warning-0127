<script setup lang="ts">
/**
 * 用户管理页面
 * 
 * 管理员功能：用户增删改查、启用/禁用、重置密码。
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { userApi } from '@/api'
import type { User, PaginatedResponse } from '@/types'

// ============ 数据状态 ============

const loading = ref(false)
const users = ref<User[]>([])
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 0
})
const keyword = ref('')
const roleFilter = ref('')
const statusFilter = ref<'' | 'true' | 'false'>('')

// ============ 弹窗状态 ============

const showFormModal = ref(false)
const showDeleteModal = ref(false)
const showResetModal = ref(false)
const isEditing = ref(false)
const currentUser = ref<User | null>(null)
const formData = reactive({
  username: '',
  password: '',
  email: '',
  phone: '',
  role: 'operator'
})
const newPassword = ref('')
const submitting = ref(false)
const formError = ref('')

// ============ 方法 ============

/**
 * 加载用户列表
 */
const loadUsers = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (keyword.value) params.keyword = keyword.value
    if (roleFilter.value) params.role = roleFilter.value
    if (statusFilter.value) params.is_active = statusFilter.value === 'true'

    const res: PaginatedResponse<User> = await userApi.getList(params)
    users.value = res.items
    pagination.total = res.total
    pagination.totalPages = res.total_pages
  } catch (error: any) {
    console.error('加载用户列表失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 搜索
 */
const handleSearch = () => {
  pagination.page = 1
  loadUsers()
}

/**
 * 切换页码
 */
const handlePageChange = (page: number) => {
  pagination.page = page
  loadUsers()
}

/**
 * 打开新增弹窗
 */
const openCreateModal = () => {
  isEditing.value = false
  currentUser.value = null
  Object.assign(formData, {
    username: '',
    password: '',
    email: '',
    phone: '',
    role: 'operator'
  })
  formError.value = ''
  showFormModal.value = true
}

/**
 * 打开编辑弹窗
 */
const openEditModal = (user: User) => {
  isEditing.value = true
  currentUser.value = user
  Object.assign(formData, {
    username: user.username,
    password: '',
    email: user.email || '',
    phone: user.phone || '',
    role: user.role
  })
  formError.value = ''
  showFormModal.value = true
}

/**
 * 提交表单
 */
const handleSubmit = async () => {
  if (!formData.username.trim()) {
    formError.value = '请输入用户名'
    return
  }
  if (!isEditing.value && !formData.password) {
    formError.value = '请输入密码'
    return
  }
  if (!isEditing.value && formData.password.length < 6) {
    formError.value = '密码长度不能少于6位'
    return
  }

  submitting.value = true
  formError.value = ''

  try {
    if (isEditing.value && currentUser.value) {
      const data: any = {
        email: formData.email.trim() || undefined,
        phone: formData.phone.trim() || undefined,
        role: formData.role
      }
      await userApi.update(currentUser.value.id, data)
    } else {
      await userApi.create({
        username: formData.username.trim(),
        password: formData.password,
        email: formData.email.trim() || undefined,
        phone: formData.phone.trim() || undefined,
        role: formData.role
      })
    }

    showFormModal.value = false
    loadUsers()
  } catch (error: any) {
    formError.value = error.response?.data?.detail || '操作失败，请重试'
  } finally {
    submitting.value = false
  }
}

/**
 * 打开删除确认弹窗
 */
const openDeleteModal = (user: User) => {
  currentUser.value = user
  showDeleteModal.value = true
}

/**
 * 确认删除
 */
const handleDelete = async () => {
  if (!currentUser.value) return

  submitting.value = true
  try {
    await userApi.delete(currentUser.value.id)
    showDeleteModal.value = false
    loadUsers()
  } catch (error: any) {
    alert(error.response?.data?.detail || '删除失败，请重试')
  } finally {
    submitting.value = false
  }
}

/**
 * 切换用户状态
 */
const handleToggleStatus = async (user: User) => {
  try {
    await userApi.toggleStatus(user.id, !user.is_active)
    loadUsers()
  } catch (error: any) {
    alert(error.response?.data?.detail || '操作失败')
  }
}

/**
 * 打开重置密码弹窗
 */
const openResetModal = (user: User) => {
  currentUser.value = user
  newPassword.value = ''
  showResetModal.value = true
}

/**
 * 重置密码
 */
const handleResetPassword = async () => {
  if (!currentUser.value) return
  if (!newPassword.value || newPassword.value.length < 6) {
    alert('新密码长度不能少于6位')
    return
  }

  submitting.value = true
  try {
    await userApi.resetPassword(currentUser.value.id, newPassword.value)
    showResetModal.value = false
    alert('密码重置成功')
  } catch (error: any) {
    alert(error.response?.data?.detail || '重置密码失败')
  } finally {
    submitting.value = false
  }
}

/**
 * 获取角色标签
 */
const getRoleLabel = (role: string) => {
  return role === 'admin' ? '管理员' : '操作员'
}

/**
 * 分页范围
 */
const pageRange = computed(() => {
  const range: number[] = []
  const start = Math.max(1, pagination.page - 2)
  const end = Math.min(pagination.totalPages, pagination.page + 2)
  for (let i = start; i <= end; i++) {
    range.push(i)
  }
  return range
})

// ============ 生命周期 ============

onMounted(() => {
  loadUsers()
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-primary-900">用户管理</h2>
        <p class="text-primary-500 mt-1">管理系统用户账户</p>
      </div>
      <button @click="openCreateModal" class="btn-primary">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        新增用户
      </button>
    </div>

    <!-- 搜索筛选 -->
    <div class="card">
      <div class="card-body">
        <div class="flex flex-wrap gap-4">
          <div class="flex-1 min-w-[200px]">
            <input
              v-model="keyword"
              type="text"
              placeholder="搜索用户名、邮箱..."
              class="input"
              @keyup.enter="handleSearch"
            />
          </div>
          <div class="w-32">
            <select v-model="roleFilter" class="input" @change="handleSearch">
              <option value="">全部角色</option>
              <option value="admin">管理员</option>
              <option value="operator">操作员</option>
            </select>
          </div>
          <div class="w-32">
            <select v-model="statusFilter" class="input" @change="handleSearch">
              <option value="">全部状态</option>
              <option value="true">启用</option>
              <option value="false">禁用</option>
            </select>
          </div>
          <button @click="handleSearch" class="btn-secondary">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            搜索
          </button>
        </div>
      </div>
    </div>

    <!-- 用户列表 -->
    <div class="card">
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="flex items-center gap-3 text-primary-500">
          <svg class="animate-spin w-6 h-6" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span>加载中...</span>
        </div>
      </div>

      <template v-else>
        <div v-if="users.length === 0" class="text-center py-20">
          <svg class="w-16 h-16 mx-auto text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
          <p class="mt-4 text-primary-500">暂无用户数据</p>
          <button @click="openCreateModal" class="btn-primary mt-4">新增第一个用户</button>
        </div>

        <table v-else class="table">
          <thead>
            <tr>
              <th>用户名</th>
              <th>邮箱</th>
              <th>电话</th>
              <th>角色</th>
              <th>状态</th>
              <th>最后登录</th>
              <th>创建时间</th>
              <th class="w-44">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                    <span class="text-sm font-medium text-primary-600">
                      {{ user.username.charAt(0).toUpperCase() }}
                    </span>
                  </div>
                  <span class="font-medium text-primary-900">{{ user.username }}</span>
                </div>
              </td>
              <td>{{ user.email || '-' }}</td>
              <td>{{ user.phone || '-' }}</td>
              <td>
                <span :class="[
                  'badge',
                  user.role === 'admin' ? 'badge-accent' : 'badge-primary'
                ]">
                  {{ getRoleLabel(user.role) }}
                </span>
              </td>
              <td>
                <span :class="[
                  'badge',
                  user.is_active ? 'badge-success' : 'badge-danger'
                ]">
                  {{ user.is_active ? '启用' : '禁用' }}
                </span>
              </td>
              <td class="text-sm text-primary-500">
                {{ user.last_login_at ? new Date(user.last_login_at).toLocaleString() : '从未登录' }}
              </td>
              <td class="text-sm text-primary-500">
                {{ new Date(user.created_at).toLocaleDateString() }}
              </td>
              <td>
                <div class="flex items-center gap-2">
                  <button 
                    @click="openEditModal(user)" 
                    class="text-accent-600 hover:text-accent-700"
                    title="编辑"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button 
                    @click="openResetModal(user)" 
                    class="text-warning-600 hover:text-warning-700"
                    title="重置密码"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                    </svg>
                  </button>
                  <!-- admin 用户不能被禁用 -->
                  <button 
                    v-if="user.username !== 'admin'"
                    @click="handleToggleStatus(user)" 
                    :class="user.is_active ? 'text-primary-400 hover:text-primary-600' : 'text-success-600 hover:text-success-700'"
                    :title="user.is_active ? '禁用' : '启用'"
                  >
                    <svg v-if="user.is_active" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                    <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </button>
                  <span v-else class="text-primary-300 cursor-not-allowed" title="admin 用户不能被禁用">
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </span>
                  <!-- admin 用户不能被删除 -->
                  <button 
                    v-if="user.username !== 'admin'"
                    @click="openDeleteModal(user)" 
                    class="text-danger-600 hover:text-danger-700"
                    title="删除"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                  <span v-else class="text-primary-300 cursor-not-allowed" title="admin 用户不能被删除">
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 分页 -->
        <div v-if="pagination.totalPages > 1" class="card-footer flex items-center justify-between">
          <div class="text-sm text-primary-500">
            共 {{ pagination.total }} 条记录，第 {{ pagination.page }}/{{ pagination.totalPages }} 页
          </div>
          <div class="flex items-center gap-1">
            <button
              :disabled="pagination.page === 1"
              @click="handlePageChange(pagination.page - 1)"
              class="btn-ghost btn-sm"
            >上一页</button>
            <button
              v-for="p in pageRange"
              :key="p"
              @click="handlePageChange(p)"
              :class="['btn-sm', p === pagination.page ? 'btn-primary' : 'btn-ghost']"
            >{{ p }}</button>
            <button
              :disabled="pagination.page === pagination.totalPages"
              @click="handlePageChange(pagination.page + 1)"
              class="btn-ghost btn-sm"
            >下一页</button>
          </div>
        </div>
      </template>
    </div>

    <!-- 新增/编辑弹窗 -->
    <Teleport to="body">
      <div v-if="showFormModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showFormModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 animate-fade-in">
          <div class="px-6 py-4 border-b border-primary-100">
            <h3 class="text-lg font-semibold text-primary-900">
              {{ isEditing ? '编辑用户' : '新增用户' }}
            </h3>
          </div>
          <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
            <div v-if="formError" class="p-3 bg-danger-50 text-danger-700 text-sm rounded-lg">
              {{ formError }}
            </div>
            <!-- 用户名 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">
                用户名 <span class="text-danger-500">*</span>
              </label>
              <input 
                v-model="formData.username" 
                type="text" 
                class="input" 
                :disabled="isEditing"
                placeholder="请输入用户名" 
              />
            </div>
            <!-- 密码（新增时必填） -->
            <div v-if="!isEditing">
              <label class="block text-sm font-medium text-primary-700 mb-1">
                密码 <span class="text-danger-500">*</span>
              </label>
              <input v-model="formData.password" type="password" class="input" placeholder="请输入密码（至少6位）" />
            </div>
            <!-- 邮箱 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">邮箱</label>
              <input v-model="formData.email" type="email" class="input" placeholder="选填" />
            </div>
            <!-- 电话 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">电话</label>
              <input v-model="formData.phone" type="text" class="input" placeholder="选填" />
            </div>
            <!-- 角色 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">角色</label>
              <select v-model="formData.role" class="input">
                <option value="operator">操作员</option>
                <option value="admin">管理员</option>
              </select>
            </div>
            <!-- 按钮 -->
            <div class="flex justify-end gap-3 pt-4">
              <button type="button" @click="showFormModal = false" class="btn-secondary">取消</button>
              <button type="submit" :disabled="submitting" class="btn-primary">
                {{ submitting ? '提交中...' : (isEditing ? '保存' : '创建') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- 删除确认弹窗 -->
    <Teleport to="body">
      <div v-if="showDeleteModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showDeleteModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 animate-fade-in">
          <div class="p-6 text-center">
            <div class="w-12 h-12 mx-auto bg-danger-100 rounded-full flex items-center justify-center">
              <svg class="w-6 h-6 text-danger-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-primary-900">确认删除</h3>
            <p class="mt-2 text-primary-500">
              确定要删除用户「{{ currentUser?.username }}」吗？此操作不可撤销。
            </p>
            <div class="flex justify-center gap-3 mt-6">
              <button @click="showDeleteModal = false" class="btn-secondary">取消</button>
              <button @click="handleDelete" :disabled="submitting" class="btn-danger">
                {{ submitting ? '删除中...' : '确认删除' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 重置密码弹窗 -->
    <Teleport to="body">
      <div v-if="showResetModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showResetModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 animate-fade-in">
          <div class="px-6 py-4 border-b border-primary-100">
            <h3 class="text-lg font-semibold text-primary-900">重置密码</h3>
          </div>
          <div class="p-6">
            <p class="text-primary-600 mb-4">
              为用户「<strong>{{ currentUser?.username }}</strong>」设置新密码
            </p>
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">新密码</label>
              <input v-model="newPassword" type="password" class="input" placeholder="请输入新密码（至少6位）" />
            </div>
            <div class="flex justify-end gap-3 mt-6">
              <button @click="showResetModal = false" class="btn-secondary">取消</button>
              <button @click="handleResetPassword" :disabled="submitting" class="btn-primary">
                {{ submitting ? '提交中...' : '确认重置' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
