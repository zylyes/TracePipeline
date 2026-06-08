import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve, dirname } from 'path'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

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
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replace(/\\/g, '/')
          if (!normalizedId.includes('node_modules')) return undefined
          if (normalizedId.includes('echarts') || normalizedId.includes('zrender') || normalizedId.includes('vue-echarts')) {
            return 'charts'
          }
          if (normalizedId.includes('element-plus') || normalizedId.includes('@element-plus')) {
            return 'element-plus'
          }
          if (normalizedId.includes('/vue') || normalizedId.includes('pinia') || normalizedId.includes('vue-router')) {
            return 'vue-vendor'
          }
          return 'vendor'
        },
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {},
    },
  },
})
