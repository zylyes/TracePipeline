<template>
  <div class="stat-cards">
    <div class="stat-card" v-for="card in cards" :key="card.label">
      <div class="stat-value tp-data">{{ formatValue(card.value) }}</div>
      <div class="stat-unit">{{ card.unit }}</div>
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
  }
}>()

const cards = computed(() => [
  { label: '线密度 P10', value: props.stats?.p10, unit: 'm⁻¹' },
  { label: '面密度 P20', value: props.stats?.p20, unit: 'm⁻²' },
  { label: '长度密度 P21', value: props.stats?.p21, unit: 'm⁻¹' },
])

function formatValue(v: number | null | undefined) {
  if (v === null || v === undefined || (typeof v === 'number' && isNaN(v))) return '—'
  return Number(v).toFixed(2)
}
</script>

<style scoped lang="scss">
.stat-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  text-align: center;
}
.stat-value {
  font-size: 36px;
  font-weight: 600;
  color: #2c3e50;
  line-height: 1.2;
  font-family: "Times New Roman", serif;
}
.stat-unit {
  font-size: 14px;
  color: #7f8c8d;
  margin-top: 4px;
}
.stat-label {
  font-size: 13px;
  color: #7f8c8d;
  margin-top: 8px;
}
</style>
