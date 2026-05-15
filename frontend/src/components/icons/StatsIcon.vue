<template>
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"
       :width="size" :height="size" fill="none"
       :stroke="color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <!-- 柱1（最低） -->
    <rect x="2" y="14" width="5" height="8" rx="1" />
    <line x1="2.5" y1="16.5" x2="6.5" y2="16.5" opacity="0.5" />
    <line x1="2.5" y1="19" x2="6.5" y2="19" opacity="0.5" />
    <!-- 柱2（中等） -->
    <rect x="9.5" y="9" width="5" height="13" rx="1" />
    <line x1="10" y1="11.5" x2="14" y2="11.5" opacity="0.5" />
    <line x1="10" y1="14" x2="14" y2="14" opacity="0.5" />
    <line x1="10" y1="16.5" x2="14" y2="16.5" opacity="0.5" />
    <line x1="10" y1="19" x2="14" y2="19" opacity="0.5" />
    <!-- 柱3（最高） -->
    <rect x="17" y="4" width="5" height="18" rx="1" />
    <line x1="17.5" y1="6.5" x2="21.5" y2="6.5" opacity="0.5" />
    <line x1="17.5" y1="9" x2="21.5" y2="9" opacity="0.5" />
    <line x1="17.5" y1="11.5" x2="21.5" y2="11.5" opacity="0.5" />
    <line x1="17.5" y1="14" x2="21.5" y2="14" opacity="0.5" />
    <line x1="17.5" y1="16.5" x2="21.5" y2="16.5" opacity="0.5" />
    <line x1="17.5" y1="19" x2="21.5" y2="19" opacity="0.5" />
    <!-- 基线 -->
    <line x1="1.5" y1="22" x2="22.5" y2="22" stroke-width="1" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number; color?: string }>(), {
  size: 24,
  color: '#2E7D5A',
})
</script>
