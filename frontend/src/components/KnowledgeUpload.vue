<script setup lang="ts">
import { ref, onMounted } from "vue";
import { uploadFile, listFiles } from "@/services/api";

const files = ref<string[]>([]);
const uploading = ref(false);
const error = ref("");

async function refresh() {
  const { data } = await listFiles();
  files.value = data.files || [];
}

async function onPick(e: Event) {
  const input = e.target as HTMLInputElement;
  if (!input.files || !input.files[0]) return;
  uploading.value = true;
  error.value = "";
  try {
    await uploadFile(input.files[0]);
    await refresh();
  } catch (e: any) {
    error.value = e?.response?.data?.error || e.message;
  } finally {
    uploading.value = false;
    (e.target as HTMLInputElement).value = "";
  }
}

onMounted(refresh);
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <label class="px-3 py-2 bg-gray-100 rounded-xl cursor-pointer hover:bg-gray-200 text-sm">
        <input type="file" class="hidden" accept=".txt,.md,.pdf,.docx" @change="onPick" />
        อัปโหลดไฟล์ (.txt .md .pdf .docx)
      </label>
      <span v-if="uploading" class="text-sm">กำลังอัปโหลด...</span>
      <span v-if="error" class="text-sm text-red-600">{{ error }}</span>
    </div>

    <div>
      <h3 class="text-sm font-medium mb-2">ไฟล์ในคลังความรู้</h3>
      <ul class="text-sm list-disc pl-6 space-y-1">
        <li v-for="f in files" :key="f">{{ f }}</li>
      </ul>
    </div>
  </div>
</template>