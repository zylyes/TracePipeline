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
  const inputDir = ref(initial.inputDir || './input')
  const outputDir = ref(initial.outputDir || './output')
  const currentPage = ref(initial.currentPage || 'processing')
  const isDevMode = ref(initial.isDevMode || false)

  watch([isDevMode, currentPage], () => {
    saveSettings({
      inputDir: inputDir.value,
      outputDir: outputDir.value,
      currentPage: currentPage.value,
      isDevMode: isDevMode.value,
    })
  }, { deep: true })

  return { inputDir, outputDir, currentPage, isDevMode }
})
