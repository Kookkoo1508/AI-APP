<!-- src/components/AIStreamChat.vue -->
<template>
  <div class="mx-auto max-w-3xl p-4 space-y-4">
    <!-- Input Card -->
    <div class="bg-white rounded-2xl shadow border p-4">
      <div class="grid md:grid-cols-[1fr_180px] gap-3">
        <div>
          <label class="block text-sm text-gray-600 mb-2">Prompt</label>
          <textarea
            v-model="prompt"
            rows="4"
            class="w-full rounded-xl border p-3 outline-none focus:ring focus:ring-indigo-100"
            placeholder="พิมพ์คำถาม/คำสั่ง แล้วกด Ctrl/Cmd + Enter เพื่อส่ง"
            @keydown.enter.exact.prevent="sendOnEnter"
            @keydown.meta.enter.prevent="onSend"
            @keydown.ctrl.enter.prevent="onSend"
          />
        </div>

        <div class="flex flex-col gap-3">
          <div>
            <label class="block text-sm text-gray-600 mb-2">Model</label>
            <input
              v-model="model"
              class="w-full rounded-xl border p-2 outline-none focus:ring focus:ring-indigo-100"
              placeholder="llama3.1"
            />
          </div>

          <div class="flex gap-2">
            <button
              :disabled="loading || !prompt.trim()"
              @click="onSend"
              class="flex-1 rounded-xl px-4 py-2 bg-indigo-600 text-white disabled:opacity-50"
            >
              {{ loading ? "กำลังส่ง..." : "ส่ง" }}
            </button>
            <button
              :disabled="!loading"
              @click="onStop"
              class="rounded-xl px-4 py-2 bg-gray-200 text-gray-800 disabled:opacity-50"
            >
              หยุด
            </button>
            <button
              :disabled="loading && !reply"
              @click="onClear"
              class="rounded-xl px-4 py-2 bg-white border text-gray-700 disabled:opacity-50"
            >
              ล้าง
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Output Card -->
    <div class="bg-white rounded-2xl shadow border p-4">
      <div class="flex items-center justify-between mb-2">
        <label class="block text-sm font-medium text-gray-600">Output (streaming)</label>
        <button
          v-if="reply"
          @click="copyReply"
          class="text-sm px-3 py-1 rounded-lg border hover:bg-gray-50"
        >
          คัดลอก
        </button>
      </div>

      <div
        ref="scrollBox"
        class="min-h-[220px] max-h-[480px] overflow-y-auto whitespace-pre-wrap leading-relaxed font-mono text-[0.95rem]"
      >
        <div v-if="error" class="text-red-600 font-medium">{{ error }}</div>
        <div v-else-if="!reply && !loading" class="text-gray-400">ยังไม่มีผลลัพธ์</div>
        <div>{{ reply }}</div>
        <span v-if="loading" class="inline-block animate-pulse">▋</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onUnmounted } from 'vue'
import { useAI } from '@/composables/useAI' // ที่คุณแก้ไว้ก่อนหน้า (มี streamChat)

const prompt = ref('')
const model = ref('llama3.1')
const scrollBox = ref<HTMLDivElement | null>(null)

const { loading, reply, error, streamChat, stop } = useAI()

async function onSend() {
  const msg = prompt.value.trim()
  if (!msg) return
  // ล้างผลลัพธ์เก่า แล้วเริ่มสตรีมใหม่
  reply.value = ''
  await streamChat(msg, model.value, async () => {
    // auto-scroll ลงล่างสุดทุกครั้งที่มี chunk ใหม่
    await nextTick()
    if (scrollBox.value) {
      scrollBox.value.scrollTop = scrollBox.value.scrollHeight
    }
  })
}

function onStop() {
  stop()
}

function onClear() {
  reply.value = ''
  prompt.value = ''
}

function sendOnEnter(e: KeyboardEvent) {
  // กด Enter เดี่ยว ๆ ให้ขึ้นบรรทัดใหม่ (default)
  // ส่วน Ctrl/Cmd+Enter ถูกจับที่ textarea ด้านบนอยู่แล้ว
}

async function copyReply() {
  if (!reply.value) return
  await navigator.clipboard.writeText(reply.value)
}

onUnmounted(() => {
  // กันสตรีมค้างเมื่อออกจากหน้า
  stop()
})
</script>
