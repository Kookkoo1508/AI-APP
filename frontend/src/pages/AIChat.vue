<!-- src/pages/AIChat.vue -->
<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useAI } from '@/composables/useAI'
import { ArrowPathIcon } from '@heroicons/vue/24/outline'
import type { ApiMsgDTO } from '@/types/chat'

type Role = 'user' | 'assistant' | 'system'
type Msg = { id: number; role: Role; content: string; ts: number; streaming?: boolean ; citations?: string[]}
type ConvItem = { id: number; title: string; created_at: string; last_preview: string }
// type ApiMsg = { id:number; role:Role; content:string; created_at:string }

const input = ref('')
// const model = ref('llama3.2')
const chatBox = ref<HTMLDivElement | null>(null)
const messages = ref<Msg[]>([])
const conversations = ref<ConvItem[]>([])
let mid = 0
const useKB = ref(true)          // ✅ สวิตช์ใช้ความรู้
const topk = ref(5)   

const atBottom = ref(true) // อยู่ล่างสุดหรือไม่ (ไว้ควบคุม autoscroll)
const showJumpBtn = ref(false)


const {
  loading, error, streamChat, stop,
  conversationId, newConversation,
  listConversations, loadMessages,
  renameConversation, deleteConversation,
  knowledgeSources, getModels
} = useAI()

const models = ref<string[]>([])
const modelsLoading = ref(false)
const modelsError = ref<string | null>(null)
const model = ref('')   // ตัวเลือกปัจจุบัน

async function refreshModels() {
  modelsLoading.value = true
  modelsError.value = null
  try {
    const list = await getModels()
    if (list.length) {
      models.value = list
      if (!list.includes(model.value)) {
        model.value = list[0]
      }
    } else {
      modelsError.value = 'ไม่พบโมเดล'
      if (!model.value) model.value = 'llama3.2'
    }
  } catch (err: any) {
    modelsError.value = err?.message || 'โหลดโมเดลล้มเหลว'
  } finally {
    modelsLoading.value = false
  }
}

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

onMounted(async () => {
  // จัดการ event global
  document.addEventListener('click', onDocClick, { passive: true })
  document.addEventListener('keydown', onEsc)

  // จัดการ conversations
  await refreshConversations()

  refreshModels()

  // scroll event
  chatBox.value?.addEventListener('scroll', handleScroll, { passive: true })

  // scroll ไปล่างสุด
  await nextTick()
  await scrollToBottom(true)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onEsc)
  chatBox.value?.removeEventListener('scroll', handleScroll)
  // stop()
})

