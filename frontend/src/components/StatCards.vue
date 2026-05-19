<template>
  <div class="stat-cards">
    <div
      class="stat-card tp-card-glow"
      v-for="(card, idx) in cards"
      :key="card.label"
      :style="{ '--accent-color': card.color, '--stagger-index': idx, animationDelay: `${idx * 70}ms` }"
    >
      <div class="stat-accent"></div>
      <div class="stat-top">
        <div class="stat-value tp-data">{{ formatValue(card.value) }}</div>
        <div class="stat-unit">{{ card.unit }}</div>
      </div>
      <div class="stat-label">{{ card.label }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getChartColors } from '@/utils/echarts-theme'

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

const chartColors = getChartColors()

const cards = computed(() => {
  const cc = chartColors
  const base = [
    { label: '线密度 P10', value: props.stats?.p10, unit: 'm⁻¹', color: cc[0] },
    { label: '面密度 P20', value: props.stats?.p20, unit: 'm⁻²', color: cc[1] },
    { label: '长度密度 P21', value: props.stats?.p21, unit: 'm⁻¹', color: cc[2] },
  ]
  if (props.showNodes !== false && ns.value) {
    base.push(
      { label: '节点总数', value: ns.value?.node_count, unit: '个', color: cc[4] },
      { label: '节点密度', value: nodeDensity.value, unit: '个/m²', color: cc[6] },
      { label: '退化跳过', value: ns.value?.degenerate_skipped, unit: '条', color: cc[5] },
      { label: '交叉节点 X', value: ns.value?.node_x_count, unit: '个', color: cc[3] },
      { label: '三叉节点 Y', value: ns.value?.node_y_count, unit: '个', color: cc[7] },
      { label: '孤立端点 I', value: ns.value?.node_i_count, unit: '个', color: cc[6] },
    )
  }
  return base
})

function formatValue(v: number | null | undefined) {
  if (v === null || v === undefined || (typeof v === 'number' && isNaN(v))) return '—'
  const n = Number(v)
  if (Number.isInteger(n)) return String(n)
  return n.toFixed(2)
}
</script>

<style scoped lang="scss">
.stat-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--tp-space-4);
  margin-bottom: var(--tp-space-4);
}

.stat-card {
  background: var(--tp-bg-card);
  border-radius: var(--tp-radius-lg);
  padding: 20px 18px;
  box-shadow: var(--tp-shadow-md);
  transition: all var(--tp-duration-slow) var(--tp-easing-expo);
  position: relative;
  overflow: hidden;
  opacity: 0;
  animation: cardFadeIn 0.5s var(--tp-easing-expo) forwards;
  border: 1px solid var(--tp-border-light);
}

@keyframes cardFadeIn {
  from { opacity: 0; transform: translateY(14px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.stat-card:hover {
  transform: translateY(-4px) scale(1.01);
  box-shadow: var(--tp-shadow-lg), 0 0 0 1px var(--tp-brand-accent-border);
}

/* 顶部彩色指示条 */
.stat-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, var(--accent-color, var(--tp-brand-accent)), transparent);
  transform: scaleX(0);
  transition: transform 0.4s var(--tp-easing-expo);
  transform-origin: center;
}

.stat-card:hover .stat-accent {
  transform: scaleX(1);
}

/* hover 时底部微光 */
.stat-card::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 20%;
  right: 20%;
  height: 1px;
  background: var(--accent-color, var(--tp-brand-accent));
  opacity: 0;
  filter: blur(4px);
  transition: opacity var(--tp-duration-slow);
}

.stat-card:hover::after {
  opacity: 0.3;
}

.stat-top {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 6px;
}

.stat-value {
  font-size: var(--tp-font-size-display);
  font-weight: 700;
  color: var(--tp-text-primary);
  line-height: 1.2;
  font-feature-settings: "tnum" 1;
}

.stat-unit {
  font-family: var(--tp-font-body);
  font-size: 13px;
  color: var(--tp-text-tertiary);
  font-weight: 500;
}

.stat-label {
  font-family: var(--tp-font-heading);
  font-size: 13px;
  color: var(--tp-text-secondary);
  font-weight: 500;
}
</style>
