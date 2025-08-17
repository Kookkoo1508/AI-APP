<script setup lang="ts">
import { ref, onMounted } from "vue";
import { uploadFile, listFiles, deleteFile } from "@/services/api"; // ✅ เพิ่ม deleteFile

const files = ref<string[]>([]);
const uploading = ref(false);
const loading = ref(false);
const error = ref("");

async function refresh() {
  loading.value = true;
  error.value = "";
  try {
    const { data } = await listFiles();
    files.value = data?.files || [];
  } catch (e: any) {
    error.value = e?.response?.data?.error || e.message || "โหลดรายการไฟล์ไม่สำเร็จ";
  } finally {
    loading.value = false;
  }
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
    error.value = e?.response?.data?.error || e.message || "อัปโหลดไม่สำเร็จ";
  } finally {
    uploading.value = false;
    (e.target as HTMLInputElement).value = "";
  }
}

async function onDelete(name: string) {
  if (!confirm(`ต้องการลบไฟล์นี้ออกจากคลังความรู้?\n\n${name}`)) return;
  error.value = "";
  try {
    await deleteFile(name);
    // อัปเดตรายการแบบทันที เพื่อให้ UI ตอบสนองไว
    files.value = files.value.filter(f => f !== name);
    // กันหลุด sync ถ้า backend มี side-effect อื่น ๆ
    await refresh();
  } catch (e: any) {
    error.value = e?.response?.data?.error || e.message || "ลบไฟล์ไม่สำเร็จ";
  }
}

onMounted(refresh);
</script>

<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex flex-wrap items-center gap-3">
      <!-- Upload button -->
      <label
        class="inline-flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer
               bg-gray-100 hover:bg-gray-200 text-sm transition"
        :class="{ 'opacity-60 pointer-events-none': uploading || loading }"
        title="อัปโหลดไฟล์เข้าสู่คลังความรู้"
      >
        <input
          type="file"
          class="hidden"
          accept=".txt,.md,.pdf,.docx"
          @change="onPick"
          :disabled="uploading || loading"
        />
        <!-- upload icon -->
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6H16a4 4 0 010 8H7z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 12v9m0 0l-3-3m3 3l3-3M12 12l-3 3m3-3l3 3"/>
        </svg>
        <span>อัปโหลดไฟล์ (.txt .md .pdf .docx)</span>
      </label>

      <!-- Refresh button -->
      <button
        @click="refresh"
        class="inline-flex items-center gap-2 px-3 py-2 rounded-xl border text-sm hover:bg-gray-50 transition"
        :disabled="loading || uploading"
        title="ดึงรายการไฟล์ล่าสุด"
      >
        <svg xmlns="http://www.w3.org/2000/svg"
             class="h-4 w-4 shrink-0"
             :class="{ 'animate-spin': loading }"
             viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v6h6M20 20v-6h-6"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M20 8a8 8 0 10.001 8.001V8z"/>
        </svg>
        <span>{{ loading ? 'กำลังโหลด…' : 'รีเฟรช' }}</span>
      </button>

      <!-- Status text -->
      <span v-if="uploading" class="text-sm text-gray-600">กำลังอัปโหลด…</span>
      <span v-if="error" class="text-sm text-red-600">{{ error }}</span>
    </div>

    <!-- List -->
    <div class="rounded-xl border bg-white">
      <div class="flex items-center justify-between px-4 py-3 border-b">
        <h3 class="text-sm font-medium">ไฟล์ในคลังความรู้</h3>
        <span v-if="!loading && files.length" class="text-xs text-gray-500">ทั้งหมด {{ files.length }} ไฟล์</span>
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="p-4 text-sm text-gray-600">
        กำลังโหลดรายการไฟล์…
      </div>

      <!-- Empty state -->
      <div v-else-if="!files.length" class="p-6 text-center text-sm text-gray-500">
        ยังไม่มีไฟล์ในคลังความรู้
        <div class="mt-2 text-gray-400">อัปโหลดไฟล์ได้จากปุ่มด้านบน</div>
      </div>

      <!-- Files list -->
      <ul v-else class="divide-y">
        <li v-for="f in files" :key="f" class="flex items-center justify-between gap-3 px-4 py-3">
          <div class="flex items-center gap-2 min-w-0">
            <!-- file icon -->
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 flex-none text-gray-500" viewBox="0 0 24 24" fill="currentColor">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"/>
              <path d="M14 2v6h6"/>
            </svg>
            <span class="truncate text-sm">{{ f }}</span>
          </div>

          <div class="flex items-center gap-2">
            <!-- delete button -->
            <button
              @click="onDelete(f)"
              class="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-sm text-red-600 hover:bg-red-50 transition"
              :disabled="loading || uploading"
              title="ลบไฟล์นี้ออกจากคลังความรู้"
            >
              <!-- trash icon -->
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7h6m-7 0h8m-3-3h-2a1 1 0 00-1 1v2h4V5a1 1 0 00-1-1z"/>
              </svg>
              <span>ลบ</span>
            </button>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>
