import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { PipelineResult } from '@/types'

const STORAGE_KEY_ROSE = 'tp_last_export_rose_plot'
const STORAGE_KEY_NODE = 'tp_last_enable_node_recognition'

function loadBool(key: string, defaultVal: boolean): boolean {
  const raw = localStorage.getItem(key)
  if (raw === null) return defaultVal
  return raw === 'true'
}

export const usePipelineStore = defineStore('pipeline', () => {
  const running = ref(false)
  const progress = ref({
    current: 0,
    total: 0,
    filename: '',
    message: '',
  })
  const results = ref<PipelineResult[]>([])

  // 从 localStorage 恢复持久化状态，默认跟随后端轻量配置
  const lastEnableNodeRecognition = ref(loadBool(STORAGE_KEY_NODE, false))
  const lastExportRosePlot = ref(loadBool(STORAGE_KEY_ROSE, false))

  const isRunning = computed(() => running.value)

  function reset() {
    running.value = false
    progress.value = { current: 0, total: 0, filename: '', message: '' }
    results.value = []
  }

  function setLastRunConfig(enableNode: boolean, exportRose: boolean) {
    lastEnableNodeRecognition.value = enableNode
    lastExportRosePlot.value = exportRose
    localStorage.setItem(STORAGE_KEY_NODE, String(enableNode))
    localStorage.setItem(STORAGE_KEY_ROSE, String(exportRose))
  }

  return {
    running, progress, results, isRunning, reset,
    lastEnableNodeRecognition, lastExportRosePlot, setLastRunConfig,
  }
})
