<!-- src/pages/AIChat.vue -->
<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useAI } from '@/composables/useAI'

type Role = 'user' | 'assistant' | 'system'
type Msg = { id: number; role: Role; content: string; ts: number; streaming?: boolean }
type ConvItem = { id: number; title: string; created_at: string; last_preview: string }
type ApiMsg = { id:number; role:Role; content:string; created_at:string }

const input = ref('')
const model = ref('llama3.1')
const chatBox = ref<HTMLDivElement | null>(null)
const messages = ref<Msg[]>([])
const conversations = ref<ConvItem[]>([])
let mid = 0

const atBottom = ref(true) // อยู่ล่างสุดหรือไม่ (ไว้ควบคุม autoscroll)
const showJumpBtn = ref(false)

const {
  loading, error, streamChat, stop,
  conversationId, newConversation,
  listConversations, loadMessages,
  renameConversation, deleteConversation
} = useAI()

const openMenuId = ref<number | null>(null)

function toggleMenu(id: number) {
  openMenuId.value = openMenuId.value === id ? null : id
}
function closeMenu() {
  openMenuId.value = null
}
function onDocClick(e: MouseEvent) {
  const el = e.target as HTMLElement
  if (!el.closest('[data-menu-root]')) closeMenu()
}
function onEsc(e: KeyboardEvent) {
  if (e.key === 'Escape') closeMenu()
}

onMounted(() => {
  document.addEventListener('click', onDocClick, { passive: true })
  document.addEventListener('keydown', onEsc)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onEsc)
})

function fmtTime(ts: number) {
  const d = new Date(ts)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function handleScroll() {
  const el = chatBox.value
  if (!el) return
  const gap = el.scrollHeight - el.scrollTop - el.clientHeight
  atBottom.value = gap < 48
  showJumpBtn.value = !atBottom.value
}

async function scrollToBottom(force = false) {
  await nextTick()
  const el = chatBox.value
  if (!el) return
  if (force || atBottom.value) {
    el.scrollTop = el.scrollHeight
  }
}

async function refreshConversations() {
  const items = await listConversations().catch(() => ({ items: [] as any }))
  conversations.value = Array.isArray(items) ? items : (items?.items ?? [])
}

async function openConversation(convId: number) {
  const items: ApiMsg[] = await loadMessages(convId)
  messages.value = items.map(m => ({
    id: m.id,
    role: m.role,
    content: m.content,
    ts: new Date(m.created_at).getTime(),
  }))
  mid = Math.max(0, ...messages.value.map(m => m.id)) + 1
  await scrollToBottom(true)
}

async function onSend() {
  const text = input.value.trim()
  if (!text || loading.value) return

  // push user message
  messages.value.push({ id: ++mid, role: 'user', content: text, ts: Date.now() })
  input.value = ''
  await scrollToBottom(true) // ส่งแล้วเลื่อนลงล่าง

  // assistant placeholder
  const aid = ++mid
  messages.value.push({ id: aid, role: 'assistant', content: '', ts: Date.now(), streaming: true })
  await scrollToBottom()

  const wasNew = !conversationId.value

  try {
    await streamChat(text, model.value, async (delta) => {
      const m = messages.value.find(m => m.id === aid)
      if (!m) return
      m.content += delta
      await scrollToBottom() // autoscroll เฉพาะถ้าอยู่ล่างสุด
    })
  } catch (e) {
    messages.value.push({ id: ++mid, role: 'system', content: String(e), ts: Date.now() })
  } finally {
    const m = messages.value.find(m => m.id === aid)
    if (m) m.streaming = false
    await scrollToBottom()
    if (wasNew && conversationId.value) await refreshConversations()
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    onSend()
  }
}

function onStop() {
  stop()
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'assistant' && messages.value[i].streaming) {
      messages.value[i].streaming = false
      break
    }
  }
}

async function onNewChat() {
  newConversation()
  messages.value = []
  input.value = ''
  await nextTick()
  await scrollToBottom(true)
}

function isSelected(convId: number) {
  return conversationId.value === convId
}

function jumpToLatest() {
  scrollToBottom(true)
}

onMounted(async () => {
  await refreshConversations()
  chatBox.value?.addEventListener('scroll', handleScroll, { passive: true })
  await nextTick()
  await scrollToBottom(true)
})

onUnmounted(() => {
  chatBox.value?.removeEventListener('scroll', handleScroll)
  stop()
})

