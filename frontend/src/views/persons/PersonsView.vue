<script setup lang="ts">
/**
 * 人员管理页面
 * 
 * 管理已知人员的增删改查、人脸图片上传。
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { personApi, groupApi } from '@/api'
import { getStaticUrl } from '@/utils'
import type { Person, PersonGroup, FaceImage, PaginatedResponse } from '@/types'

// ============ 数据状态 ============

const loading = ref(false)
const persons = ref<Person[]>([])
const groups = ref<PersonGroup[]>([])
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 0
})
const keyword = ref('')
const groupFilter = ref<number | ''>('')
const statusFilter = ref('')

// ============ 弹窗状态 ============

const showFormModal = ref(false)
const showDeleteModal = ref(false)
const showDetailModal = ref(false)
const isEditing = ref(false)
const currentPerson = ref<(Person & { face_images?: FaceImage[] }) | null>(null)
const formData = reactive({
  name: '',
  employee_id: '',
  group_id: '' as number | '',
  department: '',
  phone: '',
  remark: ''
})
const submitting = ref(false)
const formError = ref('')

// 人脸上传
const uploadingFace = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

// ============ 方法 ============

/**
 * 加载人员列表
 */
const loadPersons = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (keyword.value) params.keyword = keyword.value
    if (groupFilter.value) params.group_id = groupFilter.value
    // 后端使用 is_active 布尔值
    if (statusFilter.value === 'active') params.is_active = true
    else if (statusFilter.value === 'inactive') params.is_active = false

    const res: PaginatedResponse<Person> = await personApi.getList(params)
    persons.value = res.items
    pagination.total = res.total
    pagination.totalPages = res.total_pages
  } catch (error: any) {
    console.error('加载人员列表失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 加载分组列表
 */
const loadGroups = async () => {
  try {
    const res = await groupApi.getAll()
    // API 返回直接数组或 { items: [...] } 格式
    groups.value = Array.isArray(res) ? res : (res.items || [])
  } catch (error) {
    console.error('加载分组列表失败:', error)
  }
}

/**
 * 搜索
 */
const handleSearch = () => {
  pagination.page = 1
  loadPersons()
}

/**
 * 切换页码
 */
const handlePageChange = (page: number) => {
  pagination.page = page
  loadPersons()
}

/**
 * 打开新增弹窗
 */
const openCreateModal = () => {
  isEditing.value = false
  currentPerson.value = null
  Object.assign(formData, {
    name: '',
    employee_id: '',
    group_id: '',
    department: '',
    phone: '',
    remark: ''
  })
  formError.value = ''
  showFormModal.value = true
}

/**
 * 打开编辑弹窗
 */
const openEditModal = (person: Person) => {
  isEditing.value = true
  currentPerson.value = person
  Object.assign(formData, {
    name: person.name,
    employee_id: person.employee_id || '',
    group_id: person.group_id || '',
    department: person.department || '',
    phone: person.phone || '',
    remark: person.remark || ''
  })
  formError.value = ''
  showFormModal.value = true
}

/**
 * 提交表单
 */
const handleSubmit = async () => {
  if (!formData.name.trim()) {
    formError.value = '请输入姓名'
    return
  }

  submitting.value = true
  formError.value = ''

  try {
    const data = {
      name: formData.name.trim(),
      employee_id: formData.employee_id.trim() || undefined,
      group_id: formData.group_id || undefined,
      department: formData.department.trim() || undefined,
      phone: formData.phone.trim() || undefined,
      remark: formData.remark.trim() || undefined
    }

    if (isEditing.value && currentPerson.value) {
      await personApi.update(currentPerson.value.id, data)
    } else {
      await personApi.create(data)
    }

    showFormModal.value = false
    loadPersons()
  } catch (error: any) {
    formError.value = error.response?.data?.detail || '操作失败，请重试'
  } finally {
    submitting.value = false
  }
}

/**
 * 打开删除确认弹窗
 */
const openDeleteModal = (person: Person) => {
  currentPerson.value = person
  showDeleteModal.value = true
}

/**
 * 确认删除
 */
const handleDelete = async () => {
  if (!currentPerson.value) return

  submitting.value = true
  try {
    await personApi.delete(currentPerson.value.id)
    showDeleteModal.value = false
    loadPersons()
  } catch (error: any) {
    alert(error.response?.data?.detail || '删除失败，请重试')
  } finally {
    submitting.value = false
  }
}

/**
 * 打开详情弹窗（含人脸管理）
 */
const openDetailModal = async (person: Person) => {
  try {
    const detail = await personApi.get(person.id)
    currentPerson.value = detail
    showDetailModal.value = true
  } catch (error: any) {
    alert('加载人员详情失败')
  }
}

/**
 * 切换人员状态
 */
const handleToggleStatus = async (person: Person) => {
  try {
    const newStatus = !person.is_active
    await personApi.updateStatus(person.id, newStatus)
    loadPersons()
  } catch (error: any) {
    alert(error.response?.data?.detail || '操作失败')
  }
}

/**
 * 触发文件选择
 */
const triggerFileInput = () => {
  fileInput.value?.click()
}

/**
 * 上传人脸图片
 */
const handleFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file || !currentPerson.value) return

  // 验证文件类型
  if (!['image/jpeg', 'image/png'].includes(file.type)) {
    alert('仅支持 JPEG/PNG 格式图片')
    return
  }

  // 验证文件大小（5MB）
  if (file.size > 5 * 1024 * 1024) {
    alert('图片大小不能超过 5MB')
    return
  }

  uploadingFace.value = true
  try {
    await personApi.uploadFace(currentPerson.value.id, file)
    // 刷新详情
    const detail = await personApi.get(currentPerson.value.id)
    currentPerson.value = detail
    loadPersons()
  } catch (error: any) {
    alert(error.response?.data?.detail || '上传失败')
  } finally {
    uploadingFace.value = false
    target.value = '' // 清空选择
  }
}