watch(conversationId, async (val, old) => {
  if (!val || val === old) return
  // อย่าแทรกระหว่างสตรีม/พิมพ์
  if (loading.value) return
  if (messages.value.some(m => m.streaming)) return
  await openConversation(val)
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

// async function openConversation(convId: number) {
//   const items: ApiMsg[] = await loadMessages(convId)
//   messages.value = items.map(m => ({
//     id: m.id,
//     role: m.role,
//     content: m.content,
//     ts: new Date(m.created_at).getTime(),
//   }))
//   mid = Math.max(0, ...messages.value.map(m => m.id)) + 1
//   await scrollToBottom(true)
// }
// frontend/src/pages/AIChat.vue (เฉพาะฟังก์ชัน)
async function openConversation(convId: number) {
  let items: ApiMsgDTO[]
  try {
    items = await loadMessages(convId)
  } catch (e: any) {
    if (e?.message === 'AUTH_EXPIRED') {
      // 👉 ทำอย่างใดอย่างหนึ่ง:
      // - เด้งไปหน้า login
      // - หรือเรียก refresh-token แล้ว retry (ดูข้อ 3)
      alert('เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่')
      // router.push({ name: 'login' })
      return
    }
    if (e?.message === 'CONVERSATION_NOT_FOUND') {
      alert('ไม่พบบทสนทนา อาจถูกลบไปแล้ว')
      return
    }
    console.error('openConversation error:', e)
    alert('เกิดข้อผิดพลาดในการโหลดข้อความ')
    return
  }

  // ✅ ณ จุดนี้ items เป็น Array แน่นอน
  messages.value = items.map(m => ({
    id: m.id,
    role: m.role as Role,
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
    await streamChat(
      text,
      { model: model.value, useKnowledge: useKB.value, topk: topk.value }, // ✅ ส่งค่า RAG
      async (delta) => {
        const m = messages.value.find(m => m.id === aid)
        if (!m) return
        m.content += delta
        await scrollToBottom()
      }
    )
  } catch (e) {
    messages.value.push({ id: ++mid, role: 'system', content: String(e), ts: Date.now() })
  } finally {

    const m = messages.value.find(m => m.id === aid)

    if (m) {
      m.streaming = false
      // ยึดรายการไฟล์อ้างอิงที่ใช้ในคำตอบนี้ (ไม่ให้เปลี่ยนตาม state รอบถัดไป)
      if (Array.isArray(knowledgeSources.value) && knowledgeSources.value.length) {
        m.citations = [...knowledgeSources.value]
      }
    }
    await scrollToBottom()
    // if (wasNew && conversationId.value) await refreshConversations()
    if (wasNew && conversationId.value) {
      await refreshConversations()
      // await openConversation(conversationId.value)
    }
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

async function onDelete(c: { id: number }) {
  if (!confirm('ลบบทสนทนานี้?')) return

  const deletedId = c.id

  // ลบบนเซิร์ฟเวอร์
  try {
    await deleteConversation(deletedId)
  } catch (e) {
    alert('ลบไม่สำเร็จ')        // พังจริง ๆ ตอนลบ
    return
  }

  // ลบใน UI ทันที + ปิดเมนู
  closeMenu()
  conversations.value = conversations.value.filter(x => x.id !== deletedId)

  // ถ้ากำลังเปิดห้องที่เพิ่งลบอยู่ ให้เคลียร์หน้าจอ
  if (conversationId.value === deletedId) {
    conversationId.value = null
    messages.value = []
  }

  // พยายาม refresh (ถ้า fail อย่าโยน error ไปโชว์ "ลบไม่สำเร็จ")
  try {
    await refreshConversations()
  } catch (e) {
    console.warn('refreshConversations failed:', e)
  }

  // ถ้ายังไม่มีห้องที่เปิดอยู่ ให้เปิดห้องแรกถ้ามี
  if (!conversationId.value && conversations.value[0]) {
    try {
      await openConversation(conversations.value[0].id)
    } catch (e) {
      console.warn('openConversation failed:', e)
    }
  } else if (!conversations.value.length) {
    messages.value = []
  }
}

// ---- Citation helpers ----
type ParsedCitation = { page?: number|null; section?: string|null; name: string }

function parseCitation(s: string): ParsedCitation {
  // รองรับ 3 รูปแบบ: "p.35 • file", "§Intro • file", "file p.35"
  const t = (s || '').trim()

  // p.xx • filename
  const m1 = t.match(/^p\.?\s*(\d+)\s*•\s*(.+)$/i)
  if (m1) return { page: Number(m1[1]), section: null, name: m1[2].trim() }

  // §section • filename
  const m2 = t.match(/^§\s*([^•]+?)\s*•\s*(.+)$/)
  if (m2) return { page: null, section: m2[1].trim(), name: m2[2].trim() }

  // filename p.xx  (แบบเก่า)
  const m3 = t.match(/^(.+?)\s+p\.?\s*(\d+)$/i)
  if (m3) return { page: Number(m3[2]), section: null, name: m3[1].trim() }

  // อย่างน้อยให้ชื่อไฟล์แสดงได้
  return { page: null, section: null, name: t }
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
        <div class="ml-auto flex items-center gap-3">
          <!-- ✅ สวิตช์ใช้ความรู้ -->
          <label class="inline-flex items-center gap-1 text-sm">
            <input type="checkbox" v-model="useKB" class="rounded" />
            ใช้ความรู้ (RAG)
          </label>
          <label v-if="useKB" class="inline-flex items-center gap-1 text-sm">
            top-k
            <input type="number" v-model.number="topk" min="1" max="20" class="w-16 border rounded px-1 py-0.5 text-sm" />
          </label>

          <select
            v-model="model"
            class="rounded-lg border px-2 py-1 text-sm min-w-40"
            :disabled="modelsLoading"
          >
            <option v-if="modelsLoading" disabled>กำลังโหลดโมเดล…</option>
            <option v-else-if="modelsError" :value="model || 'llama3.2'">
              {{ modelsError }} (ใช้ {{ model || 'llama3.2' }})
            </option>
            <option v-for="m in models" :key="m" :value="m">
              {{ m }}
            </option>
            <!-- เผื่อกรณีแบ็กเอนด์คืนว่างจริง ๆ -->
            <option v-if="!modelsLoading && !modelsError && !models.length" value="llama3.2">
              llama3.1
            </option>
          </select>
          <button
            @click="refreshModels"
            class="rounded-lg border px-1 text-sm flex items-start justify-start gap-1 hover:bg-gray-50"
            :disabled="modelsLoading"
            title="ดึงรายการโมเดลใหม่"
          >
            <ArrowPathIcon
              class="h-5 w-5"
              :class="{ 'animate-spin': modelsLoading }"
            />
          </button>

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

                <!-- ✅ Citation ใต้คำตอบ (รองรับ p.xx • filename, §section • filename, และไฟล์ p.xx) -->
                <div v-if="m.citations?.length" class="mt-1 text-[11px] text-gray-500 flex items-center gap-2">
                  <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M7 7h10v10H7z" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M9.5 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                  </svg>
                  <span>อ้างอิง:</span>
                  <ul class="inline-flex flex-wrap gap-1">
                    <li
                      v-for="(s, i) in m.citations"
                      :key="i"
                      class="inline-flex items-center gap-1 border rounded-lg px-1.5 py-0.5 bg-white shadow-sm"
                      :title="s"
                    >
                      <!-- แสดง p.xx หรือ §section เป็น badge ด้านซ้าย (shrink-0) -->
                      <template v-if="parseCitation(s).page != null">
                        <span class="shrink-0 px-1 rounded bg-gray-100 border text-[10px] leading-none">
                          p.{{ parseCitation(s).page }}
                        </span>
                      </template>
                      <template v-else-if="parseCitation(s).section">
                        <span class="shrink-0 px-1 rounded bg-gray-100 border text-[10px] leading-none">
                          §{{ parseCitation(s).section }}
                        </span>
                      </template>

                      <!-- ชื่อไฟล์: truncate เพื่อไม่บังเลขหน้า -->
                      <span class="truncate max-w-[12rem]">
                        {{ parseCitation(s).name }}
                      </span>
                    </li>
                  </ul>
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
