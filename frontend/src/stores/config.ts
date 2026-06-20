import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/pywebview'
import { useCacheStore } from '@/stores/cache'

export const useConfigStore = defineStore('config', () => {
  const config = ref<Record<string, any>>({})
  const loading = ref(false)

  function invalidateCaches() {
    useCacheStore().invalidateAll()
  }

  async function loadConfig() {
    loading.value = true
    try {
      const cfg = (await api.get_config()) as Record<string, any>
      config.value = { ...cfg }
      return cfg
    } finally {
      loading.value = false
    }
  }

  async function saveConfig(payload: Record<string, any>) {
    loading.value = true
    try {
      const saved = (await api.set_config(payload)) as Record<string, any>
      config.value = { ...saved }
      invalidateCaches()
      return saved
    } finally {
      loading.value = false
    }
  }

  async function resetConfig() {
    loading.value = true
    try {
      const cfg = (await api.reset_config()) as Record<string, any>
      config.value = { ...cfg }
      invalidateCaches()
      return cfg
    } finally {
      loading.value = false
    }
  }

  async function resetProcessingConfig() {
    loading.value = true
    try {
      const cfg = (await api.reset_processing_config()) as Record<string, any>
      config.value = { ...cfg }
      invalidateCaches()
      return cfg
    } finally {
      loading.value = false
    }
  }

  async function resetStyleConfig() {
    loading.value = true
    try {
      const cfg = (await api.reset_style_config()) as Record<string, any>
      config.value = { ...cfg }
      invalidateCaches()
      return cfg
    } finally {
      loading.value = false
    }
  }

  /** 从后端 API 加载配置后，仅更新本地状态（不触发持久化）。 */
  function hydrateConfig(cfg: Record<string, any>) {
    config.value = { ...cfg }
  }

  return { config, loading, loadConfig, saveConfig, resetConfig, resetProcessingConfig, resetStyleConfig, hydrateConfig }
})
