// 图片加载工具：通过后端 API 读取图片为 base64 data URL（带前端缓存）
import { api } from '@/api/pywebview'
import { useCacheStore } from '@/stores/cache'

export async function loadImageBase64(path: string): Promise<string> {
  if (!path) return ''
  if (path.startsWith('data:')) return path

  const cacheStore = useCacheStore()
  const cached = cacheStore.getImage(path)
  if (cached) return cached

  // 去掉 file:// 前缀（兼容 2-4 个斜杠的各种变体）
  const cleanPath = path.replace(/^file:\/+(.*)$/, '$1')
  try {
    const base64 = await api.get_image(cleanPath)
    if (base64) {
      cacheStore.setImage(path, base64)
    }
    return base64 || ''
  } catch (e) {
    return ''
  }
}

export function previewImage(images: Array<{ title: string; src: string }>, initialIndex = 0) {
  // 通过事件总线或全局状态触发 ImageViewer
  // 这里返回一个配置对象，由调用方通过组件绑定
  return { images, initialIndex }
}
