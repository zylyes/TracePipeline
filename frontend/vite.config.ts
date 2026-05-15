import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { readFileSync } from 'fs'

function getAppVersion(): string {
  try {
    const initPy = readFileSync(resolve(__dirname, '../trace_pipeline/__init__.py'), 'utf-8')
    const m = initPy.match(/__version__\s*=\s*"([^"]+)"/)
    return m ? m[1] : '0.0.0'
  } catch {
    return '0.0.0'
  }
}

const APP_VERSION = getAppVersion()

export default defineConfig({
  plugins: [
    vue(),
    {
      name: 'inject-version',
      transformIndexHtml(html) {
        return html.replace('{{APP_VERSION}}', APP_VERSION)
      },
    },
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  define: {
    __APP_VERSION__: JSON.stringify(APP_VERSION),
  },
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
  },
  css: {
    preprocessorOptions: {
      scss: {},
    },
  },
})
