<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref<string | null>(null)

const router = useRouter()
const route = useRoute()
const { login } = useAuth()

async function onSubmit() {
  errorMsg.value = null
  loading.value = true
  try {
    await login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.replace(redirect)
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.message || 'เข้าสู่ระบบไม่สำเร็จ'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="min-h-screen grid place-items-center bg-gray-50">
    <div class="w-full max-w-md rounded-2xl border bg-white p-6 shadow">
      <h1 class="mb-6 text-2xl font-semibold">เข้าสู่ระบบ</h1>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <div>
          <label class="mb-1 block text-sm font-medium">อีเมล</label>
          <input
            v-model="email"
            type="email"
            required
            class="w-full rounded-lg border px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium">รหัสผ่าน</label>
          <input
            v-model="password"
            type="password"
            required
            class="w-full rounded-lg border px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="••••••••"
          />
        </div>

        <button
          :disabled="loading"
          class="w-full rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {{ loading ? 'กำลังเข้าสู่ระบบ...' : 'เข้าสู่ระบบ' }}
        </button>

        <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
      </form>
    </div>
  </main>
</template>
