import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
  build: {
    rollupOptions: {
      output: {
        // Keep ECharts in its own async chunk so index stays app-code-only.
        // Chart consumers (Gallery, future F5+ screens) import via echarts-setup.
        manualChunks(id) {
          if (id.includes('node_modules/echarts')) {
            return 'echarts'
          }
        },
      },
    },
  },
})
