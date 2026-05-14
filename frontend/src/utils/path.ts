// 将 Windows 绝对路径转换为 pywebview 可用的 file URL
export function toFileUrl(path: string): string {
  if (!path) return ''
  // Windows 路径反斜杠替换为正斜杠，并确保三个斜杠
  const normalized = path.replace(/\\/g, '/')
  if (normalized.startsWith('file:///')) return normalized
  if (normalized.startsWith('file://')) return normalized.replace('file://', 'file:///')
  return 'file:///' + normalized
}
