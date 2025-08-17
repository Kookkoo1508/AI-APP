// src/composables/useAI.ts
import { ref } from 'vue'
import { api, getAuthHeader } from '@/services/api'
import axios from 'axios'
import type { ApiMsgDTO } from '@/types/chat'

type StreamOpts = { model: string; useKnowledge: boolean; topk: number }

const loading = ref(false)
const error = ref<string | null>(null)

const conversationId = ref<number | null>(null)
const knowledgeSources = ref<string[]>([])

let controller: AbortController | null = null

function decodeB64JsonToArray(b64: string | null): string[] {
  if (!b64) return []
  try {
    const bin = atob(b64)
    const bytes = new Uint8Array([...bin].map(c => c.charCodeAt(0)))
    const json = new TextDecoder().decode(bytes)
    const val = JSON.parse(json)
    return Array.isArray(val) ? val : []
  } catch { return [] }
}

async function readTextStream(res: Response, onDelta: (s: string) => void) {
  const reader = res.body?.getReader()
  if (!reader) return
  const decoder = new TextDecoder()
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    onDelta(decoder.decode(value))
  }
}

async function streamChat(
  message: string,
  opts: StreamOpts,
  onDelta: (chunk: string) => void,
) {
  if (loading.value) return
  loading.value = true
  error.value = null
  knowledgeSources.value = [] // reset รอบใหม่

  controller?.abort()
  controller = new AbortController()

  try {
    // ดึง bearer จาก axios instance
    const auth = getAuthHeader()
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (auth) headers['Authorization'] = auth

    const res = await fetch('/api/ai/chat/stream', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model: opts.model,
        message,
        conversation_id: conversationId.value,
        use_knowledge: opts.useKnowledge,
        topk: opts.topk,
      }),
      credentials: 'include',
      signal: controller.signal,
    })

    if (!res.ok) {
      const t = await res.text().catch(() => '')
      throw new Error(t || `HTTP ${res.status}`)
    }

    // conversation id
    const convId = res.headers.get('X-Conversation-Id')
    if (convId) conversationId.value = Number(convId)

    // citations headers
    const b64 = res.headers.get('X-Knowledge-Sources-B64')
    const ascii = res.headers.get('X-Knowledge-Sources')
    const fromB64 = decodeB64JsonToArray(b64)
    if (fromB64.length) knowledgeSources.value = fromB64
    else if (ascii) knowledgeSources.value = ascii.split(',').map(s => s.trim()).filter(Boolean)

    const ragErr = res.headers.get('X-RAG-Error')
    if (ragErr) console.warn('RAG error:', ragErr)

    await readTextStream(res, onDelta)
  } catch (e: any) {
    if (e?.name !== 'AbortError') {
      console.error(e)
      error.value = String(e?.message || e)
    }
  } finally {
    loading.value = false
    controller = null
  }
}

function stop() {
  controller?.abort()
  controller = null
}

// ---------- REST ผ่าน axios api ----------
async function newConversation() {
  conversationId.value = null
}

async function listConversations() {
  const { data } = await api.get('/ai/conversations')
  return data
}

async function loadMessages(convId: number): Promise<ApiMsgDTO[]> {
  try {
    const { data, status } = await api.get('/ai/messages', {
      params: { conversation_id: convId },
    })

    //  ต้องเป็น 200 และ data.items เป็น Array
    if (status === 200 && Array.isArray(data?.items)) {
      return data.items as ApiMsgDTO[]
    }

    // รูปแบบไม่ถูกต้อง
    throw new Error(data?.error || data?.msg || 'Invalid response shape')
  } catch (err: any) {
    if (axios.isAxiosError(err) && err.response) {
      const { status, data } = err.response
      if (status === 401) {
        // token หมดอายุ → ให้โยน error เฉพาะ เพื่อให้ UI พาไป login/refresh
        throw new Error('AUTH_EXPIRED')
      }
      if (status === 404) {
        throw new Error('CONVERSATION_NOT_FOUND')
      }
      throw new Error(data?.error || data?.msg || `HTTP_${status}`)
    }
    throw err
  }
}

async function renameConversation(id: number, title: string) {
  await api.put(`/ai/conversations/${id}`, { title })
}

async function deleteConversation(id: number) {
  await api.delete(`/ai/conversations/${id}`)
}

async function getModels(): Promise<string[]> {
  try {
    const { data } = await api.get('/ai/models')   // => { models: [...] }
    const names: string[] = Array.isArray(data?.models) ? data.models : []
    return [...new Set(names.filter(Boolean))]     // unique + filter empty
  } catch (e: any) {
    console.error('โหลด models ไม่สำเร็จ', e)
    return []
  }
}

export function useAI() {
  return {
    // state
    loading, error,
    conversationId, knowledgeSources,

    // actions
    streamChat, stop,
    newConversation, listConversations,
    loadMessages, renameConversation, deleteConversation,
    getModels
  }
}
