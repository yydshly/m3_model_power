import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, 'frontend/', '')
  const apiBase = env.VITE_API_BASE_URL || 'http://localhost:8000'
  const wsBase = apiBase.replace('http://', 'ws://').replace('https://', 'wss://')

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api/ws': { target: wsBase, ws: true },
        '/api': apiBase,
      },
    },
  }
})
