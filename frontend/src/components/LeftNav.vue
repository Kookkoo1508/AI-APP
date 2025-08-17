<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, RouterLink, useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import {
  HomeIcon, UserIcon, Cog6ToothIcon, ChatBubbleLeftRightIcon, ChevronDownIcon,
  InboxStackIcon
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const { user, logout } = useAuth()

// เมนูหลัก + เมนูย่อย
type NavItem = {
  name: string
  to?: string
  icon?: any
  badge?: string | number
  children?: Array<{ name: string; to: string; badge?: string | number }>
}

const items = computed<NavItem[]>(() => ([
  { name: 'Dashboard', to: '/dashboard', icon: HomeIcon },
  { name: 'Profile',   to: '/profile',   icon: UserIcon },
  {
    name: 'AI',
    icon: ChatBubbleLeftRightIcon,
    children: [
      { name: 'Chat',        to: '/ai/chat',      badge: 'New' },
      { name: 'Knowledge',   to: '/ai/knowledge' },
       { name: 'Stream Chat',  to: '/ai/stream' },
    ]
  },
  {
    name: 'Inbox',
    icon: InboxStackIcon,
    children: [
      { name: 'Tasks', to: '/inbox/tasks', badge: 3 },
      { name: 'Archive', to: '/inbox/archive' },
    ]
  },
  { name: 'Settings',  to: '/settings',  icon: Cog6ToothIcon },
]))

// จัดการสถานะเปิด/ปิดของกลุ่มเมนูย่อย
const openGroups = ref<Record<string, boolean>>({})
function isActive(path?: string) {
  if (!path) return false
  return route.path === path
}
function isGroupActive(group: NavItem) {
  if (!group.children) return false
  return group.children.some(ch => route.path.startsWith(ch.to))
}
function toggleGroup(key: string) {
  openGroups.value[key] = !openGroups.value[key]
}
function ensureGroupOpenOnActive() {
  items.value.forEach((it) => {
    if (it.children && isGroupActive(it)) {
      openGroups.value[it.name] = true
    }
  })
}
ensureGroupOpenOnActive()

async function onLogout() {
  const ok = confirm('ออกจากระบบใช่หรือไม่?')
  if (!ok) return
  logout()
  await router.replace('/login')
}
</script>

<template>
  <aside class="w-72 shrink-0 p-4" aria-label="Sidebar">
    <div
      class="h-[calc(100vh-2rem)] sticky top-4 rounded-2xl
             bg-gradient-to-br from-slate-900/90 via-slate-800/80 to-slate-700/80
             text-white p-4 shadow-2xl ring-1 ring-white/10
             backdrop-blur-xl"
    >
      <!-- Brand -->
      <div class="mb-6 flex items-center gap-3">
        <div class="grid h-11 w-11 place-items-center rounded-xl bg-white/10 ring-1 ring-white/20">
          <span class="text-lg font-bold">AI</span>
        </div>
        <div class="truncate">
          <div class="text-xs text-white/60">Creative Tim style</div>
          <div class="font-semibold truncate">Admin Panel</div>
        </div>
      </div>

      <!-- User mini-card -->
      <div class="mb-4 rounded-xl bg-white/10 p-3 ring-1 ring-white/10">
        <p class="text-xs text-white/80">Signed in as</p>
        <p class="font-medium truncate">{{ user?.name || 'User' }}</p>
      </div>

      <!-- Navigation -->
      <nav class="space-y-1">
        <!-- เมนูเดี่ยว -->
        <RouterLink
          v-for="it in items.filter(i => !i.children)"
          :key="it.name"
          :to="it.to!"
          class="group flex items-center justify-between rounded-xl px-3 py-2 transition"
          :class="isActive(it.to)
            ? 'bg-white text-slate-900 ring-1 ring-black/5 shadow-sm'
            : 'text-white/80 hover:bg-white/10 hover:text-white'"
        >
          <span class="flex items-center gap-3">
            <component :is="it.icon" class="h-5 w-5" />
            <span class="text-sm font-medium">{{ it.name }}</span>
          </span>
          <span v-if="it.badge" class="ml-2 rounded-full bg-white/10 px-2 py-0.5 text-xs ring-1 ring-white/20">
            {{ it.badge }}
          </span>
        </RouterLink>

        <!-- เมนูกลุ่ม (มี children) -->
        <div
          v-for="grp in items.filter(i => i.children)"
          :key="grp.name"
          class="rounded-xl overflow-hidden"
        >
          <button
            type="button"
            class="w-full flex items-center justify-between rounded-xl px-3 py-2 transition text-left"
            :class="isGroupActive(grp)
              ? 'bg-white text-slate-900 ring-1 ring-black/5 shadow-sm'
              : 'text-white/80 hover:bg-white/10 hover:text-white'"
            @click="toggleGroup(grp.name)"
          >
            <span class="flex items-center gap-3">
              <component :is="grp.icon" class="h-5 w-5" />
              <span class="text-sm font-medium">{{ grp.name }}</span>
            </span>
            <ChevronDownIcon
              class="h-4 w-4 transition"
              :class="openGroups[grp.name] ? 'rotate-180' : ''"
            />
          </button>

          <div
            v-show="openGroups[grp.name]"
            class="mt-1 space-y-1 pl-9"
          >
            <RouterLink
              v-for="ch in grp.children"
              :key="ch.to"
              :to="ch.to"
              class="group flex items-center justify-between rounded-lg px-3 py-2 transition"
              :class="route.path === ch.to
                ? 'bg-white text-slate-900 ring-1 ring-black/5 shadow-sm'
                : 'text-white/70 hover:bg-white/10 hover:text-white'"
            >
              <span class="text-sm">{{ ch.name }}</span>
              <span v-if="ch.badge" class="ml-2 rounded-full bg-white/10 px-2 py-0.5 text-[10px] ring-1 ring-white/20">
                {{ ch.badge }}
              </span>
            </RouterLink>
          </div>
        </div>
      </nav>

      <!-- Logout -->
      <div class="mt-6">
        <button
          class="w-full rounded-xl bg-white/10 px-3 py-2 text-left text-white hover:bg-white/20 ring-1 ring-white/20 transition"
          @click="onLogout"
        >
          ออกจากระบบ
        </button>
      </div>
    </div>
  </aside>
</template>
