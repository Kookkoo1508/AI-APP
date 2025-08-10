<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useInbox } from '@/composables/useInbox'

const title = ref('')
const notes = ref('')
const { tasks, loading, fetchTasks, createTask, updateTask, archiveTask } = useInbox()

onMounted(fetchTasks)

async function onAdd() {
  if (!title.value.trim()) return
  await createTask(title.value, notes.value || undefined)
  title.value = ''; notes.value = ''
}
</script>

<template>
  <div class="space-y-4">
    <div class="rounded-2xl border bg-white p-4 shadow-sm">
      <div class="flex gap-2">
        <input v-model="title" placeholder="ชื่องาน…" class="flex-1 rounded-lg border px-3 py-2" />
        <input v-model="notes" placeholder="โน้ต (ถ้ามี)" class="flex-1 rounded-lg border px-3 py-2" />
        <button class="rounded-lg bg-slate-900 px-4 py-2 text-white" @click="onAdd">เพิ่ม</button>
      </div>
    </div>

    <div class="rounded-2xl border bg-white p-4 shadow-sm">
      <div class="mb-3 font-semibold">งานทั้งหมด</div>
      <div v-if="loading" class="text-sm text-neutral-500">กำลังโหลด…</div>
      <ul class="space-y-2">
        <li v-for="t in tasks" :key="t.id" class="flex items-center justify-between rounded-lg border p-3">
          <div class="flex items-center gap-3">
            <input type="checkbox" :checked="t.is_done" @change="updateTask(t.id, { is_done: !t.is_done })" />
            <div>
              <div class="font-medium" :class="t.is_done ? 'line-through text-neutral-400' : ''">{{ t.title }}</div>
              <div class="text-xs text-neutral-500" v-if="t.notes">{{ t.notes }}</div>
            </div>
          </div>
          <div class="flex gap-2">
            <button class="rounded-md border px-2 py-1 text-sm" @click="archiveTask(t.id)">Archive</button>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>
