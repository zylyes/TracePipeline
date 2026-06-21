<template>
  <div 
    class="tp-skeleton" 
    :class="[
      `variant-${variant}`, 
      { 'is-animated': animate }
    ]"
    :style="{
      width: width,
      height: computedHeight,
      borderRadius: computedRadius
    }"
  >
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  width?: string
  height?: string
  radius?: string
  variant?: 'line' | 'rect' | 'circle'
  animate?: boolean
}>(), {
  width: '100%',
  height: '',
  radius: '',
  variant: 'line',
  animate: true
})

// 根据 variant 设置默认样式（如果未显式提供）
const computedRadius = computed(() => {
  if (props.radius) return props.radius
  if (props.variant === 'circle') return '50%'
  if (props.variant === 'rect') return '8px'
  return '4px' // line 默认圆角
})

const computedHeight = computed(() => {
  if (props.height) return props.height
  if (props.variant === 'circle') return props.width // 圆形默认高度等于宽度
  if (props.variant === 'rect') return '100%'
  return '16px' // line 默认高度
})
</script>

<style scoped lang="scss">
.tp-skeleton {
  position: relative;
  overflow: hidden;
  background: var(--tp-surface-2, #21262d);
  display: block;
}

.tp-skeleton.is-animated::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.06) 50%,
    transparent 100%
  );
  animation: tp-shimmer-pass 1.5s ease-in-out infinite;
  /* 强制使用硬件加速，避免重绘 */
  will-change: transform;
}

/* 根据 variant 设置一些默认行为 */
.variant-circle {
  aspect-ratio: 1 / 1;
}

.variant-line {
  margin-bottom: 8px;
}
</style>
