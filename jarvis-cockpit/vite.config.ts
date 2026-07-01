import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  // GitHub Pages公開URL（https://<org>.github.io/SAKANA/）用のベースパス。
  // ローカル開発時（vite dev）は無視され、ビルド時（vite build）のみ適用される。
  base: process.env.GITHUB_PAGES ? '/SAKANA/' : '/',
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})
