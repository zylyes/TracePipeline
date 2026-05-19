/**
 * TracePipeline — ECharts 统一主题配置
 * 地质学术配色 + 全局字体从 CSS 变量运行时读取并展开为 Canvas 可用的字体名
 * 所有图表组件统一引用此模块
 */

/**
 * 将 CSS 变量引用链展开为 ECharts Canvas 可用的字体名列表字符串。
 * 例如 "var(--tp-font-latin), var(--tp-font-body-zh)"
 *   → '"Times New Roman","Liberation Serif",...,"SimSun","STSong",...'
 */
function resolveFontStack(cssVarName: string): string {
  try {
    const el = document.documentElement
    const style = getComputedStyle(el)
    const raw = style.getPropertyValue(cssVarName).trim()
    if (!raw) return ''
    return expandCssFontValue(raw, style)
  } catch {
    return ''
  }
}

function expandCssFontValue(value: string, style: CSSStyleDeclaration): string {
  const parts = value.split(',').map(p => p.trim())
  const resolved: string[] = []

  for (const part of parts) {
    const varMatch = part.match(/^var\((--[\w-]+)\)$/)
    if (varMatch) {
      const inner = style.getPropertyValue(varMatch[1]).trim()
      if (inner) {
        const innerResolved = expandCssFontValue(inner, style)
        if (innerResolved) resolved.push(innerResolved)
      }
    } else {
      const cleaned = part.replace(/["']/g, '').trim()
      if (cleaned) resolved.push(`"${cleaned}"`)
    }
  }

  return resolved.join(', ')
}

export function getEchartsFontFamily(): string {
  const resolved = resolveFontStack('--tp-font-data')
  if (resolved) return resolved
  return '"Times New Roman","SimSun","STSong",serif'
}

export function getEchartsHeadingFont(): string {
  const resolved = resolveFontStack('--tp-font-heading')
  if (resolved) return resolved
  return '"Times New Roman","SimHei","Microsoft YaHei",sans-serif'
}

/**
 * 图表配色 — 与 tokens.css 中 --tp-chart-c1~c8 保持同步
 */
const CHART_COLORS = [
  '#C96B4F', // = --tp-chart-c1
  '#4A7C9B', // = --tp-chart-c2
  '#4A9E7A', // = --tp-chart-c3
  '#6B8EBB', // = --tp-chart-c4
  '#B89A6A', // = --tp-chart-c5
  '#8AAFC4', // = --tp-chart-c6
  '#D4A07A', // = --tp-chart-c7
  '#7EB8A0', // = --tp-chart-c8
] as const

export function getChartColors(): string[] {
  return [...CHART_COLORS]
}

export const CHART_COLOR_PRIMARY = CHART_COLORS[0]
export const CHART_COLOR_SECONDARY = CHART_COLORS[1]
export const CHART_COLOR_TERTIARY = CHART_COLORS[2]

export function baseTextStyle() {
  const font = getEchartsFontFamily()
  return { fontFamily: font, fontSize: 12, color: '#5a5a6e' /* = --tp-text-secondary */ }
}

export function baseTitleStyle() {
  const font = getEchartsHeadingFont()
  return { fontFamily: font, fontSize: 16, fontWeight: 600 as const, color: '#1a1a2e' /* = --tp-text-primary */ }
}

export function baseAxisLabelStyle() {
  const font = getEchartsFontFamily()
  return { fontFamily: font, fontSize: 11, color: '#5a5a6e' /* = --tp-text-secondary */ }
}

export function baseTooltipStyle() {
  const font = getEchartsFontFamily()
  return {
    backgroundColor: 'rgba(255,255,255,0.96)',
    borderColor: '#e8eaed' /* = --tp-border */,
    borderWidth: 1,
    textStyle: { fontFamily: font, fontSize: 12, color: '#1a1a2e' /* = --tp-text-primary */ },
    extraCssText: 'border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,0.08);',
  }
}

export function baseAnimationConfig() {
  return {
    animationDuration: 600,
    animationEasing: 'cubicOut' as const,
    animationDurationUpdate: 300,
    animationEasingUpdate: 'cubicInOut' as const,
  }
}

export function baseSeriesAnimation() {
  return {
    animationDelay: (idx: number) => idx * 50,
  }
}
