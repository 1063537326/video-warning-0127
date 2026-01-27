/**
 * 主题切换组合式函数
 * 
 * 提供深色/浅色主题切换功能，支持系统主题跟随和本地持久化。
 */
import { ref, watch, onMounted } from 'vue'

/** 主题类型 */
export type ThemeMode = 'light' | 'dark' | 'system'

/** 本地存储键名 */
const THEME_STORAGE_KEY = 'video-warning-theme'

/** 当前主题模式 */
const themeMode = ref<ThemeMode>('system')

/** 实际应用的主题（light 或 dark） */
const isDark = ref(false)

/**
 * 获取系统主题偏好
 * 
 * @returns 系统是否偏好深色模式
 */
function getSystemTheme(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/**
 * 应用主题到 DOM
 * 
 * @param dark - 是否应用深色模式
 */
function applyTheme(dark: boolean): void {
  isDark.value = dark
  if (dark) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

/**
 * 更新主题（根据当前模式）
 */
function updateTheme(): void {
  if (themeMode.value === 'system') {
    applyTheme(getSystemTheme())
  } else {
    applyTheme(themeMode.value === 'dark')
  }
}

/**
 * 设置主题模式
 * 
 * @param mode - 要设置的主题模式
 */
function setTheme(mode: ThemeMode): void {
  themeMode.value = mode
  localStorage.setItem(THEME_STORAGE_KEY, mode)
  updateTheme()
}

/**
 * 切换主题（在 light/dark 之间切换）
 */
function toggleTheme(): void {
  if (themeMode.value === 'system') {
    // 如果当前是系统模式，切换到与当前相反的固定模式
    setTheme(isDark.value ? 'light' : 'dark')
  } else {
    setTheme(themeMode.value === 'dark' ? 'light' : 'dark')
  }
}

/**
 * 循环切换主题（light -> dark -> system -> light）
 */
function cycleTheme(): void {
  const modes: ThemeMode[] = ['light', 'dark', 'system']
  const currentIndex = modes.indexOf(themeMode.value)
  const nextIndex = (currentIndex + 1) % modes.length
  setTheme(modes[nextIndex])
}

/**
 * 初始化主题
 */
function initTheme(): void {
  // 从本地存储读取
  const stored = localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode | null
  if (stored && ['light', 'dark', 'system'].includes(stored)) {
    themeMode.value = stored
  }
  
  // 应用主题
  updateTheme()
  
  // 监听系统主题变化
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', () => {
    if (themeMode.value === 'system') {
      updateTheme()
    }
  })
}

/**
 * 主题切换组合式函数
 * 
 * @returns 主题相关的响应式状态和方法
 */
export function useTheme() {
  onMounted(() => {
    initTheme()
  })

  return {
    /** 当前主题模式（light/dark/system） */
    themeMode,
    /** 当前是否为深色模式 */
    isDark,
    /** 设置主题模式 */
    setTheme,
    /** 切换主题（light/dark） */
    toggleTheme,
    /** 循环切换主题 */
    cycleTheme,
  }
}

// 导出初始化函数，供 main.ts 使用
export { initTheme }
