/**
 * 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory((import.meta as any).env.BASE_URL),
  routes: [
    // 登录页
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { requiresAuth: false, title: '登录' }
    },
    // 主布局
    {
      path: '/',
      component: () => import('@/components/layout/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        // 仪表盘
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/dashboard/DashboardView.vue'),
          meta: { title: '仪表盘' }
        },
        // 实时监控
        {
          path: 'monitor',
          name: 'monitor',
          component: () => import('@/views/monitor/MonitorView.vue'),
          meta: { title: '实时监控' }
        },
        // 报警管理
        {
          path: 'alerts',
          name: 'alerts',
          component: () => import('@/views/alerts/AlertsView.vue'),
          meta: { title: '报警管理' }
        },
        // 人员管理
        {
          path: 'persons',
          name: 'persons',
          component: () => import('@/views/persons/PersonsView.vue'),
          meta: { title: '人员管理' }
        },
        // 人员分组
        {
          path: 'groups',
          name: 'groups',
          component: () => import('@/views/groups/GroupsView.vue'),
          meta: { title: '人员分组' }
        },
        // 摄像头管理
        {
          path: 'cameras',
          name: 'cameras',
          component: () => import('@/views/cameras/CamerasView.vue'),
          meta: { title: '摄像头管理' }
        },
        // 区域管理
        {
          path: 'zones',
          name: 'zones',
          component: () => import('@/views/zones/ZonesView.vue'),
          meta: { title: '区域管理' }
        },
        // 用户管理 (仅管理员)
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/users/UsersView.vue'),
          meta: { title: '用户管理', requiresAdmin: true }
        },
        // 操作日志 (仅管理员)
        {
          path: 'logs',
          name: 'logs',
          component: () => import('@/views/logs/LogsView.vue'),
          meta: { title: '操作日志', requiresAdmin: true }
        },
        // 系统设置 (仅管理员)
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/settings/SettingsView.vue'),
          meta: { title: '系统设置', requiresAdmin: true }
        },
        // 个人中心
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/profile/ProfileView.vue'),
          meta: { title: '个人中心' }
        },
      ]
    },
    // 404
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  // 设置页面标题
  document.title = to.meta.title
    ? `${to.meta.title} - 视频监控报警系统`
    : '视频监控报警系统'

  // 检查是否需要登录
  if (to.meta.requiresAuth !== false && !authStore.isLoggedIn) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  // 已登录用户访问登录页，跳转首页
  if (to.name === 'login' && authStore.isLoggedIn) {
    next({ name: 'dashboard' })
    return
  }

  // 检查管理员权限
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next({ name: 'dashboard' })
    return
  }

  next()
})

export default router
