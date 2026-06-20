/**
 * 前端多层缓存 Store。
 *
 * ## 缓存层级
 *
 * | 缓存 | TTL | 存储 | 淘汰策略 |
 * |------|-----|------|----------|
 * | scan | 30s | sessionStorage | TTL |
 * | stats | 5min | Memory (Map) | LRU (max 100) |
 * | comparison | 5min | sessionStorage | TTL |
 * | results | 5s | sessionStorage | TTL |
 * | image | 10min | Memory (Map) | LRU + char budget (max 50/80M) |
 * | thumbnail | 10min | Memory (Map) | LRU + char budget (max 120/30M) |
 *
 * ## LRU 实现
 *
 * 统计缓存使用 Map 的插入顺序模拟 LRU：
 * - `getStats` 命中时执行 delete+set 将条目移到末尾
 * - `setStats` 超限时淘汰 `keys().next()`（最久未使用）
 *
 * 图片缓存通过遍历找最旧 timestamp 实现 O(n) LRU。
 *
 * @module cacheStore
 */
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

/** 文件扫描结果条目 */
interface ScanEntry {
  stem: string
  outcrop: string
  path: string
  status: 'completed' | 'pending'
}

/** 统计数据（从后端返回的原始结构） */
interface StatsResult {
  outcrop: string
  trace_count: number
  p10: number | null
  p20: number | null
  p21: number | null
  [key: string]: unknown
}

/** 对比数据条目 */
interface ComparisonEntry {
  outcrop: string
  trace_count: number | string
  p10: number | string
  p20: number | string
  p21: number | string
  [key: string]: unknown
}

/** 处理结果条目 */
interface ResultEntry {
  outcrop: string
  raw_plot: string
  rotated_plot: string
  rose_plot: string
  [key: string]: unknown
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
  const scanResult = ref<CachedItem<ScanEntry[]> | null>(loadStoredItem<ScanEntry[]>(SCAN_STORE_KEY))
  // 统计数据缓存: outcrop -> data
  const statsCache = ref<Map<string, CachedItem<StatsResult>>>(new Map())
  // 对比数据缓存
  const comparisonCache = ref<CachedItem<ComparisonEntry[]> | null>(loadStoredItem<ComparisonEntry[]>(COMPARISON_STORE_KEY))
  // 结果列表缓存
  const resultsCache = ref<CachedItem<ResultEntry[]> | null>(loadStoredItem<ResultEntry[]>(RESULTS_STORE_KEY))
  // 图片缓存: path -> base64
  const imageCache = ref<Map<string, CachedItem<string>>>(new Map())
  const thumbnailCache = ref<Map<string, CachedItem<string>>>(new Map())
  const imageCacheHits = ref(0)
  const imageCacheMisses = ref(0)
  const thumbnailCacheHits = ref(0)
  const thumbnailCacheMisses = ref(0)
  const imageCacheChars = ref(0)
  const thumbnailCacheChars = ref(0)

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
  function setScan(data: ScanEntry[]) {
    scanResult.value = { data, timestamp: Date.now() }
    storeItem(SCAN_STORE_KEY, scanResult.value)
  }

  function getScan(): ScanEntry[] | null {
    return isScanValid.value ? scanResult.value!.data : null
  }

  // --- 统计数据 ---
  function getStats(outcrop: string): StatsResult | null {
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

  function setStats(outcrop: string, data: StatsResult) {
    if (statsCache.value.size >= STATS_MAX_COUNT && !statsCache.value.has(outcrop)) {
      // Map 的 keys() 按插入顺序迭代，第一个即为最久未使用
      const firstKey = statsCache.value.keys().next().value
      if (firstKey !== undefined) statsCache.value.delete(firstKey)
    }
    statsCache.value.set(outcrop, { data, timestamp: Date.now() })
  }

  // --- 对比数据 ---
  function getComparison(): ComparisonEntry[] | null {
    return isComparisonValid.value ? comparisonCache.value!.data : null
  }

  function setComparison(data: ComparisonEntry[]) {
    comparisonCache.value = { data, timestamp: Date.now() }
    storeItem(COMPARISON_STORE_KEY, comparisonCache.value)
  }

  // --- 结果列表 ---
  function getResults(): ResultEntry[] | null {
    return isResultsValid.value ? resultsCache.value!.data : null
  }

  function setResults(data: ResultEntry[]) {
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

  function getStringCacheChars(_cache: Map<string, CachedItem<string>>, runningTotal: Ref<number>): number {
    return runningTotal.value
  }

  function pruneStringCache(
    cache: Map<string, CachedItem<string>>,
    runningTotal: Ref<number>,
    maxChars: number,
    protectedKey?: string
  ) {
    while (cache.size > 1 && runningTotal.value > maxChars) {
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
      const removed = cache.get(oldestKey)
      if (removed) runningTotal.value -= removed.data.length
      cache.delete(oldestKey)
    }
  }

  function setCachedString(
    cache: Map<string, CachedItem<string>>,
    runningTotal: Ref<number>,
    key: string,
    data: string,
    maxCount: number,
    maxChars: number
  ) {
    // 主动清理同路径（不含 query string）的旧版本条目
    const baseKey = key.split('?')[0]
    for (const [k, v] of cache.entries()) {
      if (k.startsWith(baseKey + '?') || (k === baseKey && k !== key)) {
        runningTotal.value -= v.data.length
        cache.delete(k)
      }
    }

    // 计数淘汰：超过最大条目时删除最旧的记录
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
        const removed = cache.get(oldestKey)
        if (removed) runningTotal.value -= removed.data.length
        cache.delete(oldestKey)
      }
    }
    const oldItem = cache.get(key)
    if (oldItem) runningTotal.value -= oldItem.data.length
    cache.set(key, { data, timestamp: Date.now() })
    runningTotal.value += data.length
    pruneStringCache(cache, runningTotal, maxChars, key)
  }

  function setImage(path: string, data: string, version?: string | number | null) {
    setCachedString(
      imageCache.value,
      imageCacheChars,
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
      thumbnailCacheChars,
      imageKey(path, version, 'thumbnail', maxPx),
      data,
      THUMBNAIL_MAX_COUNT,
      THUMBNAIL_MAX_CHARS
    )
  }

  function getImageCacheStats() {
    return {
      count: imageCache.value.size,
      chars: getStringCacheChars(imageCache.value, imageCacheChars),
      maxChars: IMAGE_MAX_CHARS,
      hits: imageCacheHits.value,
      misses: imageCacheMisses.value,
      thumbnailCount: thumbnailCache.value.size,
      thumbnailChars: getStringCacheChars(thumbnailCache.value, thumbnailCacheChars),
      thumbnailMaxChars: THUMBNAIL_MAX_CHARS,
      thumbnailHits: thumbnailCacheHits.value,
      thumbnailMisses: thumbnailCacheMisses.value,
    }
  }

  function invalidateImages() {
    imageCache.value.clear()
    thumbnailCache.value.clear()
    imageCacheChars.value = 0
    thumbnailCacheChars.value = 0
  }

  function invalidateThumbnails() {
    thumbnailCache.value.clear()
    thumbnailCacheChars.value = 0
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
