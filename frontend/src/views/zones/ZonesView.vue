<script setup lang="ts">
/**
 * 区域管理页面
 * 
 * 管理摄像头区域（楼栋/楼层）的增删改查。
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { zoneApi } from '@/api'
import type { Zone, PaginatedResponse } from '@/types'

// ============ 数据状态 ============

/** 加载状态 */
const loading = ref(false)
/** 区域列表 */
const zones = ref<Zone[]>([])
/** 分页信息 */
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 0
})
/** 搜索关键词 */
const keyword = ref('')
/** 楼栋筛选 */
const buildingFilter = ref('')
/** 楼栋列表（用于筛选） */
const buildings = ref<string[]>([])

// ============ 弹窗状态 ============

/** 表单弹窗 */
const showFormModal = ref(false)
/** 删除确认弹窗 */
const showDeleteModal = ref(false)
/** 编辑模式 */
const isEditing = ref(false)
/** 当前编辑的区域 */
const currentZone = ref<Zone | null>(null)
/** 表单数据 */
const formData = reactive({
  name: '',
  description: '',
  building: '',
  floor: '',
  sort_order: 0
})
/** 表单提交中 */
const submitting = ref(false)
/** 表单错误 */
const formError = ref('')

// ============ 方法 ============

/**
 * 加载区域列表
 */
