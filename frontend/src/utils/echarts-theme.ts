/**
 * TracePipeline — ECharts 统一主题配置
 * 地质学术配色 + 全局字体从 CSS 变量运行时读取
 * 所有图表组件统一引用此模块
 */

export function getEchartsFontFamily(): string {
  try {
    const val = getComputedStyle(document.documentElement)
      .getPropertyValue('--tp-font-data')
      .trim()
    if (val) return val
  } catch {}
  return '"Times New Roman", "SimSun", serif'
}

export function getEchartsHeadingFont(): string {
  try {
    const val = getComputedStyle(document.documentElement)
      .getPropertyValue('--tp-font-heading')
      .trim()
    if (val) return val
  } catch {}
  return '"SimHei", "Microsoft YaHei", "Times New Roman", sans-serif'
}

const CHART_COLORS = [
  '#C96B4F',
  '#4A7C9B',
  '#4A9E7A',
  '#6B8EBB',
  '#B89A6A',
  '#8AAFC4',
  '#D4A07A',
  '#7EB8A0',
] as const

export function getChartColors(): string[] {
  return [...CHART_COLORS]
}

export const CHART_COLOR_PRIMARY = CHART_COLORS[0]
export const CHART_COLOR_SECONDARY = CHART_COLORS[1]
export const CHART_COLOR_TERTIARY = CHART_COLORS[2]

export function baseTextStyle() {
  const font = getEchartsFontFamily()
  return { fontFamily: font, fontSize: 12, color: '#5a5a6e' }
}

export function baseTitleStyle() {
  const font = getEchartsHeadingFont()
  return { fontFamily: font, fontSize: 16, fontWeight: 600 as const, color: '#1a1a2e' }
}

export function baseAxisLabelStyle() {
  const font = getEchartsFontFamily()
  return { fontFamily: font, fontSize: 11, color: '#5a5a6e' }
}

export function baseTooltipStyle() {
  const font = getEchartsFontFamily()
  return {
    backgroundColor: 'rgba(255,255,255,0.96)',
    borderColor: '#e8eaed',
    borderWidth: 1,
    textStyle: { fontFamily: font, fontSize: 12, color: '#1a1a2e' },
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
