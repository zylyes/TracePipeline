import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const SCAN_TTL = 30_000      // 文件扫描缓存 30s
const STATS_TTL = 300_000    // 统计数据缓存 5min
const COMPARISON_TTL = 300_000 // 对比数据缓存 5min
const RESULTS_TTL = 60_000   // 结果列表缓存 1min
const IMAGE_TTL = 600_000    // 图片缓存 10min

interface CachedItem<T> {
  data: T
  timestamp: number
}

export const useCacheStore = defineStore('cache', () => {
  // 扫描结果缓存
  const scanResult = ref<CachedItem<any[]> | null>(null)
  // 统计数据缓存: outcrop -> data
  const statsCache = ref<Map<string, CachedItem<any>>>(new Map())
  // 对比数据缓存
  const comparisonCache = ref<CachedItem<any[]> | null>(null)
  // 结果列表缓存
  const resultsCache = ref<CachedItem<any[]> | null>(null)
  // 图片缓存: path -> base64
  const imageCache = ref<Map<string, CachedItem<string>>>(new Map())

  const isScanValid = computed(() => {
    if (!scanResult.value) return false
    return Date.now() - scanResult.value.timestamp < SCAN_TTL
  })

  const isComparisonValid = computed(() => {
    if (!comparisonCache.value) return false
    return Date.now() - comparisonCache.value.timestamp < COMPARISON_TTL
  })

  const isResultsValid = computed(() => {
    if (!resultsCache.value) return false
    return Date.now() - resultsCache.value.timestamp < RESULTS_TTL
  })

  // --- 扫描结果 ---
  function setScan(data: any[]) {
    scanResult.value = { data, timestamp: Date.now() }
  }

  function getScan(): any[] | null {
    return isScanValid.value ? scanResult.value!.data : null
  }

  // --- 统计数据 ---
  function getStats(outcrop: string): any | null {
    const item = statsCache.value.get(outcrop)
    if (!item) return null
    if (Date.now() - item.timestamp > STATS_TTL) {
      statsCache.value.delete(outcrop)
      return null
    }
    return item.data
  }

  function setStats(outcrop: string, data: any) {
    statsCache.value.set(outcrop, { data, timestamp: Date.now() })
  }

  // --- 对比数据 ---
  function getComparison(): any[] | null {
    return isComparisonValid.value ? comparisonCache.value!.data : null
  }

  function setComparison(data: any[]) {
    comparisonCache.value = { data, timestamp: Date.now() }
  }

  // --- 结果列表 ---
  function getResults(): any[] | null {
    return isResultsValid.value ? resultsCache.value!.data : null
  }

  function setResults(data: any[]) {
    resultsCache.value = { data, timestamp: Date.now() }
  }

  // --- 图片 ---
  function getImage(path: string): string | null {
    const item = imageCache.value.get(path)
    if (!item) return null
    if (Date.now() - item.timestamp > IMAGE_TTL) {
      imageCache.value.delete(path)
      return null
    }
    return item.data
  }

  function setImage(path: string, data: string) {
    imageCache.value.set(path, { data, timestamp: Date.now() })
  }

  // --- 失效 ---
  function invalidateScan() {
    scanResult.value = null
  }

  function invalidateStats(outcrop?: string) {
    if (outcrop) {
      statsCache.value.delete(outcrop)
    } else {
      statsCache.value.clear()
    }
  }

  function invalidateComparison() {
    comparisonCache.value = null
  }

  function invalidateResults() {
    resultsCache.value = null
  }

  function invalidateAll() {
    scanResult.value = null
    statsCache.value.clear()
    comparisonCache.value = null
    resultsCache.value = null
    // 图片缓存保留，因为图片文件不常变且体积大
  }

  // --- 处理完成后全量失效 ---
  function onPipelineComplete() {
    invalidateAll()
  }

  return {
    scanResult, statsCache, comparisonCache, resultsCache, imageCache,
    isScanValid, isComparisonValid, isResultsValid,
    getScan, setScan,
    getStats, setStats,
    getComparison, setComparison,
    getResults, setResults,
    getImage, setImage,
    invalidateScan, invalidateStats, invalidateComparison, invalidateResults, invalidateAll,
    onPipelineComplete,
  }
})
