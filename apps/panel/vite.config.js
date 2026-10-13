import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const prefix = (env.VITE_BASE_URL || '/').replace(/\/$/, '')
  if (prefix && !/^(\/[a-zA-Z0-9_-]+)+$/.test(prefix)) throw new Error('VITE_BASE_URL must be a URL path')
  const base = prefix + '/'
  return {
  base,
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      [prefix + '/api']: { target: 'http://127.0.0.1:8000', changeOrigin: false, rewrite: path => path.slice(prefix.length) },
      [prefix + '/healthz']: { target: 'http://127.0.0.1:8000', changeOrigin: false, rewrite: path => path.slice(prefix.length) },
    },
  },
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: false },
  }
})
