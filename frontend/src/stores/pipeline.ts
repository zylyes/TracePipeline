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

  return { running, progress, results, pollTimer, isRunning, reset }
})
