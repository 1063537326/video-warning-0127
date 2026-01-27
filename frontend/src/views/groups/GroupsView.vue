<script setup lang="ts">
/**
 * 人员分组管理页面
 * 
 * 管理人员分组的增删改查、颜色标签、报警配置。
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { groupApi } from '@/api'
import type { PersonGroup, PaginatedResponse } from '@/types'

// ============ 数据状态 ============

const loading = ref(false)
const groups = ref<PersonGroup[]>([])
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 0
})
const keyword = ref('')
const alertFilter = ref<'' | 'true' | 'false'>('')

// ============ 弹窗状态 ============

const showFormModal = ref(false)
const showDeleteModal = ref(false)
const isEditing = ref(false)
const currentGroup = ref<PersonGroup | null>(null)
const formData = reactive({
  name: '',
  description: '',
  color: '#3B82F6',
  alert_enabled: true,
  alert_priority: 1,
  sort_order: 0
})
const submitting = ref(false)
const formError = ref('')

// 预设颜色
const presetColors = [
  '#3B82F6', // 蓝色
  '#10B981', // 绿色
  '#F59E0B', // 橙色
  '#EF4444', // 红色
  '#8B5CF6', // 紫色
  '#EC4899', // 粉色
  '#6366F1', // 靛蓝
  '#14B8A6', // 青色
  '#F97316', // 深橙
  '#64748B', // 灰色
]

// ============ 方法 ============

/**
 * 加载分组列表
 */
