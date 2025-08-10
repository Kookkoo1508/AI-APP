<script setup lang="ts">
import { onMounted } from 'vue'
import { useInbox } from '@/composables/useInbox'
const { archive, fetchArchive } = useInbox()
onMounted(fetchArchive)
</script>

<template>
  <div class="rounded-2xl border bg-white p-4 shadow-sm">
    <div class="mb-3 font-semibold">Archive</div>
    <ul class="space-y-2">
      <li v-for="t in archive" :key="t.id" class="rounded-lg border p-3">
        <div class="font-medium">{{ t.title }}</div>
        <div class="text-xs text-neutral-500" v-if="t.notes">{{ t.notes }}</div>
      </li>
    </ul>
  </div>
</template>
