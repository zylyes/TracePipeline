<template>
  <div class="stat-cards">
    <div
      class="stat-card tp-card-glow"
      v-for="(card, idx) in cards"
      :key="card.label"
      :style="{ '--card-accent': card.color, '--stagger-index': idx, animationDelay: `${idx * 70}ms` }"
    >
      <div class="stat-top">
        <div class="stat-value tp-data">{{ formatValue(displayValues[idx]) }}</div>
        <div class="stat-unit">{{ card.unit }}</div>
      </div>
      <div class="stat-label">{{ card.label }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  stats: {
    p10?: number | null
    p20?: number | null
    p21?: number | null
    outcrop_area?: number | null
    nodes_summary?: {
      node_count: number
      node_i_count: number
      node_y_count: number
      node_x_count: number
      intersection_count: number
      degenerate_skipped: number
    }
  }
  showNodes?: boolean
}>()

const ns = computed(() => props.stats?.nodes_summary)

const nodeDensity = computed(() => {
  const count = ns.value?.node_count
  const area = props.stats?.outcrop_area
  if (count == null || area == null || area <= 0) return null
  return count / area
})

// 使用 4 种强调色的不透明版本
const accentColors = [
  'var(--tp-brand-accent-light, #38BDF8)', // 蓝
  'var(--tp-success, #10B981)',            // 绿
  'var(--tp-warning, #F59E0B)',            // 黄
  'var(--tp-danger, #EF4444)'              // 红
]

const cards = computed(() => {
  const base = [
    { label: '线密度 P10', value: props.stats?.p10, unit: 'm⁻¹', color: accentColors[0] },
    { label: '面密度 P20', value: props.stats?.p20, unit: 'm⁻²', color: accentColors[1] },
    { label: '长度密度 P21', value: props.stats?.p21, unit: 'm⁻¹', color: accentColors[2] },
  ]
  if (props.showNodes !== false && ns.value) {
    base.push(
      { label: '节点总数', value: ns.value?.node_count, unit: '个', color: accentColors[3] },
      { label: '节点密度', value: nodeDensity.value, unit: '个/m²', color: accentColors[0] },
      { label: '退化跳过', value: ns.value?.degenerate_skipped, unit: '条', color: accentColors[1] },
      { label: '交叉节点 X', value: ns.value?.node_x_count, unit: '个', color: accentColors[2] },
      { label: '三叉节点 Y', value: ns.value?.node_y_count, unit: '个', color: accentColors[3] },
      { label: '孤立端点 I', value: ns.value?.node_i_count, unit: '个', color: accentColors[0] },
    )
  }
  return base
})

const displayValues = ref<number[]>([])
const animFrames = ref<number[]>([])

// 缓动函数
function easeOutCubic(x: number): number {
  return 1 - Math.pow(1 - x, 3)
}

function animateValue(index: number, start: number, end: number, duration: number) {
  if (animFrames.value[index]) {
    cancelAnimationFrame(animFrames.value[index])
  }
  
  const startTime = performance.now()
  
  function update(currentTime: number) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const easedProgress = easeOutCubic(progress)
    
    displayValues.value[index] = start + (end - start) * easedProgress
    
    if (progress < 1) {
      animFrames.value[index] = requestAnimationFrame(update)
    } else {
      displayValues.value[index] = end
    }
  }
  
  animFrames.value[index] = requestAnimationFrame(update)
}

watch(() => cards.value, (newCards, oldCards) => {
  newCards.forEach((card, idx) => {
    const target = Number(card.value) || 0
    const start = displayValues.value[idx] ?? 0
    
    if (displayValues.value[idx] === undefined) {
      displayValues.value[idx] = 0
    }
    
    if (target !== start || displayValues.value[idx] !== target) {
      animateValue(idx, start, target, 800)
    }
  })
}, { deep: true, immediate: true })

function formatValue(v: number | null | undefined) {
  if (v === null || v === undefined || isNaN(v)) return '—'
  const n = Number(v)
  if (Number.isInteger(n)) return Math.round(n).toString()
  return n.toFixed(2)
}
</script>

<style scoped lang="scss">
.stat-cards {
  display: flex;
  align-items: stretch;
  gap: var(--tp-space-4);
  margin-bottom: var(--tp-space-4);
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 200px;
  background: var(--tp-surface-2);
  border-radius: var(--tp-radius-lg);
  padding: 20px 18px;
  border: 1px solid var(--tp-border-light);
  border-top: 3px solid var(--card-accent);
  box-shadow: var(--tp-shadow-md);
  transition: all var(--tp-duration-slow) var(--tp-easing-expo);
  position: relative;
  overflow: hidden;
  opacity: 0;
  animation: cardFadeIn 0.5s var(--tp-easing-expo) forwards;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

@keyframes cardFadeIn {
  from { opacity: 0; transform: translateY(14px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px var(--card-accent);
  border-color: rgba(255, 255, 255, 0.12);
}

/* 内发光 */
.stat-card::after {
  content: '';
  position: absolute;
  inset: 0;
  box-shadow: inset 0 0 24px var(--card-accent);
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--tp-duration-slow);
}

.stat-card:hover::after {
  opacity: 0.15;
}

.stat-top {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 6px;
  position: relative;
  z-index: 1;
}

.stat-value {
  font-size: var(--tp-font-size-display);
  font-weight: 700;
  color: #e6edf3;
  line-height: 1.2;
  font-feature-settings: "tnum" 1;
}

.stat-unit {
  font-family: var(--tp-font-body);
  font-size: 14px;
  color: var(--tp-text-tertiary);
  font-weight: 500;
}

.stat-label {
  font-family: var(--tp-font-heading);
  font-size: 13px;
  color: var(--tp-text-muted);
  font-weight: 500;
  position: relative;
  z-index: 1;
}
</style>
