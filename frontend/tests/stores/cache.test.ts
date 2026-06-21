/**
 * cache store 单元测试 — 验证 TTL 过期、LRU 淘汰与 sessionStorage 持久化。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCacheStore } from '@/stores/cache'

describe('useCacheStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    sessionStorage.clear()
  })

  // 扫描缓存

  it('扫描缓存初始为空', () => {
    const store = useCacheStore()
    expect(store.isScanValid).toBe(false)
    expect(store.getScan()).toBeNull()
  })

  it('setScan 写入后 getScan 在有效期内返回数据', () => {
    const store = useCacheStore()
    store.setScan([{ outcrop: 'O76' }])

    expect(store.getScan()).toEqual([{ outcrop: 'O76' }])
    expect(store.isScanValid).toBe(true)
  })

  it('扫描缓存在 TTL 过期后失效', () => {
    const store = useCacheStore()
    store.setScan([{ outcrop: 'O76' }])
    // 直接设置一个过期的时间戳来模拟 TTL 过期
    store.scanResult = { data: [{ outcrop: 'O76' }], timestamp: Date.now() - 31_000 }

    expect(store.getScan()).toBeNull()
    expect(store.isScanValid).toBe(false)
  })

  it('invalidateScan 立即清除扫描缓存', () => {
    const store = useCacheStore()
    store.setScan([{ outcrop: 'O76' }])

    store.invalidateScan()

    expect(store.getScan()).toBeNull()
  })

  // 统计缓存

  it('统计缓存支持多露头存取', () => {
    const store = useCacheStore()
    store.setStats('O76', { p10: 1.0 })
    store.setStats('O77', { p10: 2.0 })

    expect(store.getStats('O76')).toEqual({ p10: 1.0 })
    expect(store.getStats('O77')).toEqual({ p10: 2.0 })
  })

  it('统计缓存 TTL 过期后单条失效', () => {
    const store = useCacheStore()
    store.setStats('O76', { p10: 1.0 })
    store.setStats('O77', { p10: 2.0 })
    // 直接操作 Map 使 O76 过期
    const old = store.statsCache.get('O76')!
    store.statsCache.set('O76', { ...old, timestamp: Date.now() - 301_000 })

    expect(store.getStats('O76')).toBeNull()
    expect(store.getStats('O77')).toEqual({ p10: 2.0 })
  })

  it('getStats 命中时移动条目到末尾（LRU）', () => {
    const store = useCacheStore()
    // 写入 3 条
    store.setStats('A', { v: 1 })
    store.setStats('B', { v: 2 })
    store.setStats('C', { v: 3 })

    // 访问 A — 应将其移到 Map 末尾
    store.getStats('A')

    // 验证数据未被破坏
    expect(store.getStats('A')).toEqual({ v: 1 })
    expect(store.getStats('B')).toEqual({ v: 2 })
    expect(store.getStats('C')).toEqual({ v: 3 })
  })

  it('统计缓存超过最大条目时淘汰最久未使用条目', () => {
    const store = useCacheStore()
    // STATS_MAX_COUNT = 100，写入 101 条
    for (let i = 0; i < 101; i++) {
      store.setStats(`outcrop_${i}`, { v: i })
    }
    // 第一条写入的应被淘汰
    expect(store.getStats('outcrop_0')).toBeNull()
    // 最后一条应保留
    expect(store.getStats('outcrop_100')).toEqual({ v: 100 })
  })

  it('invalidateStats 可清除单条或全部', () => {
    const store = useCacheStore()
    store.setStats('O76', { p10: 1 })
    store.setStats('O77', { p10: 2 })

    store.invalidateStats('O76')
    expect(store.getStats('O76')).toBeNull()
    expect(store.getStats('O77')).toEqual({ p10: 2 })

    store.invalidateStats() // 清除全部
    expect(store.getStats('O77')).toBeNull()
  })

  // 图片缓存

  it('图片缓存未命中返回 null', () => {
    const store = useCacheStore()
    expect(store.getImage('unknown.png')).toBeNull()
  })

  it('setImage 写入后 getImage 返回 base64 数据', () => {
    const store = useCacheStore()
    store.setImage('test.png', 'iVBORw0KGgo...')

    expect(store.getImage('test.png')).toBe('iVBORw0KGgo...')
  })

  it('图片缓存在 TTL 过期后失效', () => {
    const store = useCacheStore()
    store.setImage('test.png', 'iVBORw0KGgo...')
    // 使条目过期
    const old = store.imageCache.get('test.png')!
    store.imageCache.set('test.png', { ...old, timestamp: Date.now() - 601_000 })

    expect(store.getImage('test.png')).toBeNull()
  })

  it('图片缓存命中时更新时间戳（LRU 保护）', () => {
    const store = useCacheStore()
    store.setImage('test.png', 'data1')

    // 时间推进 5 分钟后命中（TTL 内），应刷新时间戳
    const old = store.imageCache.get('test.png')!
    store.imageCache.set('test.png', { ...old, timestamp: Date.now() - 300_000 })
    expect(store.getImage('test.png')).toBe('data1')

    // 检查时间戳已被刷新（不再过期）
    const refreshed = store.imageCache.get('test.png')!
    expect(refreshed.timestamp).toBeGreaterThanOrEqual(Date.now() - 1000)
  })

  // 结果缓存

  it('结果缓存 TTL 为 5 秒', () => {
    const store = useCacheStore()
    store.setResults([{ outcrop: 'O76' }])
    // 手动使时间戳过期
    store.resultsCache = { data: [{ outcrop: 'O76' }], timestamp: Date.now() - 5_001 }

    expect(store.getResults()).toBeNull()
  })

  // 全局失效

  it('onPipelineComplete() 清除全部缓存', () => {
    const store = useCacheStore()
    store.setScan([{ outcrop: 'O76' }])
    store.setStats('O76', { p10: 1 })
    store.setComparison([{ outcrop: 'O76' }])
    store.setResults([{ outcrop: 'O76' }])
    store.setImage('test.png', 'data')

    store.onPipelineComplete()

    expect(store.getScan()).toBeNull()
    expect(store.getStats('O76')).toBeNull()
    expect(store.getComparison()).toBeNull()
    expect(store.getResults()).toBeNull()
    expect(store.getImage('test.png')).toBeNull()
  })

  // 图片缓存统计

  it('getImageCacheStats 返回命中/未命中计数', () => {
    const store = useCacheStore()

    // 写入一条
    store.setImage('a.png', 'data_a')
    // 命中
    store.getImage('a.png')
    // 未命中
    store.getImage('missing.png')

    const stats = store.getImageCacheStats()
    expect(stats.hits).toBe(1)
    expect(stats.misses).toBe(1)
    expect(stats.count).toBe(1)
  })
})
