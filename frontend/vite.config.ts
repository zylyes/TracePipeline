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

const ELEMENT_PLUS_FORM_COMPONENTS = new Set([
  'button',
  'button-group',
  'checkbox',
  'checkbox-group',
  'form',
  'form-item',
  'input',
  'input-number',
  'option',
  'radio',
  'radio-group',
  'select',
  'switch',
])

const ELEMENT_PLUS_DATA_COMPONENTS = new Set([
  'pagination',
  'table',
  'table-column',
])

const ELEMENT_PLUS_FEEDBACK_COMPONENTS = new Set([
  'collapse',
  'collapse-item',
  'dialog',
  'empty',
  'loading',
  'message',
  'message-box',
  'progress',
  'slider',
  'tab-pane',
  'tabs',
  'tooltip',
])

function getElementPlusComponentChunk(normalizedId: string): string | undefined {
  const componentMatch = normalizedId.match(/\/node_modules\/element-plus\/es\/components\/([^/]+)/)
  const componentName = componentMatch?.[1]
  if (!componentName) return undefined

  if (ELEMENT_PLUS_FORM_COMPONENTS.has(componentName)) return 'element-plus-form'
  if (ELEMENT_PLUS_DATA_COMPONENTS.has(componentName)) return 'element-plus-data'
  if (ELEMENT_PLUS_FEEDBACK_COMPONENTS.has(componentName)) return 'element-plus-feedback'
  return 'element-plus-components'
}

function getManualChunk(id: string): string | undefined {
  const normalizedId = id.replace(/\\/g, '/')
  if (!normalizedId.includes('/node_modules/')) return undefined

  if (normalizedId.includes('/node_modules/zrender/')) return 'zrender'
  if (normalizedId.includes('/node_modules/vue-echarts/')) return 'vue-echarts'
  if (normalizedId.includes('/node_modules/echarts/')) return 'echarts'

  if (normalizedId.includes('/node_modules/@vueuse/')) return 'vueuse'
  if (normalizedId.includes('/node_modules/@element-plus/icons-vue/')) return 'element-plus-icons'
  if (normalizedId.includes('/node_modules/@popperjs/') || normalizedId.includes('/node_modules/@ctrl/tinycolor/')) {
    return 'element-plus-vendor'
  }
  if (normalizedId.includes('/node_modules/element-plus/es/components/')) {
    return getElementPlusComponentChunk(normalizedId)
  }
  if (normalizedId.includes('/node_modules/element-plus/')) return 'element-plus-core'

  if (normalizedId.includes('/node_modules/vue') || normalizedId.includes('/node_modules/pinia') || normalizedId.includes('/node_modules/vue-router')) {
    return 'vue-vendor'
  }
  return 'vendor'
}

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
      onwarn(warning, defaultHandler) {
        const id = typeof warning.id === 'string' ? warning.id.replace(/\\/g, '/') : ''
        if (warning.code === 'INVALID_ANNOTATION' && id.includes('/node_modules/@vueuse/core/')) return
        defaultHandler(warning)
      },
      output: {
        manualChunks(id) {
          return getManualChunk(id)
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
