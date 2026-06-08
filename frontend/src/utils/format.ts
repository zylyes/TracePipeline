/** 格式化工具 */

export type AreaSourceKey = 'measured' | 'window' | 'window_equivalent' | 'hull' | 'hull_buffered' | 'unavailable'

const AREA_SOURCE_MAP: Record<string, string> = {
  measured: '实测面积',
  window: '圆形取样窗',
  window_equivalent: '等效圆窗',
  hull: '凸包',
  hull_buffered: '缓冲凸包',
  unavailable: '不可用',
}

export function formatAreaSource(source: string | undefined | null): string {
  if (!source) return '未知来源'
  const mapped = AREA_SOURCE_MAP[source]
  if (mapped) return mapped
  return `未知来源(${source})`
}
