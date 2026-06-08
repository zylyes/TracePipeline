import { api } from '@/api/pywebview'
import { useCacheStore } from '@/stores/cache'

interface ImageMeta {
  mtime_ns?: number
  size?: number
}

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

  const cacheStore = useCacheStore()
  const cleanPath = cleanImagePath(path)
  let version: string | null = null

  try {
    const meta = await api.get_image_meta(cleanPath)
    version = imageVersion(meta)
  } catch {
    version = null
  }

  const cached = cacheStore.getImage(path, version)
  if (cached) return cached

  try {
    const base64 = await api.get_image(cleanPath)
    if (base64) {
      cacheStore.setImage(path, base64, version)
    }
    return base64 || ''
  } catch {
    return ''
  }
}
