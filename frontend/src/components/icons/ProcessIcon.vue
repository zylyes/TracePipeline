<template>
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"
       :width="size" :height="size" fill="none"
       :stroke="color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <!-- 菱形晶体（岩芯样本） -->
    <polygon points="12,2 21,12 12,22 3,12" />
    <!-- 水平扫描线 -->
    <line x1="4" y1="12" x2="20" y2="12" />
    <!-- 扫描脉冲点 -->
    <line x1="8" y1="12" x2="10" y2="12" stroke-width="2" />
    <line x1="14" y1="12" x2="16" y2="12" stroke-width="2" />
    <!-- 中心测量标记 -->
    <circle cx="12" cy="12" r="1.2" :fill="color" stroke="none" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number; color?: string }>(), {
  size: 24,
  color: '#C96B4F',
})
</script>
