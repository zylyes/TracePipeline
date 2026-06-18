import { defineStore } from 'pinia'
import { ref, computed, type Ref } from 'vue'

const SCAN_TTL = 30_000      // 文件扫描缓存 30s
const STATS_TTL = 300_000    // 统计数据缓存 5min
const STATS_MAX_COUNT = 100  // 统计数据最大条目数
const COMPARISON_TTL = 300_000 // 对比数据缓存 5min
const RESULTS_TTL = 5_000    // 结果列表缓存 5s（output 目录可被外部删除，需快速感知变更）
const IMAGE_TTL = 600_000    // 图片缓存 10min
const IMAGE_MAX_COUNT = 50   // 图片缓存最大条目数
const IMAGE_MAX_CHARS = 80_000_000
const THUMBNAIL_MAX_COUNT = 120
const THUMBNAIL_MAX_CHARS = 30_000_000

interface CachedItem<T> {
  data: T
  timestamp: number
}

const SCAN_STORE_KEY = 'tp_cache_scan'
const COMPARISON_STORE_KEY = 'tp_cache_comparison'
const RESULTS_STORE_KEY = 'tp_cache_results'

function loadStoredItem<T>(key: string): CachedItem<T> | null {
  try {
    const raw = sessionStorage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw) as CachedItem<T>
    if (!parsed || typeof parsed.timestamp !== 'number' || parsed.data === undefined) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

function storeItem<T>(key: string, item: CachedItem<T> | null) {
  try {
    if (item) {
      sessionStorage.setItem(key, JSON.stringify(item))
    } else {
      sessionStorage.removeItem(key)
    }
  } catch {
    // sessionStorage 配额不足或禁用时静默降级
  }
}

export const useCacheStore = defineStore('cache', () => {
  // 扫描结果缓存（页面刷新后从 sessionStorage 恢复）
  const scanResult = ref<CachedItem<any[]> | null>(loadStoredItem<any[]>(SCAN_STORE_KEY))
  // 统计数据缓存: outcrop -> data
  const statsCache = ref<Map<string, CachedItem<any>>>(new Map())
  // 对比数据缓存
  const comparisonCache = ref<CachedItem<any[]> | null>(loadStoredItem<any[]>(COMPARISON_STORE_KEY))
  // 结果列表缓存
  const resultsCache = ref<CachedItem<any[]> | null>(loadStoredItem<any[]>(RESULTS_STORE_KEY))
  // 图片缓存: path -> base64
  const imageCache = ref<Map<string, CachedItem<string>>>(new Map())
  const thumbnailCache = ref<Map<string, CachedItem<string>>>(new Map())
  const imageCacheHits = ref(0)
  const imageCacheMisses = ref(0)
  const thumbnailCacheHits = ref(0)
  const thumbnailCacheMisses = ref(0)

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
    storeItem(SCAN_STORE_KEY, scanResult.value)
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
    // LRU: 命中时将条目移动到 Map 末尾（delete + set 模拟 move_to_end）
    statsCache.value.delete(outcrop)
    statsCache.value.set(outcrop, item)
    return item.data
  }

  function setStats(outcrop: string, data: any) {
    if (statsCache.value.size >= STATS_MAX_COUNT && !statsCache.value.has(outcrop)) {
      // Map 的 keys() 按插入顺序迭代，第一个即为最久未使用
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
    storeItem(COMPARISON_STORE_KEY, comparisonCache.value)
  }

  // --- 结果列表 ---
  function getResults(): any[] | null {
    return isResultsValid.value ? resultsCache.value!.data : null
  }

  function setResults(data: any[]) {
    resultsCache.value = { data, timestamp: Date.now() }
    storeItem(RESULTS_STORE_KEY, resultsCache.value)
  }

  // --- 图片 ---
  function imageKey(
    path: string,
    version?: string | number | null,
    variant = 'full',
    maxPx?: number
  ): string {
    const params: string[] = []
    if (variant !== 'full') params.push(`kind=${variant}`)
    if (maxPx) params.push(`max=${maxPx}`)
    if (version) params.push(`v=${version}`)
    return params.length ? `${path}?${params.join('&')}` : path
  }

  function getCachedString(
    cache: Map<string, CachedItem<string>>,
    key: string,
    hits: Ref<number>,
    misses: Ref<number>
  ): string | null {
    const item = cache.get(key)
    if (!item) {
      misses.value += 1
      return null
    }
    if (Date.now() - item.timestamp > IMAGE_TTL) {
      cache.delete(key)
      misses.value += 1
      return null
    }
    item.timestamp = Date.now()
    hits.value += 1
    return item.data
  }

  function getImage(path: string, version?: string | number | null): string | null {
    return getCachedString(
      imageCache.value,
      imageKey(path, version),
      imageCacheHits,
      imageCacheMisses
    )
  }

  function getThumbnail(
    path: string,
    version?: string | number | null,
    maxPx = 480
  ): string | null {
    return getCachedString(
      thumbnailCache.value,
      imageKey(path, version, 'thumbnail', maxPx),
      thumbnailCacheHits,
      thumbnailCacheMisses
    )
  }

  function getStringCacheChars(cache: Map<string, CachedItem<string>>): number {
    let total = 0
    for (const item of cache.values()) total += item.data.length
    return total
  }

  function pruneStringCache(
    cache: Map<string, CachedItem<string>>,
    maxChars: number,
    protectedKey?: string
  ) {
    while (cache.size > 1 && getStringCacheChars(cache) > maxChars) {
      let oldestKey: string | null = null
      let oldestTime = Infinity
      for (const [k, v] of cache.entries()) {
        if (k === protectedKey) continue
        if (v.timestamp < oldestTime) {
          oldestTime = v.timestamp
          oldestKey = k
        }
      }
      if (oldestKey === null) break
      cache.delete(oldestKey)
    }
  }

  function setCachedString(
    cache: Map<string, CachedItem<string>>,
    key: string,
    data: string,
    maxCount: number,
    maxChars: number
  ) {
    // LRU 淘汰：超过最大条目时删除最旧的记录
    if (cache.size >= maxCount && !cache.has(key)) {
      let oldestKey: string | null = null
      let oldestTime = Infinity
      for (const [k, v] of cache.entries()) {
        if (v.timestamp < oldestTime) {
          oldestTime = v.timestamp
          oldestKey = k
        }
      }
      if (oldestKey !== null) {
        cache.delete(oldestKey)
      }
    }
    cache.set(key, { data, timestamp: Date.now() })
    pruneStringCache(cache, maxChars, key)
  }

  function setImage(path: string, data: string, version?: string | number | null) {
    setCachedString(
      imageCache.value,
      imageKey(path, version),
      data,
      IMAGE_MAX_COUNT,
      IMAGE_MAX_CHARS
    )
  }

  function setThumbnail(
    path: string,
    data: string,
    version?: string | number | null,
    maxPx = 480
  ) {
    setCachedString(
      thumbnailCache.value,
      imageKey(path, version, 'thumbnail', maxPx),
      data,
      THUMBNAIL_MAX_COUNT,
      THUMBNAIL_MAX_CHARS
    )
  }

  function getImageCacheStats() {
    return {
      count: imageCache.value.size,
      chars: getStringCacheChars(imageCache.value),
      maxChars: IMAGE_MAX_CHARS,
      hits: imageCacheHits.value,
      misses: imageCacheMisses.value,
      thumbnailCount: thumbnailCache.value.size,
      thumbnailChars: getStringCacheChars(thumbnailCache.value),
      thumbnailMaxChars: THUMBNAIL_MAX_CHARS,
      thumbnailHits: thumbnailCacheHits.value,
      thumbnailMisses: thumbnailCacheMisses.value,
    }
  }

  function invalidateImages() {
    imageCache.value.clear()
    thumbnailCache.value.clear()
  }

  function invalidateThumbnails() {
    thumbnailCache.value.clear()
  }

  // --- 失效 ---
  function invalidateScan() {
    scanResult.value = null
    storeItem(SCAN_STORE_KEY, null)
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
    storeItem(COMPARISON_STORE_KEY, null)
  }

  function invalidateResults() {
    resultsCache.value = null
    storeItem(RESULTS_STORE_KEY, null)
  }

  function invalidateAll() {
    scanResult.value = null
    statsCache.value.clear()
    comparisonCache.value = null
    resultsCache.value = null
    invalidateImages()
    storeItem(SCAN_STORE_KEY, null)
    storeItem(COMPARISON_STORE_KEY, null)
    storeItem(RESULTS_STORE_KEY, null)
  }

  // --- 处理完成后全量失效 ---
  function onPipelineComplete() {
    invalidateAll()
  }

  return {
    scanResult, statsCache, comparisonCache, resultsCache, imageCache, thumbnailCache,
    imageCacheHits, imageCacheMisses, thumbnailCacheHits, thumbnailCacheMisses,
    isScanValid, isComparisonValid, isResultsValid,
    getScan, setScan,
    getStats, setStats,
    getComparison, setComparison,
    getResults, setResults,
    getImage, setImage, getThumbnail, setThumbnail, getImageCacheStats,
    invalidateScan, invalidateStats, invalidateComparison, invalidateResults,
    invalidateImages, invalidateThumbnails, invalidateAll,
    onPipelineComplete,
  }
})
