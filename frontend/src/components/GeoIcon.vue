<template>
  <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" :width="size" :height="size">
    <!-- 深色圆盘底 -->
    <circle cx="32" cy="32" r="30" fill="#1E2935" stroke="#B85C38" stroke-width="3"/>
    <!-- 内圈刻度环背景 -->
    <circle cx="32" cy="32" r="24" fill="none" stroke="#B85C38" stroke-width="1" opacity="0.3"/>
    <!-- 刻度线（每30°一根长刻度，每10°一根短刻度） -->
    <g stroke="#B85C38" stroke-linecap="round">
      <line x1="32" y1="4"  x2="32" y2="10" stroke-width="2.5"/>
      <line x1="32" y1="54" x2="32" y2="60" stroke-width="2.5"/>
      <line x1="4"  y1="32" x2="10" y2="32" stroke-width="2.5"/>
      <line x1="54" y1="32" x2="60" y2="32" stroke-width="2.5"/>
      <line x1="11.7" y1="11.7" x2="16" y2="16" stroke-width="2"/>
      <line x1="48" y1="48" x2="52.3" y2="52.3" stroke-width="2"/>
      <line x1="11.7" y1="52.3" x2="16" y2="48" stroke-width="2"/>
      <line x1="48" y1="16" x2="52.3" y2="11.7" stroke-width="2"/>
      <!-- 短刻度 -->
      <line x1="22.3" y1="6.5" x2="23.8" y2="10.5" stroke-width="1.2"/>
      <line x1="40.2" y1="6.5" x2="38.7" y2="10.5" stroke-width="1.2"/>
      <line x1="6.5" y1="22.3" x2="10.5" y2="23.8" stroke-width="1.2"/>
      <line x1="6.5" y1="40.2" x2="10.5" y2="38.7" stroke-width="1.2"/>
      <line x1="22.3" y1="57.5" x2="23.8" y2="53.5" stroke-width="1.2"/>
      <line x1="40.2" y1="57.5" x2="38.7" y2="53.5" stroke-width="1.2"/>
      <line x1="57.5" y1="22.3" x2="53.5" y2="23.8" stroke-width="1.2"/>
      <line x1="57.5" y1="40.2" x2="53.5" y2="38.7" stroke-width="1.2"/>
    </g>
    <!-- N 标记 -->
    <text x="32" y="16" text-anchor="middle" fill="#B85C38" font-size="10" font-weight="bold" font-family="Times New Roman, serif">N</text>
    <!-- 指北针（大三角形） -->
    <polygon points="32,6 35,30 32,25 29,30" fill="#B85C38"/>
    <!-- 南方倒三角（小） -->
    <polygon points="32,58 35,34 32,38 29,34" fill="#7f8c8d" opacity="0.8"/>
    <!-- 中心测量点 -->
    <circle cx="32" cy="32" r="3" fill="#B85C38"/>
    <circle cx="32" cy="32" r="1.5" fill="#1E2935"/>
    <!-- 产状线（虚线迹线） -->
    <line x1="16" y1="48" x2="48" y2="16" stroke="#B85C38" stroke-width="1.5" opacity="0.8" stroke-dasharray="4,2"/>
    <!-- 产状线端点 -->
    <circle cx="16" cy="48" r="1.5" fill="#B85C38" opacity="0.8"/>
    <circle cx="48" cy="16" r="1.5" fill="#B85C38" opacity="0.8"/>
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  size?: number | string
  color?: string
}>(), {
  size: 24,
  color: '#B85C38',
})
</script>
