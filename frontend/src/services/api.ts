import axios from 'axios'
import { useAuth } from '@/composables/useAuth'

export const api = axios.create({
  baseURL: '/api', // Vite proxy → Flask (localhost:8000)
  timeout: 30000,
})

// แนบ Authorization header ถ้ามี token
// api.interceptors.request.use((config) => {
//   const token = localStorage.getItem('token')
//   if (token) {
//     config.headers.Authorization = `Bearer ${token}`
//   }
//   return config
// })


// กู้ header ถ้ามี token ใน localStorage (กันพลาด)
const saved = localStorage.getItem('token')
if (saved) {
  api.defaults.headers.common['Authorization'] = `Bearer ${saved}`
  ;(api.defaults.headers as any)['Authorization'] = `Bearer ${saved}`
}

let isRefreshing = false
let pending: Array<(t: string) => void> = []

function onRefreshed(tok: string) { pending.forEach(cb => cb(tok)); pending = [] }

api.interceptors.response.use(
  res => res,
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
        isRefreshing = false
        onRefreshed(newTok)
      } catch (e) {
        isRefreshing = false
        pending = []
        throw err
      }
    }

    // รอจน refresh เสร็จ แล้ว retry คำขอเดิม
    const newTok = await new Promise<string>(resolve => pending.push(resolve))
    ;(config as any)._retry = true
    config.headers = { ...(config.headers || {}), Authorization: `Bearer ${newTok}` }
    return api.request(config)
  }
)