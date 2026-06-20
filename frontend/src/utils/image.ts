import { api } from '@/api/pywebview'
import { useCacheStore } from '@/stores/cache'

interface ImageMeta {
  mtime_ns?: number
  size?: number
}

/** 正在进行的图片加载请求，用于并发去重 */
const _loadingPromises = new Map<string, Promise<string>>()

function cleanImagePath(path: string): string {
  return path.replace(/^file:\/+(.*)$/, '$1')
}

function imageVersion(meta: ImageMeta | null): string | null {
  if (!meta?.mtime_ns || !meta?.size) return null
  return `${meta.mtime_ns}-${meta.size}`
}

export async function loadImageBase64(path: string): Promise<string> {
  if (!path) return ''
  if (path.startsWith('data:')) return path

  // 并发去重：如果同一图片正在加载，复用现有 Promise
  const dedupKey = `full:${path}`
  const existing = _loadingPromises.get(dedupKey)
  if (existing) return existing

  const promise = _loadImageBase64Impl(path)
  _loadingPromises.set(dedupKey, promise)
  try {
    return await promise
  } finally {
    _loadingPromises.delete(dedupKey)
  }
}

async function _loadImageBase64Impl(path: string): Promise<string> {
  const cacheStore = useCacheStore()
  const cleanPath = cleanImagePath(path)
  let version: string | null = null

  try {
    const meta = (await api.get_image_meta(cleanPath)) as ImageMeta | null
    version = imageVersion(meta)
  } catch (_err: unknown) {
    version = null
  }

  const cached = cacheStore.getImage(path, version)
  if (cached) return cached

  try {
    const result = await api.get_image_data(cleanPath)
    if (result && result.data) {
      const data = result.data as string
      if (result.mtime_ns && result.size) {
        version = `${result.mtime_ns}-${result.size}`
      }
      cacheStore.setImage(path, data, version)
      return data
    }
    return ''
  } catch (_err: unknown) {
    return ''
  }
}

export async function loadImageThumbnail(path: string, maxPx = 480): Promise<string> {
  if (!path) return ''
  if (path.startsWith('data:')) return path

  // 并发去重
  const dedupKey = `thumb:${path}:${maxPx}`
  const existing = _loadingPromises.get(dedupKey)
  if (existing) return existing

  const promise = _loadImageThumbnailImpl(path, maxPx)
  _loadingPromises.set(dedupKey, promise)
  try {
    return await promise
  } finally {
    _loadingPromises.delete(dedupKey)
  }
}

async function _loadImageThumbnailImpl(path: string, maxPx: number): Promise<string> {
  const cacheStore = useCacheStore()
  const cleanPath = cleanImagePath(path)
  let version: string | null = null

  try {
    const meta = (await api.get_image_meta(cleanPath)) as ImageMeta | null
    version = imageVersion(meta)
  } catch (_err: unknown) {
    version = null
  }

  const cached = cacheStore.getThumbnail(path, version, maxPx)
  if (cached) return cached

  try {
    const thumbnail = await api.get_image_thumbnail(cleanPath, maxPx)
    if (thumbnail) {
      cacheStore.setThumbnail(path, thumbnail, version, maxPx)
    }
    return thumbnail || ''
  } catch (_err: unknown) {
    return ''
  }
}