const loadZones = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (keyword.value) params.keyword = keyword.value
    if (buildingFilter.value) params.building = buildingFilter.value

    const res: PaginatedResponse<Zone> = await zoneApi.getList(params)
    zones.value = res.items
    pagination.total = res.total
    pagination.totalPages = res.total_pages

    // 提取楼栋列表
    const allBuildings = new Set<string>()
    res.items.forEach(z => {
      if (z.building) allBuildings.add(z.building)
    })
    buildings.value = Array.from(allBuildings).sort()
  } catch (error: any) {
    console.error('加载区域列表失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 搜索（重置到第一页）
 */
const handleSearch = () => {
  pagination.page = 1
  loadZones()
}

/**
 * 切换页码
 */
const handlePageChange = (page: number) => {
  pagination.page = page
  loadZones()
}

/**
 * 打开新增弹窗
 */
const openCreateModal = () => {
  isEditing.value = false
  currentZone.value = null
  Object.assign(formData, {
    name: '',
    description: '',
    building: '',
    floor: '',
    sort_order: 0
  })
  formError.value = ''
  showFormModal.value = true
}

/**
 * 打开编辑弹窗
 */
const openEditModal = (zone: Zone) => {
  isEditing.value = true
  currentZone.value = zone
  Object.assign(formData, {
    name: zone.name,
    description: zone.description || '',
    building: zone.building || '',
    floor: zone.floor || '',
    sort_order: zone.sort_order
  })
  formError.value = ''
  showFormModal.value = true
}

/**
 * 提交表单
 */
const handleSubmit = async () => {
  // 验证
  if (!formData.name.trim()) {
    formError.value = '请输入区域名称'
    return
  }

  submitting.value = true
  formError.value = ''

  try {
    const data = {
      name: formData.name.trim(),
      description: formData.description.trim() || undefined,
      building: formData.building.trim() || undefined,
      floor: formData.floor.trim() || undefined,
      sort_order: formData.sort_order
    }

    if (isEditing.value && currentZone.value) {
      await zoneApi.update(currentZone.value.id, data)
    } else {
      await zoneApi.create(data)
    }

    showFormModal.value = false
    loadZones()
  } catch (error: any) {
    formError.value = error.response?.data?.detail || '操作失败，请重试'
  } finally {
    submitting.value = false
  }
}

/**
 * 打开删除确认弹窗
 */
const openDeleteModal = (zone: Zone) => {
  currentZone.value = zone
  showDeleteModal.value = true
}

/**
 * 确认删除
 */
const handleDelete = async () => {
  if (!currentZone.value) return

  submitting.value = true
  try {
    await zoneApi.delete(currentZone.value.id)
    showDeleteModal.value = false
    loadZones()
  } catch (error: any) {
    alert(error.response?.data?.detail || '删除失败，请重试')
  } finally {
    submitting.value = false
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
  loadZones()
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-primary-900">区域管理</h2>
        <p class="text-primary-500 mt-1">管理摄像头所属的区域（楼栋/楼层）</p>
      </div>
      <button @click="openCreateModal" class="btn-primary">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        新增区域
      </button>
    </div>

    <!-- 搜索筛选 -->
    <div class="card">
      <div class="card-body">
        <div class="flex flex-wrap gap-4">
          <!-- 关键词搜索 -->
          <div class="flex-1 min-w-[200px]">
            <input
              v-model="keyword"
              type="text"
              placeholder="搜索区域名称..."
              class="input"
              @keyup.enter="handleSearch"
            />
          </div>
          <!-- 楼栋筛选 -->
          <div class="w-40">
            <select v-model="buildingFilter" class="input" @change="handleSearch">
              <option value="">全部楼栋</option>
              <option v-for="b in buildings" :key="b" :value="b">{{ b }}</option>
            </select>
          </div>
          <!-- 搜索按钮 -->
          <button @click="handleSearch" class="btn-secondary">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            搜索
          </button>
        </div>
      </div>
    </div>

    <!-- 区域列表 -->
    <div class="card">
      <!-- 加载状态 -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="flex items-center gap-3 text-primary-500">
          <svg class="animate-spin w-6 h-6" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span>加载中...</span>
        </div>
      </div>

      <!-- 列表内容 -->
      <template v-else>
        <!-- 空状态 -->
        <div v-if="zones.length === 0" class="text-center py-20">
          <svg class="w-16 h-16 mx-auto text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <p class="mt-4 text-primary-500">暂无区域数据</p>
          <button @click="openCreateModal" class="btn-primary mt-4">
            新增第一个区域
          </button>
        </div>

        <!-- 表格 -->
        <table v-else class="table">
          <thead>
            <tr>
              <th>区域名称</th>
              <th>楼栋</th>
              <th>楼层</th>
              <th>摄像头数量</th>
              <th>排序</th>
              <th>创建时间</th>
              <th class="w-32">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="zone in zones" :key="zone.id">
              <td>
                <div class="font-medium text-primary-900">{{ zone.name }}</div>
                <div v-if="zone.description" class="text-xs text-primary-400 mt-0.5">{{ zone.description }}</div>
              </td>
              <td>{{ zone.building || '-' }}</td>
              <td>{{ zone.floor || '-' }}</td>
              <td>
                <span class="badge-primary">{{ zone.camera_count }}</span>
              </td>
              <td>{{ zone.sort_order }}</td>
              <td class="text-primary-500 text-sm">
                {{ new Date(zone.created_at).toLocaleDateString() }}
              </td>
              <td>
                <div class="flex items-center gap-2">
                  <button 
                    @click="openEditModal(zone)" 
                    class="text-accent-600 hover:text-accent-700"
                    title="编辑"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button 
                    @click="openDeleteModal(zone)" 
                    class="text-danger-600 hover:text-danger-700"
                    title="删除"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
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
            >
              上一页
            </button>
            <button
              v-for="p in pageRange"
              :key="p"
              @click="handlePageChange(p)"
              :class="['btn-sm', p === pagination.page ? 'btn-primary' : 'btn-ghost']"
            >
              {{ p }}
            </button>
            <button
              :disabled="pagination.page === pagination.totalPages"
              @click="handlePageChange(pagination.page + 1)"
              class="btn-ghost btn-sm"
            >
              下一页
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- 新增/编辑弹窗 -->
    <Teleport to="body">
      <div v-if="showFormModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- 遮罩 -->
        <div class="absolute inset-0 bg-black/50" @click="showFormModal = false" />
        <!-- 弹窗内容 -->
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 animate-fade-in">
          <div class="px-6 py-4 border-b border-primary-100">
            <h3 class="text-lg font-semibold text-primary-900">
              {{ isEditing ? '编辑区域' : '新增区域' }}
            </h3>
          </div>
          <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
            <!-- 错误提示 -->
            <div v-if="formError" class="p-3 bg-danger-50 text-danger-700 text-sm rounded-lg">
              {{ formError }}
            </div>
            <!-- 区域名称 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">
                区域名称 <span class="text-danger-500">*</span>
              </label>
              <input v-model="formData.name" type="text" class="input" placeholder="如：大堂入口" />
            </div>
            <!-- 楼栋 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">楼栋</label>
              <input v-model="formData.building" type="text" class="input" placeholder="如：A栋" />
            </div>
            <!-- 楼层 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">楼层</label>
              <input v-model="formData.floor" type="text" class="input" placeholder="如：1F" />
            </div>
            <!-- 描述 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">描述</label>
              <textarea v-model="formData.description" class="input" rows="2" placeholder="区域描述（选填）" />
            </div>
            <!-- 排序 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">排序</label>
              <input v-model.number="formData.sort_order" type="number" class="input" min="0" />
            </div>
            <!-- 按钮 -->
            <div class="flex justify-end gap-3 pt-4">
              <button type="button" @click="showFormModal = false" class="btn-secondary">
                取消
              </button>
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
        <!-- 遮罩 -->
        <div class="absolute inset-0 bg-black/50" @click="showDeleteModal = false" />
        <!-- 弹窗内容 -->
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 animate-fade-in">
          <div class="p-6 text-center">
            <div class="w-12 h-12 mx-auto bg-danger-100 rounded-full flex items-center justify-center">
              <svg class="w-6 h-6 text-danger-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-primary-900">确认删除</h3>
            <p class="mt-2 text-primary-500">
              确定要删除区域「{{ currentZone?.name }}」吗？
              <span v-if="currentZone?.camera_count" class="block text-danger-600 mt-1">
                该区域下有 {{ currentZone.camera_count }} 个摄像头！
              </span>
            </p>
            <div class="flex justify-center gap-3 mt-6">
              <button @click="showDeleteModal = false" class="btn-secondary">
                取消
              </button>
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
