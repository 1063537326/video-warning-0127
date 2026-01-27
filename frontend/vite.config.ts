import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  optimizeDeps: {
    noDiscovery: true,
    include: []
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:329',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:329',
        ws: true
      },
      '/static': {
        target: 'http://127.0.0.1:329',
        changeOrigin: true
      }
    }
  }
})
