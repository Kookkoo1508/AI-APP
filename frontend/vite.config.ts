import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
// import path from 'path'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
    resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8088',
      changeOrigin: true,
    },
  },
},
})
