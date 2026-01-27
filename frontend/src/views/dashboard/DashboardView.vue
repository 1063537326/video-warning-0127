<script setup lang="ts">
/**
 * 仪表盘页面
 * 
 * 展示系统概览、报警统计、摄像头状态、趋势图表等信息。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { alertApi, cameraApi, settingsApi, personApi, groupApi } from '@/api'
import type { AlertStatistics, CameraStatusStats, SystemStatus } from '@/types'
import { useTheme } from '@/composables/useTheme'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
])

// 主题
const { isDark } = useTheme()

// 数据
const loading = ref(true)
const alertStats = ref<AlertStatistics | null>(null)
const cameraStats = ref<CameraStatusStats | null>(null)
const systemStatus = ref<SystemStatus | null>(null)
const personCount = ref(0)
const groupCount = ref(0)

// 趋势图数据
const trendPeriod = ref<'7d' | '30d' | '90d'>('7d')
const trendData = ref<any[]>([])
const trendLoading = ref(false)

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const [alertRes, cameraRes, systemRes, personRes, groupRes] = await Promise.all([
      alertApi.getStatistics(),
      cameraApi.getStatus(),
      settingsApi.getStatus(),
      personApi.getList({ page: 1, page_size: 1 }),
      groupApi.getList({ page: 1, page_size: 1 }),
    ])
    
    alertStats.value = alertRes
    cameraStats.value = cameraRes.stats
    systemStatus.value = systemRes
    personCount.value = personRes.total
    groupCount.value = groupRes.total
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 加载趋势数据
 */
const loadTrendData = async () => {
  trendLoading.value = true
  try {
    const res = await alertApi.getTrend(trendPeriod.value)
    trendData.value = res.items || []
  } catch (error) {
    console.error('Failed to load trend data:', error)
    trendData.value = []
  } finally {
    trendLoading.value = false
  }
}

// 监听周期变化
watch(trendPeriod, () => {
  loadTrendData()
})

onMounted(() => {
  loadData()
  loadTrendData()
})

// 格式化数字
const formatNumber = (num: number) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

/**
 * 图表通用主题配置
 */
const chartTheme = computed(() => ({
  textColor: isDark.value ? '#d9e2ec' : '#334e68',
  axisLineColor: isDark.value ? '#486581' : '#bcccdc',
  splitLineColor: isDark.value ? '#334e68' : '#d9e2ec',
  backgroundColor: 'transparent',
}))

/**
 * 报警趋势图配置
 */
const trendChartOption = computed(() => {
  const dates = trendData.value.map(item => item.date)
  const strangerData = trendData.value.map(item => item.stranger || 0)
  const knownData = trendData.value.map(item => item.known || 0)
  const blacklistData = trendData.value.map(item => item.blacklist || 0)

  return {
    backgroundColor: chartTheme.value.backgroundColor,
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark.value ? '#243b53' : '#ffffff',
      borderColor: isDark.value ? '#486581' : '#d9e2ec',
      textStyle: {
        color: chartTheme.value.textColor,
      },
      axisPointer: {
        type: 'shadow',
      },
    },
    legend: {
      data: ['陌生人', '已知人员', '黑名单'],
      top: 0,
      textStyle: {
        color: chartTheme.value.textColor,
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '40px',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: {
        lineStyle: {
          color: chartTheme.value.axisLineColor,
        },
      },
      axisLabel: {
        color: chartTheme.value.textColor,
        rotate: trendPeriod.value === '90d' ? 45 : 0,
        fontSize: 11,
      },
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: false,
      },
      axisLabel: {
        color: chartTheme.value.textColor,
      },
      splitLine: {
        lineStyle: {
          color: chartTheme.value.splitLineColor,
          type: 'dashed',
        },
      },
    },
    series: [
      {
        name: '陌生人',
        type: 'bar',
        stack: 'total',
        barMaxWidth: 30,
        itemStyle: {
          color: '#ef4444',
          borderRadius: [0, 0, 0, 0],
        },
        emphasis: {
          itemStyle: {
            color: '#dc2626',
          },
        },
        data: strangerData,
      },
      {
        name: '已知人员',
        type: 'bar',
        stack: 'total',
        barMaxWidth: 30,
        itemStyle: {
          color: '#319795',
          borderRadius: [0, 0, 0, 0],
        },
        emphasis: {
          itemStyle: {
            color: '#2c7a7b',
          },
        },
        data: knownData,
      },
      {
        name: '黑名单',
        type: 'bar',
        stack: 'total',
        barMaxWidth: 30,
        itemStyle: {
          color: '#102a43',
          borderRadius: [4, 4, 0, 0],
        },
        emphasis: {
          itemStyle: {
            color: '#243b53',
          },
        },
        data: blacklistData,
      },
    ],
  }
})