const loadGroups = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (keyword.value) params.keyword = keyword.value
    if (alertFilter.value) params.alert_enabled = alertFilter.value === 'true'

    const res: PaginatedResponse<PersonGroup> = await groupApi.getList(params)
    groups.value = res.items
    pagination.total = res.total
    pagination.totalPages = res.total_pages
  } catch (error: any) {
    console.error('加载分组列表失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 搜索
 */
const handleSearch = () => {
  pagination.page = 1
  loadGroups()
}

/**
 * 切换页码
 */
const handlePageChange = (page: number) => {
  pagination.page = page
  loadGroups()
}

/**
 * 打开新增弹窗
 */
const openCreateModal = () => {
  isEditing.value = false
  currentGroup.value = null
  Object.assign(formData, {
    name: '',
    description: '',
    color: '#3B82F6',
    alert_enabled: true,
    alert_priority: 1,
    sort_order: 0
  })
  formError.value = ''
  showFormModal.value = true
}

/**
 * 打开编辑弹窗
 */
const openEditModal = (group: PersonGroup) => {
  isEditing.value = true
  currentGroup.value = group
  Object.assign(formData, {
    name: group.name,
    description: group.description || '',
    color: group.color || '#3B82F6',
    alert_enabled: group.alert_enabled,
    alert_priority: group.alert_priority,
    sort_order: group.sort_order
  })
  formError.value = ''
  showFormModal.value = true
}

/**
 * 提交表单
 */
const handleSubmit = async () => {
  if (!formData.name.trim()) {
    formError.value = '请输入分组名称'
    return
  }

  submitting.value = true
  formError.value = ''

  try {
    const data = {
      name: formData.name.trim(),
      description: formData.description.trim() || undefined,
      color: formData.color,
      alert_enabled: formData.alert_enabled,
      alert_priority: formData.alert_priority,
      sort_order: formData.sort_order
    }

    if (isEditing.value && currentGroup.value) {
      await groupApi.update(currentGroup.value.id, data)
    } else {
      await groupApi.create(data)
    }

    showFormModal.value = false
    loadGroups()
  } catch (error: any) {
    formError.value = error.response?.data?.detail || '操作失败，请重试'
  } finally {
    submitting.value = false
  }
}

/**
 * 打开删除确认弹窗
 */
const openDeleteModal = (group: PersonGroup) => {
  currentGroup.value = group
  showDeleteModal.value = true
}

/**
 * 确认删除
 */
const handleDelete = async () => {
  if (!currentGroup.value) return

  submitting.value = true
  try {
    await groupApi.delete(currentGroup.value.id)
    showDeleteModal.value = false
    loadGroups()
  } catch (error: any) {
    alert(error.response?.data?.detail || '删除失败，请重试')
  } finally {
    submitting.value = false
  }
}

/**
 * 切换报警状态
 */
const handleToggleAlert = async (group: PersonGroup) => {
  try {
    await groupApi.toggleAlert(group.id, !group.alert_enabled)
    loadGroups()
  } catch (error: any) {
    alert(error.response?.data?.detail || '操作失败')
  }
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
  loadGroups()
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-primary-900 dark:text-primary-100">人员分组</h2>
        <p class="text-primary-500 dark:text-primary-400 mt-1">管理人员分组（员工、访客、VIP、黑名单等）</p>
      </div>
      <button @click="openCreateModal" class="btn-primary">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        新增分组
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
              placeholder="搜索分组名称..."
              class="input"
              @keyup.enter="handleSearch"
            />
          </div>
          <div class="w-40">
            <select v-model="alertFilter" class="input" @change="handleSearch">
              <option value="">全部</option>
              <option value="true">触发报警</option>
              <option value="false">不触发报警</option>
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

    <!-- 分组列表 -->
    <div class="card">
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="flex items-center gap-3 text-primary-500 dark:text-primary-400">
          <svg class="animate-spin w-6 h-6" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span>加载中...</span>
        </div>
      </div>

      <template v-else>
        <div v-if="groups.length === 0" class="text-center py-20">
          <svg class="w-16 h-16 mx-auto text-primary-300 dark:text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <p class="mt-4 text-primary-500 dark:text-primary-400">暂无分组数据</p>
          <button @click="openCreateModal" class="btn-primary mt-4">新增第一个分组</button>
        </div>

        <!-- 卡片网格展示 -->
        <div v-else class="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="group in groups"
            :key="group.id"
            class="bg-white dark:bg-primary-800/50 border border-primary-100 dark:border-primary-700 rounded-xl p-4 hover:shadow-md dark:hover:shadow-lg dark:hover:shadow-black/20 transition-shadow"
          >
            <!-- 头部 -->
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-3">
                <div
                  class="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold"
                  :style="{ backgroundColor: group.color || '#3B82F6' }"
                >
                  {{ group.name.charAt(0) }}
                </div>
                <div>
                  <h4 class="font-semibold text-primary-900 dark:text-primary-100">{{ group.name }}</h4>
                  <p class="text-xs text-primary-400 dark:text-primary-500">{{ group.person_count }} 人</p>
                </div>
              </div>
              <!-- 操作菜单 -->
              <div class="flex items-center gap-1">
                <button 
                  @click="openEditModal(group)" 
                  class="p-1.5 text-primary-400 hover:text-accent-600 hover:bg-primary-50 dark:hover:bg-primary-700 rounded"
                  title="编辑"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button 
                  @click="openDeleteModal(group)" 
                  class="p-1.5 text-primary-400 hover:text-danger-600 hover:bg-danger-50 dark:hover:bg-danger-900/30 rounded"
                  title="删除"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- 描述 -->
            <p v-if="group.description" class="text-sm text-primary-500 dark:text-primary-400 mt-3 line-clamp-2">
              {{ group.description }}
            </p>

            <!-- 底部信息 -->
            <div class="flex items-center justify-between mt-4 pt-3 border-t border-primary-100 dark:border-primary-700">
              <!-- 报警状态 -->
              <div class="flex items-center gap-2">
                <span class="text-xs text-primary-500 dark:text-primary-400">报警触发</span>
                <button
                  @click="handleToggleAlert(group)"
                  :class="[
                    'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                    group.alert_enabled ? 'bg-danger-500' : 'bg-primary-200 dark:bg-primary-600'
                  ]"
                >
                  <span
                    :class="[
                      'inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform',
                      group.alert_enabled ? 'translate-x-5' : 'translate-x-1'
                    ]"
                  />
                </button>
              </div>
              <!-- 优先级 -->
              <div class="flex items-center gap-1">
                <span class="text-xs text-primary-400 dark:text-primary-500">优先级:</span>
                <span :class="[
                  'text-xs font-medium px-1.5 py-0.5 rounded',
                  group.alert_priority >= 3 ? 'bg-danger-100 dark:bg-danger-900/50 text-danger-700 dark:text-danger-400' :
                  group.alert_priority === 2 ? 'bg-warning-100 dark:bg-warning-900/50 text-warning-700 dark:text-warning-400' :
                  'bg-primary-100 dark:bg-primary-700 text-primary-700 dark:text-primary-300'
                ]">
                  {{ group.alert_priority }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="pagination.totalPages > 1" class="card-footer flex items-center justify-between">
          <div class="text-sm text-primary-500 dark:text-primary-400">
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
        <div class="relative bg-white dark:bg-primary-800 rounded-xl shadow-xl w-full max-w-md mx-4 animate-fade-in">
          <div class="px-6 py-4 border-b border-primary-100 dark:border-primary-700">
            <h3 class="text-lg font-semibold text-primary-900 dark:text-primary-100">
              {{ isEditing ? '编辑分组' : '新增分组' }}
            </h3>
          </div>
          <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
            <div v-if="formError" class="p-3 bg-danger-50 dark:bg-danger-900/30 text-danger-700 dark:text-danger-400 text-sm rounded-lg">
              {{ formError }}
            </div>
            <!-- 分组名称 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-1">
                分组名称 <span class="text-danger-500">*</span>
              </label>
              <input v-model="formData.name" type="text" class="input" placeholder="如：员工、访客" />
            </div>
            <!-- 颜色选择 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">标签颜色</label>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="color in presetColors"
                  :key="color"
                  type="button"
                  @click="formData.color = color"
                  :class="[
                    'w-8 h-8 rounded-lg transition-transform',
                    formData.color === color ? 'ring-2 ring-offset-2 dark:ring-offset-primary-800 ring-primary-500 scale-110' : ''
                  ]"
                  :style="{ backgroundColor: color }"
                />
                <!-- 自定义颜色 -->
                <div class="relative">
                  <input
                    type="color"
                    v-model="formData.color"
                    class="absolute inset-0 w-8 h-8 opacity-0 cursor-pointer"
                  />
                  <div
                    class="w-8 h-8 rounded-lg border-2 border-dashed border-primary-300 dark:border-primary-600 flex items-center justify-center"
                    :style="{ backgroundColor: formData.color }"
                  >
                    <svg class="w-4 h-4 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
            <!-- 描述 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-1">描述</label>
              <textarea v-model="formData.description" class="input" rows="2" placeholder="分组描述（选填）" />
            </div>
            <!-- 报警配置 -->
            <div class="flex items-center justify-between">
              <div>
                <label class="text-sm font-medium text-primary-700 dark:text-primary-300">触发报警</label>
                <p class="text-xs text-primary-400 dark:text-primary-500">该分组人员被识别时是否触发报警</p>
              </div>
              <button
                type="button"
                @click="formData.alert_enabled = !formData.alert_enabled"
                :class="[
                  'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                  formData.alert_enabled ? 'bg-danger-500' : 'bg-primary-200 dark:bg-primary-600'
                ]"
              >
                <span
                  :class="[
                    'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                    formData.alert_enabled ? 'translate-x-6' : 'translate-x-1'
                  ]"
                />
              </button>
            </div>
            <!-- 优先级 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-1">报警优先级</label>
              <select v-model.number="formData.alert_priority" class="input">
                <option :value="1">1 - 低</option>
                <option :value="2">2 - 中</option>
                <option :value="3">3 - 高</option>
              </select>
            </div>
            <!-- 排序 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-1">排序</label>
              <input v-model.number="formData.sort_order" type="number" class="input" min="0" />
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
        <div class="relative bg-white dark:bg-primary-800 rounded-xl shadow-xl w-full max-w-sm mx-4 animate-fade-in">
          <div class="p-6 text-center">
            <div class="w-12 h-12 mx-auto bg-danger-100 dark:bg-danger-900/30 rounded-full flex items-center justify-center">
              <svg class="w-6 h-6 text-danger-600 dark:text-danger-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-primary-900 dark:text-primary-100">确认删除</h3>
            <p class="mt-2 text-primary-500 dark:text-primary-400">
              确定要删除分组「{{ currentGroup?.name }}」吗？
              <span v-if="currentGroup?.person_count" class="block text-danger-600 dark:text-danger-400 mt-1">
                该分组下有 {{ currentGroup.person_count }} 个人员！
              </span>
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
  </div>
</template>