watch(conversationId, async (val, old) => {
  if (val && val !== old) await openConversation(val)
})

async function onRename(c: { id:number; title:string }) {
  const newTitle = prompt('ตั้งชื่อบทสนทนาใหม่', c.title || '')
  if (newTitle == null) return  // ผู้ใช้กด Cancel → ไม่ต้องปิดเมนู

  try {
    await renameConversation(c.id, newTitle.trim() || 'Untitled')
    closeMenu()                 // ✅ กด OK แล้วปิดเมนู
    await refreshConversations()
  } catch (e) {
    alert('เปลี่ยนชื่อไม่สำเร็จ')
  }
}

async function onDelete(c: { id:number }) {
  if (!confirm('ลบบทสนทนานี้?')) return
  try {
    await deleteConversation(c.id)
    closeMenu()                 // ✅ ลบแล้วปิดเมนู
    await refreshConversations()
    if (!conversationId.value && conversations.value[0]) {
      await openConversation(conversations.value[0].id)
    } else if (!conversations.value.length) {
      messages.value = []
    }
  } catch (e) {
    alert('ลบไม่สำเร็จ')
  }
}
</script>

<template>
  <!-- ใช้ h-dvh + overflow-hidden กันล้นจอ, คุมสกรอลล์เฉพาะกล่องภายใน -->
  <div class="mx-auto max-w-6xl h-[85dvh] rounded-2xl border bg-white shadow-sm grid grid-cols-1 md:grid-cols-[280px_1fr] overflow-hidden">
    <!-- Sidebar -->
    <aside class="hidden md:flex min-h-0 flex-col border-r">
      <div class="px-3 py-3 border-b flex items-center gap-2">
        <div class="font-heading font-semibold">บทสนทนา</div>
        <button @click="onNewChat" class="ml-auto text-sm px-3 py-1 rounded-lg border hover:bg-gray-50">เริ่มใหม่</button>
      </div>
<div class="flex-1 min-h-0 overflow-y-auto">
  <div
    v-for="c in conversations"
    :key="c.id"
    class="relative px-3 py-3 border-b hover:bg-gray-50 cursor-pointer flex items-start gap-2 group"
    :class="isSelected(c.id) ? 'bg-gray-100' : ''"
    @click="openConversation(c.id)"
    data-menu-root
  >
    <div class="w-9 h-9 rounded-full bg-sky-500 text-white grid place-items-center text-xs font-semibold shrink-0">
      AI
    </div>

    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <div class="font-medium truncate">{{ c.title || 'Untitled' }}</div>

        <!-- ปุ่ม ⋮ : โชว์เสมอในจอเล็ก-กลาง, ซ่อนจน hover เฉพาะจอใหญ่ (xl ขึ้นไป) -->
        <button
          class="ml-auto shrink-0 rounded p-1 hover:bg-gray-100
                 opacity-100
                 xl:opacity-0 xl:group-hover:opacity-100
                 focus:opacity-100 focus-visible:opacity-100
                 transition-opacity"
          @click.stop="toggleMenu(c.id)"
          :aria-expanded="openMenuId === c.id"
          aria-haspopup="menu"
          title="เมนู"
        >
          <span class="sr-only">เมนู</span>
          <!-- Ellipsis Vertical (⋮) -->
          <svg class="w-5 h-5 text-gray-500" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 6.75a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5zm0 6.5a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5zm0 6.5a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5z" fill="currentColor"/>
          </svg>
        </button>
      </div>

      <div class="text-xs text-gray-500 truncate">{{ c.last_preview }}</div>
    </div>

    <!-- Dropdown เมนู -->
    <div
      v-if="openMenuId === c.id"
      class="absolute right-2 top-11 z-20 w-44 rounded-lg border bg-white shadow-lg p-1"
      role="menu"
    >
      <!-- เปลี่ยนชื่อ -->
      <button
        class="w-full text-left px-3 py-2 rounded flex items-center gap-2 hover:bg-gray-50 text-sm"
        @click.stop="onRename(c)"
        role="menuitem"
      >
        <!-- ไอคอนดินสอ -->
        <svg class="w-4 h-4 text-gray-600" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M4 15.5V20h4.5L19 9.5 14.5 5 4 15.5z" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <path d="M13 6l5 5" stroke="currentColor" stroke-width="1.5"/>
        </svg>
        <span>เปลี่ยนชื่อ</span>
      </button>

      <!-- ลบ -->
      <button
        class="w-full text-left px-3 py-2 rounded flex items-center gap-2 hover:bg-gray-50 text-sm text-red-600"
        @click.stop="onDelete(c)"
        role="menuitem"
      >
        <!-- ไอคอนถังขยะ -->
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M6 7h12M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2M8 7l1 12a1 1 0 001 1h4a1 1 0 001-1l1-12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <span>ลบ</span>
      </button>
    </div>
  </div>
