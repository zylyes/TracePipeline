/**
 * TracePipeline — ECharts 统一主题配置 v2
 * 地质科学主题配色 + 全局字体从 CSS 变量运行时读取并展开为 Canvas 可用的字体名
 * 所有图表组件统一引用此模块
 * 配色与 tokens.css 中 --tp-chart-c1~c10 保持同步
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
 * 图表配色 — 与 tokens.css 中 --tp-chart-c1~c10 保持同步
 * 地质科学主题：色相均匀分布，相邻色相间隔 ≥ 40°
 * 融入地质色语义：蓝=深度/水体 青碧=矿物 赭石=砂岩 紫=构造应力 红=断层
 */
const CHART_COLORS = [
  '#0369A1', // 深蓝——深度/水体
  '#0D9488', // 青碧——矿物/岩体
  '#C2703A', // 赭石——砂岩/沉积
  '#7C3AED', // 蓝紫——构造应力
  '#DC2626', // 鲜红——断层/危险
  '#0EA5E9', // 天蓝——浅层/天空
  '#65A30D', // 草绿——植被/地表
  '#DB2777', // 品红——特殊标注
  '#EA580C', // 橙——次级沉积
  '#6D28D9', // 暗紫——深层构造
] as const

export function getChartColors(): string[] {
  return [...CHART_COLORS]
}

/**
 * 读取单个 CSS 变量的实际值(供 ECharts Canvas 使用)。
 * ECharts Canvas 渲染器不识别 `var(--x)` 字符串,必须解析为具体色值。
 */
export function cssVar(name: string): string | undefined {
  try {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || undefined
  } catch {
    return undefined
  }
}

export const CHART_COLOR_PRIMARY = '#38bdf8' // 主色（蓝）
export const CHART_COLOR_SECONDARY = '#22c55e' // 成功（绿）
export const CHART_COLOR_TERTIARY = '#f59e0b' // 警告（黄）
export const CHART_COLOR_DANGER = '#f87171' // 危险（红）

export function baseTextStyle() {
  const font = getEchartsFontFamily()
  return { fontFamily: font, fontSize: 12, color: '#8b949e' }
}

export function baseTitleStyle() {
  const font = getEchartsHeadingFont()
  return { fontFamily: font, fontSize: 16, fontWeight: 600 as const, color: '#8b949e' }
}

export function baseAxisLabelStyle() {
  const font = getEchartsFontFamily()
  return { fontFamily: font, fontSize: 11, color: '#8b949e' }
}

export function baseTooltipStyle() {
  const font = getEchartsFontFamily()
  return {
    backgroundColor: 'rgba(255,255,255,0.92)',
    borderColor: 'rgba(56,189,248,0.28)',
    borderWidth: 1,
    textStyle: { fontFamily: font, fontSize: 12, color: '#1A202C' },
    extraCssText: 'border-radius:12px;box-shadow:0 16px 32px rgba(26,54,93,0.12),0 0 24px rgba(56,189,248,0.16);backdrop-filter:blur(10px) saturate(1.12);',
  }
}

export function baseAnimationConfig() {
  return {
    animationDuration: 900,
    animationEasing: 'quarticOut' as const,
    animationDurationUpdate: 520,
    animationEasingUpdate: 'cubicInOut' as const,
  }
}

export function baseSeriesAnimation() {
  return {
    animationDelay: (idx: number) => idx * 45,
  }
}
