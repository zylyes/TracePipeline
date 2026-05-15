import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/pywebview'

export const useConfigStore = defineStore('config', () => {
  const config = ref<Record<string, any>>({})
  const loading = ref(false)

  async function loadConfig() {
    loading.value = true
    try {
      const cfg = await api.get_config()
      config.value = { ...cfg }
      return cfg
    } finally {
      loading.value = false
    }
  }

  async function saveConfig(payload: Record<string, any>) {
    loading.value = true
    try {
      const saved = await api.set_config(payload)
      config.value = { ...saved }
      return saved
    } finally {
      loading.value = false
    }
  }

  async function resetConfig() {
    loading.value = true
    try {
      const cfg = await api.reset_config()
      config.value = { ...cfg }
      return cfg
    } finally {
      loading.value = false
    }
  }

  async function resetProcessingConfig() {
    loading.value = true
    try {
      const cfg = await api.reset_processing_config()
      config.value = { ...cfg }
      return cfg
    } finally {
      loading.value = false
    }
  }

  async function resetStyleConfig() {
    loading.value = true
    try {
      const cfg = await api.reset_style_config()
      config.value = { ...cfg }
      return cfg
    } finally {
      loading.value = false
    }
  }

  return { config, loading, loadConfig, saveConfig, resetConfig, resetProcessingConfig, resetStyleConfig }
})