/**
 * 报警类型分布饼图配置
 */
const pieChartOption = computed(() => {
  const data = alertStats.value ? [
    { value: alertStats.value.by_type.stranger || 0, name: '陌生人', itemStyle: { color: '#ef4444' } },
    { value: alertStats.value.by_type.known || 0, name: '已知人员', itemStyle: { color: '#319795' } },
    { value: alertStats.value.by_type.blacklist || 0, name: '黑名单', itemStyle: { color: '#102a43' } },
  ] : []

  return {
    backgroundColor: chartTheme.value.backgroundColor,
    tooltip: {
      trigger: 'item',
      backgroundColor: isDark.value ? '#243b53' : '#ffffff',
      borderColor: isDark.value ? '#486581' : '#d9e2ec',
      textStyle: {
        color: chartTheme.value.textColor,
      },
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: {
        color: chartTheme.value.textColor,
      },
    },
    series: [
      {
        name: '报警类型',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: isDark.value ? '#1f3a52' : '#ffffff',
          borderWidth: 2,
        },
        label: {
          show: false,
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
            color: chartTheme.value.textColor,
          },
        },
        labelLine: {
          show: false,
        },
        data,
      },
    ],
  }
})

/**
 * 切换趋势周期
 */
const changeTrendPeriod = (period: '7d' | '30d' | '90d') => {
  trendPeriod.value = period
}
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <!-- 页面标题 -->
    <div>
      <h2 class="text-2xl font-bold text-primary-900 dark:text-primary-100">系统概览</h2>
      <p class="text-primary-500 dark:text-primary-400 mt-1">查看系统运行状态和关键指标</p>
    </div>

    <!-- 加载状态 -->
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
      <!-- 统计卡片 -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- 待处理报警 -->
        <div class="stat-card">
          <div class="stat-icon bg-danger-100">
            <svg class="w-6 h-6 text-danger-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          </div>
          <div>
            <p class="stat-value text-danger-600">{{ alertStats?.pending || 0 }}</p>
            <p class="stat-label">待处理报警</p>
          </div>
        </div>

        <!-- 今日报警 -->
        <div class="stat-card">
          <div class="stat-icon bg-warning-100">
            <svg class="w-6 h-6 text-warning-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <p class="stat-value text-warning-600">{{ alertStats?.today_count || 0 }}</p>
            <p class="stat-label">今日报警</p>
          </div>
        </div>

        <!-- 在线摄像头 -->
        <div class="stat-card">
          <div class="stat-icon bg-success-100">
            <svg class="w-6 h-6 text-success-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <p class="stat-value text-success-600">
              {{ cameraStats?.online || 0 }}<span class="text-sm text-primary-400">/{{ cameraStats?.total || 0 }}</span>
            </p>
            <p class="stat-label">在线摄像头</p>
          </div>
        </div>

        <!-- 已知人员 -->
        <div class="stat-card">
          <div class="stat-icon bg-accent-100">
            <svg class="w-6 h-6 text-accent-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <div>
            <p class="stat-value">{{ formatNumber(personCount) }}</p>
            <p class="stat-label">已知人员</p>
          </div>
        </div>
      </div>

      <!-- 趋势图表区 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- 报警趋势图 -->
        <div class="card lg:col-span-2">
          <div class="card-header flex items-center justify-between">
            <h3 class="font-semibold text-primary-900 dark:text-primary-100">报警趋势</h3>
            <div class="flex items-center gap-1 bg-primary-100 dark:bg-primary-700 rounded-lg p-1">
              <button 
                v-for="period in ['7d', '30d', '90d'] as const" 
                :key="period"
                @click="changeTrendPeriod(period)"
                :class="[
                  'px-3 py-1 text-xs font-medium rounded-md transition-colors',
                  trendPeriod === period 
                    ? 'bg-white dark:bg-primary-600 text-primary-900 dark:text-primary-100 shadow-sm' 
                    : 'text-primary-600 dark:text-primary-300 hover:text-primary-900 dark:hover:text-primary-100'
                ]"
              >
                {{ period === '7d' ? '7天' : period === '30d' ? '30天' : '90天' }}
              </button>
            </div>
          </div>
          <div class="card-body">
            <div v-if="trendLoading" class="flex items-center justify-center h-64">
              <div class="flex items-center gap-3 text-primary-500 dark:text-primary-400">
                <svg class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>加载中...</span>
              </div>
            </div>
            <div v-else-if="trendData.length === 0" class="flex items-center justify-center h-64 text-primary-500 dark:text-primary-400">
              <p>暂无数据</p>
            </div>
            <v-chart 
              v-else
              :option="trendChartOption" 
              :autoresize="true"
              class="h-64 w-full"
            />
          </div>
        </div>

        <!-- 报警类型分布 -->
        <div class="card">
          <div class="card-header">
            <h3 class="font-semibold text-primary-900 dark:text-primary-100">类型分布</h3>
          </div>
          <div class="card-body">
            <div v-if="!alertStats" class="flex items-center justify-center h-48 text-primary-500 dark:text-primary-400">
              <p>暂无数据</p>
            </div>
            <v-chart 
              v-else
              :option="pieChartOption" 
              :autoresize="true"
              class="h-48 w-full"
            />
          </div>
        </div>
      </div>

      <!-- 详细信息区 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- 报警统计 -->
        <div class="card lg:col-span-2">
          <div class="card-header flex items-center justify-between">
            <h3 class="font-semibold text-primary-900 dark:text-primary-100">报警统计</h3>
            <router-link :to="{ name: 'alerts' }" class="text-sm text-accent-600 hover:text-accent-700 dark:text-accent-400 dark:hover:text-accent-300">
              查看全部 →
            </router-link>
          </div>
          <div class="card-body">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div class="text-center p-4 bg-primary-50 dark:bg-primary-700/50 rounded-lg">
                <p class="text-2xl font-bold text-primary-900 dark:text-primary-100">{{ alertStats?.total || 0 }}</p>
                <p class="text-sm text-primary-500 dark:text-primary-400">总报警数</p>
              </div>
              <div class="text-center p-4 bg-danger-50 dark:bg-danger-900/30 rounded-lg">
                <p class="text-2xl font-bold text-danger-600 dark:text-danger-400">{{ alertStats?.pending || 0 }}</p>
                <p class="text-sm text-primary-500 dark:text-primary-400">待处理</p>
              </div>
              <div class="text-center p-4 bg-success-50 dark:bg-success-900/30 rounded-lg">
                <p class="text-2xl font-bold text-success-600 dark:text-success-400">{{ alertStats?.processed || 0 }}</p>
                <p class="text-sm text-primary-500 dark:text-primary-400">已处理</p>
              </div>
              <div class="text-center p-4 bg-primary-100 dark:bg-primary-700/50 rounded-lg">
                <p class="text-2xl font-bold text-primary-600 dark:text-primary-300">{{ alertStats?.ignored || 0 }}</p>
                <p class="text-sm text-primary-500 dark:text-primary-400">已忽略</p>
              </div>
            </div>

            <!-- 按类型统计 -->
            <div class="mt-6">
              <h4 class="text-sm font-medium text-primary-700 dark:text-primary-300 mb-3">按类型分布</h4>
              <div class="space-y-2">
                <div class="flex items-center gap-3">
                  <span class="w-20 text-sm text-primary-500 dark:text-primary-400">陌生人</span>
                  <div class="flex-1 h-2 bg-primary-100 dark:bg-primary-700 rounded-full overflow-hidden">
                    <div 
                      class="h-full bg-danger-500 rounded-full transition-all duration-500"
                      :style="{ width: alertStats?.total ? ((alertStats.by_type.stranger || 0) / alertStats.total * 100) + '%' : '0%' }"
                    />
                  </div>
                  <span class="w-12 text-sm text-primary-700 dark:text-primary-300 text-right">{{ alertStats?.by_type.stranger || 0 }}</span>
                </div>
                <div class="flex items-center gap-3">
                  <span class="w-20 text-sm text-primary-500 dark:text-primary-400">已知人员</span>
                  <div class="flex-1 h-2 bg-primary-100 dark:bg-primary-700 rounded-full overflow-hidden">
                    <div 
                      class="h-full bg-accent-500 rounded-full transition-all duration-500"
                      :style="{ width: alertStats?.total ? ((alertStats.by_type.known || 0) / alertStats.total * 100) + '%' : '0%' }"
                    />
                  </div>
                  <span class="w-12 text-sm text-primary-700 dark:text-primary-300 text-right">{{ alertStats?.by_type.known || 0 }}</span>
                </div>
                <div class="flex items-center gap-3">
                  <span class="w-20 text-sm text-primary-500 dark:text-primary-400">黑名单</span>
                  <div class="flex-1 h-2 bg-primary-100 dark:bg-primary-700 rounded-full overflow-hidden">
                    <div 
                      class="h-full bg-primary-900 dark:bg-primary-300 rounded-full transition-all duration-500"
                      :style="{ width: alertStats?.total ? ((alertStats.by_type.blacklist || 0) / alertStats.total * 100) + '%' : '0%' }"
                    />
                  </div>
                  <span class="w-12 text-sm text-primary-700 dark:text-primary-300 text-right">{{ alertStats?.by_type.blacklist || 0 }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 系统状态 -->
        <div class="card">
          <div class="card-header">
            <h3 class="font-semibold text-primary-900 dark:text-primary-100">系统状态</h3>
          </div>
          <div class="card-body space-y-4">
            <!-- 运行时间 -->
            <div class="flex items-center justify-between">
              <span class="text-sm text-primary-500 dark:text-primary-400">运行时间</span>
              <span class="text-sm font-medium text-primary-900 dark:text-primary-100">{{ systemStatus?.uptime_formatted || '-' }}</span>
            </div>

            <!-- 数据库 -->
            <div class="flex items-center justify-between">
              <span class="text-sm text-primary-500 dark:text-primary-400">数据库</span>
              <span :class="[
                'badge',
                systemStatus?.database.connected ? 'badge-success' : 'badge-danger'
              ]">
                {{ systemStatus?.database.connected ? '已连接' : '未连接' }}
              </span>
            </div>

            <!-- 磁盘使用 -->
            <div v-if="systemStatus?.disk_usage?.[0]">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm text-primary-500 dark:text-primary-400">磁盘使用</span>
                <span class="text-sm text-primary-700 dark:text-primary-300">{{ systemStatus.disk_usage[0].usage_percent }}%</span>
              </div>
              <div class="h-2 bg-primary-100 dark:bg-primary-700 rounded-full overflow-hidden">
                <div 
                  class="h-full rounded-full transition-all duration-500"
                  :class="systemStatus.disk_usage[0].usage_percent > 90 ? 'bg-danger-500' : systemStatus.disk_usage[0].usage_percent > 70 ? 'bg-warning-500' : 'bg-success-500'"
                  :style="{ width: systemStatus.disk_usage[0].usage_percent + '%' }"
                />
              </div>
              <p class="text-xs text-primary-400 mt-1">
                {{ systemStatus.disk_usage[0].used_formatted }} / {{ systemStatus.disk_usage[0].total_formatted }}
              </p>
            </div>

            <!-- CPU -->
            <div v-if="systemStatus?.system_info">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm text-primary-500 dark:text-primary-400">CPU 使用</span>
                <span class="text-sm text-primary-700 dark:text-primary-300">{{ systemStatus.system_info.cpu_percent }}%</span>
              </div>
              <div class="h-2 bg-primary-100 dark:bg-primary-700 rounded-full overflow-hidden">
                <div 
                  class="h-full bg-accent-500 rounded-full transition-all duration-500"
                  :style="{ width: systemStatus.system_info.cpu_percent + '%' }"
                />
              </div>
            </div>

            <!-- 内存 -->
            <div v-if="systemStatus?.system_info">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm text-primary-500 dark:text-primary-400">内存使用</span>
                <span class="text-sm text-primary-700 dark:text-primary-300">{{ systemStatus.system_info.memory_percent }}%</span>
              </div>
              <div class="h-2 bg-primary-100 dark:bg-primary-700 rounded-full overflow-hidden">
                <div 
                  class="h-full bg-primary-500 dark:bg-primary-400 rounded-full transition-all duration-500"
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

      <!-- 快捷入口 -->
      <div class="card">
        <div class="card-header">
          <h3 class="font-semibold text-primary-900 dark:text-primary-100">快捷入口</h3>
        </div>
        <div class="card-body">
          <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <router-link 
              :to="{ name: 'monitor' }" 
              class="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-700/50 transition-colors"
            >
              <div class="w-12 h-12 bg-accent-100 dark:bg-accent-900/50 rounded-xl flex items-center justify-center">
                <svg class="w-6 h-6 text-accent-600 dark:text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <span class="text-sm text-primary-700 dark:text-primary-300">实时监控</span>
            </router-link>

            <router-link 
              :to="{ name: 'alerts' }" 
              class="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-700/50 transition-colors"
            >
              <div class="w-12 h-12 bg-danger-100 dark:bg-danger-900/50 rounded-xl flex items-center justify-center">
                <svg class="w-6 h-6 text-danger-600 dark:text-danger-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
              </div>
              <span class="text-sm text-primary-700 dark:text-primary-300">报警管理</span>
            </router-link>

            <router-link 
              :to="{ name: 'persons' }" 
              class="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-700/50 transition-colors"
            >
              <div class="w-12 h-12 bg-primary-100 dark:bg-primary-700/50 rounded-xl flex items-center justify-center">
                <svg class="w-6 h-6 text-primary-600 dark:text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <span class="text-sm text-primary-700 dark:text-primary-300">人员管理</span>
            </router-link>

            <router-link 
              :to="{ name: 'cameras' }" 
              class="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-700/50 transition-colors"
            >
              <div class="w-12 h-12 bg-success-100 dark:bg-success-900/50 rounded-xl flex items-center justify-center">
                <svg class="w-6 h-6 text-success-600 dark:text-success-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <span class="text-sm text-primary-700 dark:text-primary-300">摄像头</span>
            </router-link>

            <router-link 
              :to="{ name: 'zones' }" 
              class="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-700/50 transition-colors"
            >
              <div class="w-12 h-12 bg-warning-100 dark:bg-warning-900/50 rounded-xl flex items-center justify-center">
                <svg class="w-6 h-6 text-warning-600 dark:text-warning-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <span class="text-sm text-primary-700 dark:text-primary-300">区域管理</span>
            </router-link>

            <router-link 
              :to="{ name: 'settings' }" 
              class="flex flex-col items-center gap-2 p-4 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-700/50 transition-colors"
            >
              <div class="w-12 h-12 bg-primary-200 dark:bg-primary-700/50 rounded-xl flex items-center justify-center">
                <svg class="w-6 h-6 text-primary-700 dark:text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <span class="text-sm text-primary-700 dark:text-primary-300">系统设置</span>
            </router-link>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
