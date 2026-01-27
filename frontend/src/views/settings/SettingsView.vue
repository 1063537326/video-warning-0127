<script setup lang="ts">
/**
 * 系统设置页面
 * 
 * 管理系统配置、数据清理、查看系统状态。
 */
import { ref, onMounted } from 'vue'
import { settingsApi } from '@/api'
import type { ConfigGroup, SystemStatus } from '@/types'

// ============ 数据状态 ============

const loading = ref(false)
const saving = ref(false)
const configGroups = ref<ConfigGroup[]>([])
const systemStatus = ref<SystemStatus | null>(null)
const editedValues = ref<Record<string, string>>({})

// 清理相关
const showCleanupModal = ref(false)
const cleanupForm = ref({
  cleanupType: 'all',
  daysToKeep: 30,
  dryRun: true
})
const cleaning = ref(false)
const cleanupResult = ref<any>(null)

// 分组标签映射
const groupLabels: Record<string, string> = {
  face_recognition: '人脸识别',
  alert: '报警设置',
  storage: '存储配置',
  system: '系统配置'
}

// ============ 方法 ============

/**
 * 加载系统配置
 */
const loadConfig = async () => {
  loading.value = true
  try {
    const res = await settingsApi.getConfig()
    configGroups.value = res.groups
    // 初始化编辑值
    res.groups.forEach(group => {
      group.items.forEach(item => {
        editedValues.value[item.config_key] = item.config_value || ''
      })
    })
  } catch (error) {
    console.error('加载配置失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 加载系统状态
 */
const loadStatus = async () => {
  try {
    const res = await settingsApi.getStatus()
    systemStatus.value = res
  } catch (error) {
    console.error('加载系统状态失败:', error)
  }
}

/**
 * 保存配置
 */
const handleSave = async () => {
  saving.value = true
  try {
    const items = Object.entries(editedValues.value).map(([key, value]) => ({
      config_key: key,
      config_value: value
    }))
    const res = await settingsApi.updateConfig(items)
    alert(`保存成功：成功 ${res.success_count} 项，失败 ${res.failed_count} 项`)
    loadConfig()
  } catch (error: any) {
    alert(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

/**
 * 打开清理弹窗
 */
const openCleanupModal = () => {
  cleanupForm.value = {
    cleanupType: 'all',
    daysToKeep: 30,
    dryRun: true
  }
  cleanupResult.value = null
  showCleanupModal.value = true
}

/**
 * 执行数据清理
 */
const handleCleanup = async () => {
  cleaning.value = true
  cleanupResult.value = null
  try {
    const res = await settingsApi.triggerCleanup({
      cleanup_type: cleanupForm.value.cleanupType,
      days_to_keep: cleanupForm.value.daysToKeep,
      dry_run: cleanupForm.value.dryRun
    })
    cleanupResult.value = res
    if (!cleanupForm.value.dryRun) {
      loadStatus()
    }
  } catch (error: any) {
    alert(error.response?.data?.detail || '清理失败')
  } finally {
    cleaning.value = false
  }
}

/**
 * 获取配置项详细提示
 * 
 * 鼠标悬停在问号图标上时显示的详细说明
 */
const getConfigTooltip = (key: string): string => {
  const tooltips: Record<string, string> = {
    // 人脸识别配置
    face_similarity_threshold: '人脸比对相似度阈值（0.0-1.0）。值越高匹配越严格，可能漏报；值越低匹配越宽松，可能误报。建议值：0.5-0.7',
    face_detection_min_size: '最小人脸检测尺寸（像素）。小于此尺寸的人脸将被忽略。值越小检测越灵敏但性能消耗越大。建议值：30-50',
    face_detection_confidence: '人脸检测置信度阈值（0.0-1.0）。过滤低置信度的检测结果，避免误检。建议值：0.8-0.95',
    // 报警配置
    alert_cooldown_seconds: '同一人员的报警冷却时间（秒）。在此时间内，同一人不会重复触发报警，避免频繁打扰。建议值：30-120',
    alert_sound_enabled: '启用后，触发报警时会播放声音提示',
    alert_push_enabled: '启用后，报警信息会通过 WebSocket 实时推送到前端',
    // 存储配置
    data_retention_days: '报警记录和截图的保留天数。超过此天数的数据将在自动清理时被删除。建议值：30-90',
    capture_quality: '截图保存的 JPEG 质量（1-100）。值越高图片越清晰但文件越大。建议值：70-90',
    max_face_images_per_person: '每个人员最多保存的人脸图片数量。超出后需手动删除旧图片才能添加新图片',
    concurrent_limit: '并发识别限制数。控制同时请求人脸识别服务的最大并发数，防止服务器过载。建议值：3-10',
    // 系统配置
    enable_operation_log: '启用后，系统会记录用户的操作日志（登录、修改配置、删除数据等），便于审计追踪',
    auto_cleanup_enabled: '【自动清理功能】启用后，系统会在指定时间自动清理过期的报警记录和截图文件，释放磁盘空间。清理范围由"数据保留天数"决定',
    auto_cleanup_hour: '自动清理任务的执行时间（0-23 点）。建议设置在凌晨业务低峰期执行',
  }
  return tooltips[key] || ''
}

/**
 * 获取配置项简短描述
 */
const getConfigDescription = (key: string): string => {
  const descriptions: Record<string, string> = {
    face_similarity_threshold: '值越高越严格',
    face_detection_min_size: '小于此尺寸的人脸将被忽略',
    face_detection_confidence: '过滤低置信度检测结果',
    alert_cooldown_seconds: '避免同一人重复报警',
    alert_sound_enabled: '触发报警时播放声音',
    alert_push_enabled: '实时推送报警到前端',
    data_retention_days: '超过此天数的数据会被清理',
    capture_quality: '值越高图片越清晰',
    max_face_images_per_person: '每人最多保存的照片数',
    concurrent_limit: 'API 请求并发限制',
    enable_operation_log: '记录用户操作便于审计',
    auto_cleanup_enabled: '定时清理过期数据释放空间',
    auto_cleanup_hour: '建议设在凌晨低峰期',
  }
  return descriptions[key] || ''
}

/**
 * 获取配置项输入类型
 */
const getInputType = (valueType: string): string => {
  switch (valueType) {
    case 'number': return 'number'
    case 'boolean': return 'checkbox'
    default: return 'text'
  }
}

// ============ 生命周期 ============

onMounted(() => {
  loadConfig()
  loadStatus()
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-primary-900">系统设置</h2>
        <p class="text-primary-500 mt-1">配置系统参数和维护操作</p>
      </div>
      <div class="flex items-center gap-4">
        <button @click="handleSave" :disabled="saving" class="btn-primary">
          <svg v-if="saving" class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          {{ saving ? '保存中...' : '保存配置' }}
        </button>
        <button @click="openCleanupModal" class="btn-danger">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          数据清理
        </button>
      </div>
    </div>

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

    <template v-else>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- 配置区域 -->
        <div class="lg:col-span-2 space-y-6">
          <!-- 配置分组 -->
          <div v-for="group in configGroups" :key="group.group_name" class="card">
            <div class="card-header">
              <h3 class="font-semibold text-primary-900">
                {{ groupLabels[group.group_name] || group.group_label }}
              </h3>
            </div>
            <div class="card-body space-y-4">
              <div v-for="item in group.items" :key="item.config_key" class="flex items-start gap-4">
                <div class="flex-1">
                  <div class="flex items-center gap-2 mb-1">
                    <label class="text-sm font-medium text-primary-700">
                      {{ item.description || item.config_key }}
                    </label>
                    <!-- 问号提示图标 -->
                    <div v-if="getConfigTooltip(item.config_key)" class="relative group/tooltip">
                      <svg class="w-4 h-4 text-primary-400 hover:text-primary-600 cursor-help" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <!-- Tooltip 弹出框 -->
                      <div class="absolute left-6 top-0 z-50 invisible group-hover/tooltip:visible opacity-0 group-hover/tooltip:opacity-100 transition-all duration-200">
                        <div class="bg-gray-800 text-white text-xs rounded-lg py-2 px-3 w-64 shadow-lg">
                          {{ getConfigTooltip(item.config_key) }}
                          <div class="absolute left-0 top-2 -translate-x-1 w-2 h-2 bg-gray-800 rotate-45"></div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <p v-if="getConfigDescription(item.config_key)" class="text-xs text-primary-400 mb-2">
                    {{ getConfigDescription(item.config_key) }}
                  </p>
                  <!-- Boolean 类型 -->
                  <div v-if="item.value_type === 'boolean'" class="flex items-center gap-2">
                    <button
                      @click="editedValues[item.config_key] = editedValues[item.config_key] === 'true' ? 'false' : 'true'"
                      :class="[
                        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                        editedValues[item.config_key] === 'true' ? 'bg-success-500' : 'bg-primary-200'
                      ]"
                    >
                      <span
                        :class="[
                          'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                          editedValues[item.config_key] === 'true' ? 'translate-x-6' : 'translate-x-1'
                        ]"
                      />
                    </button>
                    <span class="text-sm text-primary-600">
                      {{ editedValues[item.config_key] === 'true' ? '启用' : '禁用' }}
                    </span>
                  </div>
                  <!-- Number 类型 -->
                  <input
                    v-else-if="item.value_type === 'number'"
                    v-model="editedValues[item.config_key]"
                    type="number"
                    class="input w-40"
                  />
                  <!-- String 类型 -->
                  <input
                    v-else
                    v-model="editedValues[item.config_key]"
                    type="text"
                    class="input"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 系统状态 -->
        <div class="space-y-6">
          <!-- 系统信息 -->
          <div class="card">
            <div class="card-header">
              <h3 class="font-semibold text-primary-900">系统状态</h3>
            </div>
            <div class="card-body space-y-4">
              <div v-if="systemStatus">
                <!-- 运行时间 -->
                <div class="flex items-center justify-between py-2 border-b border-primary-100">
                  <span class="text-sm text-primary-500">运行时间</span>
                  <span class="text-sm font-medium text-primary-900">{{ systemStatus.uptime_formatted }}</span>
                </div>
                <!-- 版本 -->
                <div class="flex items-center justify-between py-2 border-b border-primary-100">
                  <span class="text-sm text-primary-500">系统版本</span>
                  <span class="text-sm font-medium text-primary-900">{{ systemStatus.app_version }}</span>
                </div>
                <!-- 数据库 -->
                <div class="flex items-center justify-between py-2 border-b border-primary-100">
                  <span class="text-sm text-primary-500">数据库</span>
                  <span :class="[
                    'badge',
                    systemStatus.database.connected ? 'badge-success' : 'badge-danger'
                  ]">
                    {{ systemStatus.database.connected ? '已连接' : '未连接' }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- 磁盘使用 -->
          <div v-if="systemStatus?.disk_usage?.[0]" class="card">
            <div class="card-header">
              <h3 class="font-semibold text-primary-900">磁盘使用</h3>
            </div>
            <div class="card-body">
              <div class="mb-2 flex items-center justify-between">
                <span class="text-sm text-primary-500">{{ systemStatus.disk_usage[0].path }}</span>
                <span class="text-sm font-medium text-primary-900">{{ systemStatus.disk_usage[0].usage_percent }}%</span>
              </div>
              <div class="h-3 bg-primary-100 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="systemStatus.disk_usage[0].usage_percent > 90 ? 'bg-danger-500' : systemStatus.disk_usage[0].usage_percent > 70 ? 'bg-warning-500' : 'bg-success-500'"
                  :style="{ width: systemStatus.disk_usage[0].usage_percent + '%' }"
                />
              </div>
              <div class="mt-2 text-xs text-primary-400">
                已使用 {{ systemStatus.disk_usage[0].used_formatted }} / 共 {{ systemStatus.disk_usage[0].total_formatted }}
              </div>
            </div>
          </div>

          <!-- 数据统计 -->
          <div v-if="systemStatus?.database.total_records" class="card">
            <div class="card-header">
              <h3 class="font-semibold text-primary-900">数据统计</h3>
            </div>
            <div class="card-body space-y-2">
              <div
                v-for="(count, table) in systemStatus.database.total_records"
                :key="table"
                class="flex items-center justify-between text-sm"
              >
                <span class="text-primary-500">{{ table }}</span>
                <span class="font-medium text-primary-900">{{ count }} 条</span>
              </div>
            </div>
          </div>

          <!-- 系统资源 -->
          <div v-if="systemStatus?.system_info" class="card">
            <div class="card-header">
              <h3 class="font-semibold text-primary-900">系统资源</h3>
            </div>
            <div class="card-body space-y-3">
              <!-- CPU -->
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm text-primary-500">CPU</span>
                  <span class="text-sm text-primary-700">{{ systemStatus.system_info.cpu_percent }}%</span>
                </div>
                <div class="h-2 bg-primary-100 rounded-full overflow-hidden">
                  <div
                    class="h-full bg-accent-500 rounded-full"
                    :style="{ width: systemStatus.system_info.cpu_percent + '%' }"
                  />
                </div>
              </div>
              <!-- 内存 -->
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm text-primary-500">内存</span>
                  <span class="text-sm text-primary-700">{{ systemStatus.system_info.memory_percent }}%</span>
                </div>
                <div class="h-2 bg-primary-100 rounded-full overflow-hidden">
                  <div
                    class="h-full bg-primary-500 rounded-full"
                    :style="{ width: systemStatus.system_info.memory_percent + '%' }"
                  />
                </div>
                <p class="text-xs text-primary-400 mt-1">
                  {{ systemStatus.system_info.memory_used }} / {{ systemStatus.system_info.memory_total }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 数据清理弹窗 -->
    <Teleport to="body">
      <div v-if="showCleanupModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50" @click="showCleanupModal = false" />
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 animate-fade-in">
          <div class="px-6 py-4 border-b border-primary-100">
            <h3 class="text-lg font-semibold text-primary-900">数据清理</h3>
          </div>
          <div class="p-6 space-y-4">
            <!-- 清理类型 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">清理类型</label>
              <select v-model="cleanupForm.cleanupType" class="input">
                <option value="all">全部</option>
                <option value="alert">报警记录</option>
                <option value="capture">截图文件</option>
              </select>
            </div>
            <!-- 保留天数 -->
            <div>
              <label class="block text-sm font-medium text-primary-700 mb-1">保留天数</label>
              <input v-model.number="cleanupForm.daysToKeep" type="number" class="input" min="1" />
              <p class="text-xs text-primary-400 mt-1">将删除超过此天数的数据</p>
            </div>
            <!-- 模拟运行 -->
            <div class="flex items-center justify-between">
              <div>
                <label class="text-sm font-medium text-primary-700">模拟运行</label>
                <p class="text-xs text-primary-400">仅预览将删除的数据，不实际删除</p>
              </div>
              <button
                @click="cleanupForm.dryRun = !cleanupForm.dryRun"
                :class="[
                  'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                  cleanupForm.dryRun ? 'bg-success-500' : 'bg-danger-500'
                ]"
              >
                <span
                  :class="[
                    'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                    cleanupForm.dryRun ? 'translate-x-6' : 'translate-x-1'
                  ]"
                />
              </button>
            </div>

            <!-- 清理结果 -->
            <div v-if="cleanupResult" class="p-4 bg-primary-50 rounded-lg">
              <h4 class="font-medium text-primary-900 mb-2">
                {{ cleanupResult.dry_run ? '预览结果' : '清理完成' }}
              </h4>
              <div class="text-sm text-primary-600 space-y-1">
                <p>删除记录数: {{ cleanupResult.records_deleted }}</p>
                <p>删除文件数: {{ cleanupResult.files_deleted }}</p>
                <p>释放空间: {{ cleanupResult.bytes_freed_formatted }}</p>
              </div>
            </div>

            <!-- 按钮 -->
            <div class="flex justify-end gap-3 pt-4">
              <button @click="showCleanupModal = false" class="btn-secondary">关闭</button>
              <button
                @click="handleCleanup"
                :disabled="cleaning"
                :class="cleanupForm.dryRun ? 'btn-primary' : 'btn-danger'"
              >
                <svg v-if="cleaning" class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {{ cleaning ? '执行中...' : (cleanupForm.dryRun ? '预览' : '执行清理') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
