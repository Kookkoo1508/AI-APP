<script setup lang="ts">
import { ref } from 'vue'
import LeftNav from '@/components/LeftNav.vue'

const open = ref(false)
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex">
    <!-- Sidebar (Desktop) -->
    <LeftNav class="hidden lg:block" />

    <!-- Mobile Drawer -->
    <div class="lg:hidden">
      <transition name="fade">
        <div v-if="open" class="fixed inset-0 z-40 bg-black/40" @click="open=false"></div>
      </transition>
      <transition name="slide">
        <aside v-if="open" class="fixed z-50 inset-y-0 left-0 w-72" @click.self="open=false">
          <LeftNav />
        </aside>
      </transition>
    </div>

    <!-- Main -->
    <div class="flex-1 flex flex-col">
      <header class="sticky top-0 z-10 bg-white/80 backdrop-blur border-b">
        <div class="mx-auto max-w-7xl px-4 h-14 flex items-center gap-3">
          <button class="lg:hidden rounded-md border px-2 py-1.5" @click="open=true">☰</button>
          <h1 class="font-semibold">AI App</h1>
        </div>
      </header>

      <main class="mx-auto max-w-7xl w-full p-4 lg:p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,.fade-leave-active{transition:opacity .15s}
.fade-enter-from,.fade-leave-to{opacity:0}
.slide-enter-active,.slide-leave-active{transition:transform .2s}
.slide-enter-from,.slide-leave-to{transform:translateX(-100%)}
</style>
