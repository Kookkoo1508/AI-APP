<script setup lang="ts"></script>
<template>
  <div class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
    <div class="rounded-2xl border bg-white p-6 shadow-sm">
      <h3 class="font-semibold">Welcome</h3>
      <p class="mt-2 text-sm text-neutral-600">
        นี่คือ Dashboard เริ่มต้นของคุณ
      </p>
    </div>
    <div class="rounded-2xl border bg-white p-6 shadow-sm">
      <h3 class="font-semibold">Stats</h3>
      <p class="mt-2 text-sm text-neutral-600">…</p>
    </div>
    <div class="rounded-2xl border bg-white p-6 shadow-sm">
      <h3 class="font-semibold">Quick Actions</h3>
      <div class="mt-3 flex gap-3">
        <button class="rounded-lg bg-slate-900 px-3 py-2 text-white">Action</button>
        <button class="rounded-lg border px-3 py-2">Secondary</button>
      </div>
    </div>
  </div>
</template>
