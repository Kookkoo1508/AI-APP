// src/services/api.ts
import axios from 'axios'
import { useAuth } from '@/composables/useAuth'

export const api = axios.create({
  baseURL: '/api', // Vite proxy → Flask (localhost:8000)
  timeout: 300000,
})

/** ---------- Token helpers (ให้ที่อื่นเรียกใช้ได้ด้วย) ---------- */
export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem('token', token)
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    ;(api.defaults.headers as any)['Authorization'] = `Bearer ${token}` // เผื่อบางเวอร์ชัน
  } else {
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
    if ((api.defaults.headers as any)['Authorization']) {
      delete (api.defaults.headers as any)['Authorization']
    }
  }
}

export function getAuthHeader(): string | undefined {
  return (
    (api.defaults.headers as any)?.common?.Authorization ||
    (api.defaults.headers as any)?.Authorization ||
    undefined
  )
}

/** ---------- Bootstrap token ครั้งแรก ---------- */
const saved = localStorage.getItem('token')
if (saved) setAuthToken(saved)

/** ---------- Files / Knowledge Base ---------- */
export const uploadFile = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/files/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** ---------- Delete Files / Knowledge Base ---------- */
export function deleteFile(name: string) {
  // ถ้าชื่อไฟล์มีช่องว่าง/อักขระพิเศษ ควรเข้ารหัส
  return api.delete('/files/delete', { params: { name } });
  // หรือถ้าเป็น path: return api.delete(`/ai/files/${encodeURIComponent(name)}`);
}
export const listFiles = () => api.get('/files/list')

export const searchKB = (query: string, k = 5) =>
  api.post('/files/search', { query, k })

/** ---------- 401 Refresh (กันลูป/ยิงซ้ำให้ถูกต้อง) ---------- */
let isRefreshing = false
let pending: Array<(t: string) => void> = []

function onRefreshed(tok: string) {
  pending.forEach((cb) => cb(tok))
  pending = []
}

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const { response, config } = err
    if (!response) throw err

    // ป้องกันวนลูป
    if (response.status !== 401 || (config as any)._retry) {
      throw err
    }

    const { refresh } = useAuth()

    if (!isRefreshing) {
      isRefreshing = true
      try {
        const newTok = await refresh()
        // ✅ อัปเดต axios defaults + localStorage ทันที
        setAuthToken(newTok)
        isRefreshing = false
        onRefreshed(newTok)
      } catch (e) {
        isRefreshing = false
        pending = []
        // ล้าง token ทิ้ง ป้องกันสถานะเพี้ยน
        setAuthToken(null)
        throw err
      }
    }

    // รอจน refresh เสร็จ แล้ว retry คำขอเดิมด้วย token ใหม่
    const newTok = await new Promise<string>((resolve) => pending.push(resolve))
    ;(config as any)._retry = true
    config.headers = {
      ...(config.headers || {}),
      Authorization: `Bearer ${newTok}`,
    }
    return api.request(config)
  }
)
