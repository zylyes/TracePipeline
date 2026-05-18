<template>
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"
       :width="size" :height="size" fill="none"
       :stroke="color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <!-- 罗盘外圆 -->
    <circle cx="12" cy="12" r="10" />
    <!-- 水平线（测线方向） -->
    <line x1="2" y1="12" x2="22" y2="12" />
    <!-- 中心十字 -->
    <line x1="12" y1="3" x2="12" y2="21" />
    <!-- 中心点 -->
    <circle cx="12" cy="12" r="1.5" :fill="color" stroke="none" />
    <!-- 左上调节旋钮 -->
    <circle cx="4" cy="4" r="1.5" :fill="color" stroke="none" opacity="0.5" />
    <!-- 右侧刻度标记 -->
    <line x1="22" y1="7"  x2="21" y2="7"  stroke-width="1" opacity="0.4" />
    <line x1="22" y1="12" x2="21" y2="12" stroke-width="1" opacity="0.6" />
    <line x1="22" y1="17" x2="21" y2="17" stroke-width="1" opacity="0.4" />
    <!-- 底部刻度标记 -->
    <line x1="7"  y1="22" x2="7"  y2="21" stroke-width="1" opacity="0.4" />
    <line x1="12" y1="22" x2="12" y2="21" stroke-width="1" opacity="0.6" />
    <line x1="17" y1="22" x2="17" y2="21" stroke-width="1" opacity="0.4" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number; color?: string }>(), {
  size: 24,
  color: '#B89A6A',
})
</script>
