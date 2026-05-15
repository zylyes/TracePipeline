import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePipelineStore = defineStore('pipeline', () => {
  const running = ref(false)
  const progress = ref({
    current: 0,
    total: 0,
    filename: '',
    message: '',
  })
  const results = ref<any[]>([])
  const pollTimer = ref<number | null>(null)

  // 最近一次处理时的配置状态（用于控制其他页面的显示）
  const lastEnableNodeRecognition = ref(true)
  const lastExportRosePlot = ref(true)

  const isRunning = computed(() => running.value)

  function reset() {
    running.value = false
    progress.value = { current: 0, total: 0, filename: '', message: '' }
    results.value = []
    if (pollTimer.value) {
      clearInterval(pollTimer.value)
      pollTimer.value = null
    }
  }

  function setLastRunConfig(enableNode: boolean, exportRose: boolean) {
    lastEnableNodeRecognition.value = enableNode
    lastExportRosePlot.value = exportRose
  }

  return {
    running, progress, results, pollTimer, isRunning, reset,
    lastEnableNodeRecognition, lastExportRosePlot, setLastRunConfig,
  }
})
