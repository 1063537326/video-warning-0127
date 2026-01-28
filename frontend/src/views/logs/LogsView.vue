<script setup lang="ts">
/**
 * 操作日志页面
 * 
 * 管理员功能：查询系统操作审计日志。
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { logApi } from '@/api'
import type { OperationLog, PaginatedResponse } from '@/types'

// ============ 数据状态 ============

const loading = ref(false)
const logs = ref<OperationLog[]>([])
const pagination = reactive({
  page: 1,
  pageSize: 15,
  total: 0,
  totalPages: 0
})
const keyword = ref('')
const actionTypes = ref<{ value: string; label: string }[]>([])
const targetTypes = ref<{ value: string; label: string }[]>([])
const actionFilter = ref('')
const targetFilter = ref('')

// ============ 方法 ============

/**
 * 加载日志筛选选项
 */
const loadOptions = async () => {
  try {
    const [actionRes, targetRes] = await Promise.all([
      logApi.getActionTypes(),
      logApi.getTargetTypes()
    ])
    actionTypes.value = actionRes.items
    targetTypes.value = targetRes.items
  } catch (error) {
    console.error('加载选项失败:', error)
  }
}

/**
 * 加载日志列表
 */
const loadLogs = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (keyword.value) params.keyword = keyword.value
    if (actionFilter.value) params.action = actionFilter.value
    if (targetFilter.value) params.target_type = targetFilter.value

    const res: PaginatedResponse<OperationLog> = await logApi.getList(params)
    logs.value = res.items
    pagination.total = res.total
    pagination.totalPages = res.total_pages
  } catch (error: any) {
    console.error('加载日志列表失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 搜索
 */
const handleSearch = () => {
  pagination.page = 1
  loadLogs()
}

/**
 * 切换页码
 */
const handlePageChange = (page: number) => {
  pagination.page = page
  loadLogs()
}

/**
 * 获取操作类型标签
 */
const getActionLabel = (action: string) => {
  return actionTypes.value.find(t => t.value === action)?.label || action
}

/**
 * 获取目标类型标签
 */
const getTargetLabel = (type?: string) => {
  if (!type) return '-'
  return targetTypes.value.find(t => t.value === type)?.label || type
}

/**
 * 格式化详情
 */
const formatDetails = (details: any) => {
  if (!details) return '-'
  try {
    return typeof details === 'string' ? details : JSON.stringify(details)
  } catch {
    return '-'
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
  loadOptions()
  loadLogs()
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-primary-900">操作日志</h2>
        <p class="text-primary-500 mt-1">系统操作审计与追踪记录</p>
      </div>
    </div>

    <!-- 搜索筛选 -->
    <div class="card">
      <div class="card-body">
        <div class="flex flex-wrap gap-4">
          <div class="flex-1 min-w-[200px]">
            <input
              v-model="keyword"
              type="text"
              placeholder="搜索关键词、详情..."
              class="input"
              @keyup.enter="handleSearch"
            />
          </div>
          <div class="w-40">
            <select v-model="actionFilter" class="input" @change="handleSearch">
              <option value="">全部操作类型</option>
              <option v-for="item in actionTypes" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>
          <div class="w-40">
            <select v-model="targetFilter" class="input" @change="handleSearch">
              <option value="">全部目标类型</option>
              <option v-for="item in targetTypes" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
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

    <!-- 日志列表 -->
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
        <div v-if="logs.length === 0" class="text-center py-20">
          <svg class="w-16 h-16 mx-auto text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p class="mt-4 text-primary-500">暂无相关日志记录</p>
        </div>

        <table v-else class="table">
          <thead>
            <tr>
              <th>操作时间</th>
              <th>操作员</th>
              <th>操作类型</th>
              <th>目标类型</th>
              <th>目标ID</th>
              <th>操作详情</th>
              <th>IP地址</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id">
              <td class="text-sm whitespace-nowrap">
                {{ new Date(log.created_at).toLocaleString() }}
              </td>
              <td class="font-medium text-primary-900">
                {{ log.user?.username || '未知用户' }}
              </td>
              <td>
                <span :class="[
                  'badge',
                  log.action === 'delete' ? 'badge-danger' : 
                  log.action === 'update' ? 'badge-warning' : 
                  log.action === 'create' ? 'badge-success' : 'badge-primary'
                ]">
                  {{ getActionLabel(log.action) }}
                </span>
              </td>
              <td>{{ getTargetLabel(log.target_type) || '-' }}</td>
              <td class="font-mono text-xs">{{ log.target_id || '-' }}</td>
              <td class="max-w-xs truncate" :title="formatDetails(log.details)">
                {{ formatDetails(log.details) }}
              </td>
              <td class="text-xs text-primary-500">{{ log.ip_address || '-' }}</td>
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
  </div>
</template>
