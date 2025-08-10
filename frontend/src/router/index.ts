// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const Login        = () => import('@/pages/Login.vue')
const AuthedLayout = () => import('@/layouts/AuthedLayout.vue')
const Dashboard    = () => import('@/pages/Dashboard.vue')
const Profile      = () => import('@/pages/Profile.vue')
const Settings     = () => import('@/pages/Settings.vue')

const AIChat       = () => import('@/pages/AIChat.vue')
const AIKnowledge  = () => import('@/pages/AIKnowledge.vue')
const AIEmbeddings = () => import('@/pages/AIEmbeddings.vue')
const InboxTasks   = () => import('@/pages/InboxTasks.vue')
const InboxArchive = () => import('@/pages/InboxArchive.vue')
const AIStreamChat = () => import('@/pages/AIStreamChat.vue')

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: Login, meta: { public: true } },
  {
    path: '/',
    component: AuthedLayout,
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: Dashboard },
      { path: 'profile',   name: 'profile',   component: Profile },
      { path: 'settings',  name: 'settings',  component: Settings },

      // AI group
      { path: 'ai/chat',       name: 'ai-chat',       component: AIChat },
      { path: 'ai/knowledge',  name: 'ai-knowledge',  component: AIKnowledge },
      { path: 'ai/embeddings', name: 'ai-embeddings', component: AIEmbeddings },
      { path: 'ai/stream',     name: 'ai-stramChat',  component: AIStreamChat },


      // Inbox group
      { path: 'inbox/tasks',   name: 'inbox-tasks',   component: InboxTasks },
      { path: 'inbox/archive', name: 'inbox-archive', component: InboxArchive },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  if (to.meta.public) return

  const { token, initAuthHeader } = useAuth()
  const hasToken = !!token.value || !!localStorage.getItem('token')

  // กู้ header ถ้ารีเฟรชมาแล้ว ref ว่าง
  if (!token.value && localStorage.getItem('token')) {
    initAuthHeader()
  }

  if (!hasToken) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router
