import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useConfigStore = defineStore('config', () => {
  const config = ref<Record<string, any>>({})
  const loading = ref(false)

  return { config, loading }
})
