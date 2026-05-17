<template>
  <div class="stat-cards">
    <div
      class="stat-card"
      v-for="(card, idx) in cards"
      :key="card.label"
      :style="{ '--accent-color': card.color, animationDelay: `${idx * 80}ms` }"
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

const CARD_COLORS = [
  '#2c3e50', '#B85C38', '#2E7D5A',
  '#4A5568', '#7B1FA2', '#606266',
  '#1565C0', '#E65100', '#2E7D5A',
]

const cards = computed(() => {
  const base = [
    { label: '线密度 P10', value: props.stats?.p10, unit: 'm⁻¹', color: '#2c3e50' },
    { label: '面密度 P20', value: props.stats?.p20, unit: 'm⁻²', color: '#B85C38' },
    { label: '长度密度 P21', value: props.stats?.p21, unit: 'm⁻¹', color: '#2E7D5A' },
  ]
  if (props.showNodes !== false && ns.value) {
    base.push(
      { label: '节点总数', value: ns.value?.node_count, unit: '个', color: '#4A5568' },
      { label: '节点密度', value: nodeDensity.value, unit: '个/m²', color: '#7B1FA2' },
      { label: '退化跳过', value: ns.value?.degenerate_skipped, unit: '条', color: '#606266' },
      { label: '交叉节点 X', value: ns.value?.node_x_count, unit: '个', color: '#1565C0' },
      { label: '三叉节点 Y', value: ns.value?.node_y_count, unit: '个', color: '#E65100' },
      { label: '孤立端点 I', value: ns.value?.node_i_count, unit: '个', color: '#2E7D5A' },
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
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--tp-shadow-lg), 0 0 0 1px rgba(184, 92, 56, 0.06);
}

/* 顶部彩色指示条 */
.stat-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--accent-color, var(--tp-brand-accent));
  opacity: 0;
  transition: opacity var(--tp-duration-normal);
}

.stat-card:hover .stat-accent {
  opacity: 1;
}

.stat-top {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 6px;
}

.stat-value {
  font-size: 34px;
  font-weight: 700;
  color: var(--tp-text-primary);
  line-height: 1.2;
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
