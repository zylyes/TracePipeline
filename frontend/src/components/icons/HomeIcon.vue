<template>
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"
       :width="size" :height="size" fill="none"
       :stroke="color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <!-- 外圆 -->
    <circle cx="12" cy="12" r="10" />
    <!-- 内圈刻度环 -->
    <circle cx="12" cy="12" r="7" opacity="0.3" />
    <!-- N 标记 -->
    <text x="12" y="6" text-anchor="middle" :fill="color" stroke="none"
          font-size="5.5" font-weight="bold" font-family="Times New Roman, serif">N</text>
    <!-- 指北针（上三角） -->
    <polygon points="12,3 13.5,11 12,9 10.5,11" :fill="color" stroke="none" />
    <!-- 南指针（下三角，半透明） -->
    <polygon points="12,21 13.5,13 12,15 10.5,13" :fill="color" stroke="none" opacity="0.25" />
    <!-- 中心点 -->
    <circle cx="12" cy="12" r="1.5" :fill="color" stroke="none" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number; color?: string }>(), {
  size: 24,
  color: '#C96B4F',
})
</script>
