// src/composables/useAuth.ts
import { computed } from 'vue'
import { useStorage } from '@vueuse/core'
import { api } from '@/services/api'

type User = { id: number; name: string; email: string }
const token = useStorage<string | null>('token', null)   //  ใช้ key 'token' เดียว
const refreshToken = useStorage<string | null>('refresh_token', null)
const user  = useStorage<User | null>('user', null)

export function useAuth() {
  const isAuthenticated = computed(() => !!token.value)

  async function login(email: string, password: string) {
    const { data } = await api.post('/auth/login', { email, password })
    // รองรับทั้ง BE ส่ง token หรือ access_token
    const tok = data.token ?? data.access_token
    if (!tok) throw new Error('No token returned')

    token.value = tok
    refreshToken.value = data.refresh_token ?? null
    user.value  = data.user ?? null  // ถ้า BE ไม่ส่ง user มาก็ปล่อย null ไว้ แล้วไป /auth/me ทีหลัง

    //  ตั้ง header ให้ axios ใช้ในทุกคำขอ
    api.defaults.headers.common['Authorization'] = `Bearer ${tok}`
    ;(api.defaults.headers as any)['Authorization'] = `Bearer ${tok}`
    localStorage.setItem('token', tok) // กันพลาด ใช้ key เดียวกับ useStorage
     if (refreshToken.value) localStorage.setItem('refresh_token', refreshToken.value)
  }

    async function refresh() {
      const rt = refreshToken.value || localStorage.getItem('refresh_token')
      if (!rt) throw new Error('No refresh token')
      const { data } = await api.post('/auth/refresh', {}, { headers: { Authorization: `Bearer ${rt}` } })
      const tok = data.token
      token.value = tok
      api.defaults.headers.common['Authorization'] = `Bearer ${tok}`
      ;(api.defaults.headers as any)['Authorization'] = `Bearer ${tok}`
      localStorage.setItem('token', tok)
      return tok
  }

  function logout() {
    token.value = null
    user.value  = null
    delete api.defaults.headers.common['Authorization']
    delete (api.defaults.headers as any)['Authorization']
    localStorage.removeItem('token'); localStorage.removeItem('refresh_token')
  }

  // เรียกตอนแอปรันใหม่ เพื่อกู้ header จาก localStorage
  function initAuthHeader() {
    const tok = token.value || localStorage.getItem('token')
    if (tok) {
      api.defaults.headers.common['Authorization'] = `Bearer ${tok}`
      ;(api.defaults.headers as any)['Authorization'] = `Bearer ${tok}`
    }
  }

  return { token, user, isAuthenticated, login, logout, initAuthHeader, refresh, refreshToken }
}
