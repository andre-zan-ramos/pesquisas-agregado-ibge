import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const port = Number(env.VITE_WEB_PORT || '5187')
  const target = env.VITE_BACKEND_PROXY_TARGET || 'http://127.0.0.1:8817'
  const url = new URL(target)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('VITE_BACKEND_PROXY_TARGET deve ser uma origem HTTP/HTTPS.')
  }
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('VITE_WEB_PORT inválida.')
  return {
    plugins: [react()],
    server: { host: '127.0.0.1', port, strictPort: true, proxy: { '/api/': { target: url.origin } } },
    preview: { host: '127.0.0.1', port: port + 1, strictPort: true },
  }
})
