import { ref } from 'vue'
import { nextTick, onUnmounted } from 'vue'
import { api } from '@/services/api' // axios baseURL: '/api'

export function useAI() {
  const loading = ref(false)
  const reply = ref<string>('')
  const error = ref<string | null>(null)
  const conversationId = ref<number | null>(null)
  let controller: AbortController | null = null

  async function chat(message: string, model = 'llama3.1') {
    loading.value = true
    try {
      const { data } = await api.post('/ai/chat', { message, model })
      reply.value = data.reply
    } finally {
      loading.value = false
    }
  }

  async function embeddings(text: string, model = 'nomic-embed-text') {
    const { data } = await api.post('/ai/embeddings', { text, model })
    return data.embedding as number[]
  }

  async function streamChat(message: string, model = 'llama3.1', onDelta?: (chunk: string) => void) {
    loading.value = true
    error.value = null
    reply.value = ''

    // ถ้ามีสตรีมค้าง ให้ยกเลิกก่อน
    controller?.abort()
    controller = new AbortController()

    // ใช้ baseURL จาก axios เพื่อคง prefix '/api'
    const endpoint = `${api.defaults.baseURL ?? ''}/ai/chat/stream`
    const authHeader =
    // axios เก็บไว้ที่ common บางเวอร์ชัน
    (api.defaults.headers as any)?.common?.Authorization ||
    (api.defaults.headers as any)?.Authorization || undefined

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authHeader ? { Authorization: authHeader } : {}), // <<— สำคัญ
        },
        body: JSON.stringify({ message, model, conversation_id: conversationId.value }),
        signal: controller.signal,
      })

      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(`HTTP ${res.status}: ${text || res.statusText}`)
      }

      const reader = res.body?.getReader()
      if (!reader) throw new Error('ReadableStream not available')

      const decoder = new TextDecoder()

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value || new Uint8Array(), { stream: true })
        if (!chunk) continue

        // ถ้า backend ส่ง [ERROR] มากับสตรีม ให้หยุดทันที
        if (chunk.includes('[ERROR]')) {
          reply.value += chunk
          onDelta?.(chunk)
          throw new Error(chunk)
        }

        reply.value += chunk
        onDelta?.(chunk)
        await nextTick()
      }
    } catch (e: any) {
      error.value = e?.message || String(e)
    } finally {
      loading.value = false
      controller = null
    }
  }

  function stop() {
    controller?.abort()
    controller = null
    loading.value = false
  }

    // REST ช่วยดึง/เลือกบทสนทนา
  async function listConversations() {
    const { data } = await api.get('/ai/conversations')
    return data.items as Array<{ id:number; title:string; created_at:string; last_preview:string }>
  }

  async function loadMessages(convId: number) {
    conversationId.value = convId
    const { data } = await api.get('/ai/messages', { params: { conversation_id: convId } })
    return data.items as Array<{ id:number; role:'user'|'assistant'|'system'; content:string; created_at:string }>
  }

    async function renameConversation(id: number, title: string) {
    await api.patch(`/ai/conversations/${id}`, { title })
  }
  async function deleteConversation(id: number) {
    await api.delete(`/ai/conversations/${id}`)
    if (conversationId.value === id) conversationId.value = null
  }


  function newConversation() {
    conversationId.value = null
    reply.value = ''
  }

  onUnmounted(stop)

  return {
    loading, reply, error, embeddings,
    conversationId, newConversation,
    chat, streamChat, stop,
    listConversations, loadMessages,
    renameConversation, deleteConversation
  }
}