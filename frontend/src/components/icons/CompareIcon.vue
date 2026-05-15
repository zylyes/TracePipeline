<template>
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"
       :width="size" :height="size" fill="none"
       :stroke="color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <!-- 左侧岩体剖面（梯形） -->
    <polygon points="2,6 9,6 11,20 0,20" />
    <!-- 左侧层理 -->
    <line x1="1" y1="10" x2="9.5" y2="10" opacity="0.4" />
    <line x1="0.5" y1="14" x2="10" y2="14" opacity="0.4" />
    <line x1="0" y1="18" x2="10.5" y2="18" opacity="0.4" />
    <!-- 右侧岩体剖面（梯形，略小） -->
    <polygon points="13,8 20,8 22,20 11,20" />
    <!-- 右侧层理 -->
    <line x1="12" y1="12" x2="20.5" y2="12" opacity="0.4" />
    <line x1="11.5" y1="16" x2="21" y2="16" opacity="0.4" />
    <!-- 对比虚线连接 -->
    <line x1="6" y1="8" x2="16.5" y2="10" stroke-dasharray="2,1.5" opacity="0.6" />
    <!-- 双箭头 -->
    <line x1="4" y1="5" x2="22" y2="5" stroke-width="1" opacity="0.5" />
    <polyline points="5,3 4,5 5,7" opacity="0.5" />
    <polyline points="19,3 20,5 19,7" opacity="0.5" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number; color?: string }>(), {
  size: 24,
  color: '#4A5568',
})
</script>