</div>


    </aside>

    <!-- Chat Column -->
    <div class="relative flex min-h-0 flex-col">
      <!-- Header -->
      <div class="px-4 py-3 border-b flex items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-sky-500 text-white grid place-items-center text-sm font-semibold">AI</div>
        <div class="font-medium truncate">Assistant</div>
        <div class="ml-auto flex items-center gap-2">
          <select v-model="model" class="rounded-lg border px-2 py-1 text-sm">
            <option value="llama3.1">llama3.1</option>
            <option value="llama2">llama2</option>
          </select>
          <button @click="onNewChat" class="text-sm px-3 py-1 rounded-lg border hover:bg-gray-50">เริ่มแชทใหม่</button>
        </div>
      </div>

      <!-- Messages (พื้นที่สกรอลล์หลัก) -->
      <div
        ref="chatBox"
        class="flex-1 min-h-0 overflow-y-auto px-3 py-4 space-y-3 bg-gray-50"
      >
        <template v-for="m in messages" :key="m.id">
          <div v-if="m.role === 'system'" class="text-center text-xs text-gray-500">
            {{ m.content }}
          </div>

          <div v-else-if="m.role === 'assistant'" class="flex items-end gap-2">
            <div class="w-8 h-8 rounded-full bg-sky-500 text-white grid place-items-center text-xs font-semibold">AI</div>
            <div class="max-w-[80%]">
              <div class="rounded-2xl rounded-bl-sm bg-white border px-4 py-2 text-gray-900 whitespace-pre-wrap">
                {{ m.content }}
                <span v-if="m.streaming" class="inline-block animate-pulse">▋</span>
              </div>
              <div class="text-[11px] text-gray-400 mt-1">{{ fmtTime(m.ts) }}</div>
            </div>
          </div>

          <div v-else class="flex items-end gap-2 justify-end">
            <div class="max-w-[80%] text-right">
              <div class="rounded-2xl rounded-br-sm bg-sky-500 text-white px-4 py-2 whitespace-pre-wrap">
                {{ m.content }}
              </div>
              <div class="text-[11px] text-gray-400 mt-1">{{ fmtTime(m.ts) }}</div>
            </div>
            <div class="w-8 h-8 rounded-full bg-gray-300 text-gray-700 grid place-items-center text-xs font-semibold">U</div>
          </div>
        </template>

        <div v-if="error" class="text-center text-xs text-red-600">{{ error }}</div>
      </div>

      <!-- Composer (ไม่อยู่ในพื้นที่สกรอลล์) -->
      <div class="p-3 border-t bg-white">
        <div class="flex items-end gap-2">
          <textarea
            v-model="input"
            @keydown="onKeydown"
            rows="1"
            class="flex-1 resize-y rounded-xl border px-3 py-2 outline-none focus:ring focus:ring-indigo-100"
            placeholder="พิมพ์ข้อความ (Enter เพื่อส่ง, Shift+Enter ขึ้นบรรทัดใหม่)"
          />
          <button
            :disabled="loading || !input.trim()"
            @click="onSend"
            class="rounded-xl bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
          >
            {{ loading ? 'กำลังพิมพ์…' : 'ส่ง' }}
          </button>
          <button
            :disabled="!loading"
            @click="onStop"
            class="rounded-xl border px-3 py-2 disabled:opacity-50"
          >
            หยุด
          </button>
        </div>
      </div>

      <!-- ปุ่มเลื่อนไปล่าสุด (โผล่เมื่อผู้ใช้เลื่อนขึ้น) -->
      <button
        v-show="showJumpBtn"
        @click="jumpToLatest"
        class="absolute right-4 bottom-20 md:bottom-24 rounded-full border bg-white/90 backdrop-blur px-3 py-1 text-sm shadow hover:bg-white"
        title="เลื่อนไปข้อความล่าสุด"
      >
        ไปล่าสุด ↓
      </button>
    </div>
  </div>
</template>
