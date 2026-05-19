import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const SCAN_TTL = 30_000      // 文件扫描缓存 30s
const STATS_TTL = 300_000    // 统计数据缓存 5min
const STATS_MAX_COUNT = 100  // 统计数据最大条目数
const COMPARISON_TTL = 300_000 // 对比数据缓存 5min
const RESULTS_TTL = 5_000    // 结果列表缓存 5s（output 目录可被外部删除，需快速感知变更）
  const IMAGE_TTL = 600_000    // 图片缓存 10min
  const IMAGE_MAX_COUNT = 50   // 图片缓存最大条目数

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
    if (statsCache.value.size >= STATS_MAX_COUNT) {
      const firstKey = statsCache.value.keys().next().value
      if (firstKey !== undefined) statsCache.value.delete(firstKey)
    }
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
    // LRU 淘汰：超过最大条目时删除最旧的记录
    if (imageCache.value.size >= IMAGE_MAX_COUNT && !imageCache.value.has(path)) {
      let oldestKey: string | null = null
      let oldestTime = Infinity
      for (const [k, v] of imageCache.value.entries()) {
        if (v.timestamp < oldestTime) {
          oldestTime = v.timestamp
          oldestKey = k
        }
      }
      if (oldestKey !== null) {
        imageCache.value.delete(oldestKey)
      }
    }
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
    imageCache.value.clear()
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
