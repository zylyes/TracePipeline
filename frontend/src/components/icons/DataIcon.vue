<template>
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"
       :width="size" :height="size" fill="none"
       :stroke="color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <!-- 网格 4列×3行 -->
    <rect x="2" y="4" width="20" height="17" rx="1.5" />
    <!-- 竖线 -->
    <line x1="7" y1="4" x2="7" y2="21" />
    <line x1="12" y1="4" x2="12" y2="21" />
    <line x1="17" y1="4" x2="17" y2="21" />
    <!-- 横线 -->
    <line x1="2" y1="9.5" x2="22" y2="9.5" />
    <line x1="2" y1="15" x2="22" y2="15" />
    <!-- 表头行淡色填充 -->
    <rect x="2" y="4" width="20" height="5.5" rx="1.5" :fill="color" stroke="none" opacity="0.1" />
    <!-- 数据点标记（小菱形） -->
    <polygon points="9.5,9 10.5,8 11.5,9 10.5,10" :fill="color" stroke="none" opacity="0.7" />
    <polygon points="14.5,12.5 15.5,11.5 16.5,12.5 15.5,13.5" :fill="color" stroke="none" opacity="0.5" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number; color?: string }>(), {
  size: 24,
  color: '#7C3AED',
})
</script>
