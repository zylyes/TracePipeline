// 图片加载工具：通过后端 API 读取图片为 base64 data URL
import { api } from '@/api/pywebview'

export async function loadImageBase64(path: string): Promise<string> {
  if (!path) return ''
  if (path.startsWith('data:')) return path
  // 去掉 file:/// 或 file:// 前缀
  const cleanPath = path.replace(/^file:\/\/\//, '').replace(/^file:\/\//, '')
  try {
    const base64 = await api.get_image(cleanPath)
    return base64 || ''
  } catch (e) {
    return ''
  }
}