/**
 * 删除人脸图片
 */
const handleDeleteFace = async (face: FaceImage) => {
  if (!currentPerson.value) return
  if (!confirm('确定要删除这张人脸图片吗？')) return

  try {
    await personApi.deleteFace(currentPerson.value.id, face.id)
    // 刷新详情
    const detail = await personApi.get(currentPerson.value.id)
    currentPerson.value = detail
    loadPersons()
  } catch (error: any) {
    alert(error.response?.data?.detail || '删除失败')
  }
}

/**
 * 设置为主图
 */
const handleSetPrimary = async (face: FaceImage) => {
  if (!currentPerson.value || face.is_primary) return

  try {
    await personApi.setPrimaryFace(currentPerson.value.id, face.id)
    // 刷新详情
    const detail = await personApi.get(currentPerson.value.id)
    currentPerson.value = detail
    loadPersons()
  } catch (error: any) {
    alert(error.response?.data?.detail || '设置失败')
  }
}

/**
 * 获取分组名称
 */
const getGroupName = (groupId?: number) => {
  if (!groupId) return '-'
  const group = groups.value.find(g => g.id === groupId)
  return group?.name || '-'
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
  loadPersons()
  loadGroups()
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-primary-900">人员管理</h2>
        <p class="text-primary-500 mt-1">管理已知人员及其人脸信息</p>
      </div>
      <button @click="openCreateModal" class="btn-primary">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        新增人员
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
              placeholder="搜索姓名、工号..."
              class="input"
              @keyup.enter="handleSearch"
            />
          </div>
          <div class="w-40">
            <select v-model="groupFilter" class="input" @change="handleSearch">
              <option value="">全部分组</option>
              <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
            </select>
          </div>
          <div class="w-32">
            <select v-model="statusFilter" class="input" @change="handleSearch">
              <option value="">全部状态</option>
              <option value="active">在职</option>
              <option value="inactive">离职</option>
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

    <!-- 人员列表 -->
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
        <div v-if="persons.length === 0" class="text-center py-20">
          <svg class="w-16 h-16 mx-auto text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          <p class="mt-4 text-primary-500">暂无人员数据</p>
          <button @click="openCreateModal" class="btn-primary mt-4">新增第一个人员</button>
        </div>

        <table v-else class="table">
          <thead>
            <tr>
              <th>人员信息</th>
              <th>工号</th>
              <th>分组</th>
              <th>部门</th>
              <th>人脸</th>
              <th>状态</th>
              <th class="w-40">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="person in persons" :key="person.id">
              <td>
                <div class="flex items-center gap-3">
                  <!-- 头像 -->
                  <div class="w-10 h-10 rounded-full overflow-hidden bg-primary-100 flex-shrink-0">
                    <img
                      v-if="person.primary_face?.image_url"
                      :src="getStaticUrl(person.primary_face.image_url)"
                      class="w-full h-full object-cover"
                      alt=""
                    />
                    <div v-else class="w-full h-full flex items-center justify-center text-primary-400">
                      <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    </div>
                  </div>
                  <div>
                    <div class="font-medium text-primary-900">{{ person.name }}</div>
                    <div v-if="person.phone" class="text-xs text-primary-400">{{ person.phone }}</div>
                  </div>
                </div>
              </td>
              <td>{{ person.employee_id || '-' }}</td>
              <td>
                <span
                  v-if="person.group"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
                  :style="{ backgroundColor: (person.group.color || '#3B82F6') + '20', color: person.group.color || '#3B82F6' }"
                >
                  {{ person.group.name }}
                </span>
                <span v-else class="text-primary-400">-</span>
              </td>
              <td>{{ person.department || '-' }}</td>
              <td>
                <span :class="[
                  'badge',
                  person.face_count > 0 ? 'badge-success' : 'badge-warning'
                ]">
                  {{ person.face_count }} 张
                </span>
              </td>
              <td>
                <span :class="[
                  'badge',
                  person.is_active ? 'badge-success' : 'badge-primary'
                ]">
                  {{ person.is_active ? '在职' : '离职' }}
                </span>
              </td>
              <td>
                <div class="flex items-center gap-2">
                  <button 
                    @click="openDetailModal(person)" 
                    class="text-primary-600 hover:text-primary-700"
                    title="详情/人脸"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </button>
                  <button 
                    @click="openEditModal(person)" 
                    class="text-accent-600 hover:text-accent-700"
                    title="编辑"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button 
                    @click="handleToggleStatus(person)" 
                    :class="person.is_active ? 'text-warning-600 hover:text-warning-700' : 'text-success-600 hover:text-success-700'"
                    :title="person.is_active ? '设为离职' : '设为在职'"
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                  </button>
                  <button 
                    @click="openDeleteModal(person)" 
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
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 animate-fade-in max-h-[90vh] overflow-y-auto">
          <div class="px-6 py-4 border-b border-primary-100 sticky top-0 bg-white">
            <h3 class="text-lg font-semibold text-primary-900">
              {{ isEditing ? '编辑人员' : '新增人员' }}
            </h3>
          </div>
          <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
            <div v-if="formError" class="p-3 bg-danger-50 text-danger-700 text-sm rounded-lg">
              {{ formError }}
            </div>
            <!-- 姓名 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">
                姓名 <span class="text-danger-500">*</span>
              </label>
              <input v-model="formData.name" type="text" class="input" placeholder="请输入姓名" />
            </div>
            <!-- 工号 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">工号</label>
              <input v-model="formData.employee_id" type="text" class="input" placeholder="选填" />
            </div>
            <!-- 分组 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">所属分组</label>
              <select v-model="formData.group_id" class="input">
                <option value="">未分组</option>
                <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
              </select>
            </div>
            <!-- 部门 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">部门</label>
              <input v-model="formData.department" type="text" class="input" placeholder="选填" />
            </div>
            <!-- 电话 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">电话</label>
              <input v-model="formData.phone" type="text" class="input" placeholder="选填" />
            </div>
            <!-- 备注 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">备注</label>
              <textarea v-model="formData.remark" class="input" rows="2" placeholder="选填" />
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

    <!-- 人员详情弹窗（含人脸管理） -->
    <Teleport to="body">
      <div v-if="showDetailModal && currentPerson" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showDetailModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 animate-fade-in max-h-[90vh] overflow-y-auto">
          <div class="px-6 py-4 border-b border-primary-100 sticky top-0 bg-white flex items-center justify-between">
            <h3 class="text-lg font-semibold text-primary-900">人员详情</h3>
            <button @click="showDetailModal = false" class="text-primary-400 hover:text-primary-600">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="p-6">
            <!-- 基本信息 -->
            <div class="flex items-start gap-4 mb-6">
              <div class="w-16 h-16 rounded-full overflow-hidden bg-primary-100 flex-shrink-0">
                <img
                  v-if="currentPerson.primary_face?.image_url"
                  :src="getStaticUrl(currentPerson.primary_face.image_url)"
                  class="w-full h-full object-cover"
                  alt=""
                />
                <div v-else class="w-full h-full flex items-center justify-center text-primary-400">
                  <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
              </div>
              <div class="flex-1">
                <h4 class="text-lg font-semibold text-primary-900">{{ currentPerson.name }}</h4>
                <div class="text-sm text-primary-500 space-y-1 mt-1">
                  <p v-if="currentPerson.employee_id">工号: {{ currentPerson.employee_id }}</p>
                  <p v-if="currentPerson.department">部门: {{ currentPerson.department }}</p>
                  <p v-if="currentPerson.phone">电话: {{ currentPerson.phone }}</p>
                </div>
              </div>
              <span
                v-if="currentPerson.group"
                class="px-2 py-1 rounded text-xs font-medium"
                :style="{ backgroundColor: (currentPerson.group.color || '#3B82F6') + '20', color: currentPerson.group.color || '#3B82F6' }"
              >
                {{ currentPerson.group.name }}
              </span>
            </div>

            <!-- 人脸图片管理 -->
            <div class="border-t border-primary-100 pt-4">
              <div class="flex items-center justify-between mb-4">
                <h5 class="font-medium text-primary-900">人脸图片 ({{ currentPerson.face_images?.length || 0 }})</h5>
                <input
                  ref="fileInput"
                  type="file"
                  accept="image/jpeg,image/png"
                  class="hidden"
                  @change="handleFileChange"
                />
                <button @click="triggerFileInput" :disabled="uploadingFace" class="btn-secondary btn-sm">
                  <svg v-if="uploadingFace" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                  </svg>
                  {{ uploadingFace ? '上传中...' : '上传图片' }}
                </button>
              </div>

              <!-- 图片列表 -->
              <div v-if="currentPerson.face_images && currentPerson.face_images.length > 0" class="grid grid-cols-3 gap-3">
                <div
                  v-for="face in currentPerson.face_images"
                  :key="face.id"
                  class="relative group aspect-square rounded-lg overflow-hidden bg-primary-100"
                >
                  <img :src="getStaticUrl(face.image_url)" class="w-full h-full object-cover" alt="" />
                  <!-- 主图标记 -->
                  <div v-if="face.is_primary" class="absolute top-1 left-1 bg-success-500 text-white text-xs px-1.5 py-0.5 rounded">
                    主图
                  </div>
                  <!-- 操作按钮 -->
                  <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    <button
                      v-if="!face.is_primary"
                      @click="handleSetPrimary(face)"
                      class="p-1.5 bg-white rounded-full text-success-600 hover:bg-success-50"
                      title="设为主图"
                    >
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      </svg>
                    </button>
                    <button
                      @click="handleDeleteFace(face)"
                      class="p-1.5 bg-white rounded-full text-danger-600 hover:bg-danger-50"
                      title="删除"
                    >
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
              <div v-else class="text-center py-8 bg-primary-50 rounded-lg">
                <svg class="w-12 h-12 mx-auto text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <p class="mt-2 text-sm text-primary-500">暂无人脸图片</p>
                <p class="text-xs text-primary-400 mt-1">请上传清晰的正面人脸照片</p>
              </div>
            </div>
          </div>
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
              确定要删除「{{ currentPerson?.name }}」吗？相关人脸图片也将被删除。
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
