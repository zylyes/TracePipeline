import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const SETTINGS_KEY = 'tp_settings'

function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return {}
}

function saveSettings(data: any) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(data))
  } catch { /* ignore */ }
}

const initial = loadSettings()

export const useAppStore = defineStore('app', () => {
  const inputDir = ref('input')
  const outputDir = ref('output')
  const currentPage = ref(initial.currentPage || 'processing')
  const isDevMode = ref(false)
  const lastOperationTime = ref(initial.lastOperationTime || '')
  const selectedFileCount = ref(0)
  const pipelineStatus = ref<'idle' | 'running' | 'completed' | 'error'>('idle')

  function setDirs(input: string, output: string) {
    inputDir.value = input
    outputDir.value = output
  }

  function updateLastOperation(action?: string) {
    const now = new Date()
    const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    lastOperationTime.value = action ? `${action} (${timeStr})` : timeStr
  }

  watch([currentPage], () => {
    saveSettings({
      inputDir: inputDir.value,
      outputDir: outputDir.value,
      currentPage: currentPage.value,
      lastOperationTime: lastOperationTime.value,
    })
  }, { deep: true })

  return {
    inputDir, outputDir, currentPage, isDevMode,
    lastOperationTime, selectedFileCount, pipelineStatus,
    setDirs, updateLastOperation,
  }
})
