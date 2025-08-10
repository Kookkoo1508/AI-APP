<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ msg: string }>()
const count = ref(0)
</script>

<template>
  <section class="p-6 space-y-6">
    <h1 class="text-2xl font-semibold">{{ msg }}</h1>

    <div class="rounded-2xl border p-6 shadow-sm bg-white/50 dark:bg-neutral-900/50">
      <p class="mb-4 text-sm text-neutral-600">ตัวอย่างปุ่มที่สไตล์ด้วย Tailwind</p>

      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-xl px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 active:scale-[.98] focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
        @click="count++"
      >
        count is {{ count }}
      </button>

      <p class="mt-4 text-xs text-neutral-500">
        เคล็ดลับ: ถ้าปุ่มไม่ดูเหมือนปุ่ม ให้เพิ่มคลาส Tailwind เอง เพราะ preflight จะล้างสไตล์เริ่มต้นของเบราว์เซอร์
      </p>
    </div>
  </section>
</template>
