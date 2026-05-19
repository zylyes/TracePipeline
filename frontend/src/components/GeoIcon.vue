<template>
  <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" :width="size" :height="size">
    <defs>
      <!-- 明亮的银灰金属边框，增加与背景的区分度 -->
      <linearGradient :id="'dial-' + gradientId" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#F8FAFC" />
        <stop offset="50%" stop-color="#CBD5E1" />
        <stop offset="100%" stop-color="#94A3B8" />
      </linearGradient>
      <!-- 亮红/朱红渐变指针与刻度，更显眼 -->
      <linearGradient :id="'needle-' + gradientId" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#EF4444" />
        <stop offset="100%" stop-color="#B91C1C" />
      </linearGradient>

      <filter :id="'shadow-' + gradientId" x="-10%" y="-10%" width="120%" height="120%">
        <feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000" flood-opacity="0.15" />
      </filter>
    </defs>

    <!-- 圆盘外侧物理边框，加入投影使其与背景剥离 -->
    <circle cx="32" cy="32" r="31" fill="none" :stroke="`url(#dial-${gradientId})`" stroke-width="2" :filter="`url(#shadow-${gradientId})`"/>
    <!-- 圆盘底板，去除底色以适应不同背景 -->
    <circle cx="32" cy="32" r="30" fill="none" :stroke="`url(#dial-${gradientId})`" stroke-width="1.5"/>

    <!-- 内圈刻度环背景 -->
    <circle cx="32" cy="32" r="24" fill="none" stroke="#64748B" stroke-width="1" opacity="0.3"/>

    <!-- 刻度线 (亮银色) -->
    <g stroke="#94A3B8" stroke-linecap="round">
      <line x1="32" y1="54" x2="32" y2="60" stroke-width="2.5"/> <!-- 南 -->
      <line x1="4"  y1="32" x2="10" y2="32" stroke-width="2.5"/> <!-- 西 -->
      <line x1="54" y1="32" x2="60" y2="32" stroke-width="2.5"/> <!-- 东 -->
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

    <!-- N 标记 (亮红) 移动到正北刻度的位置 -->
    <text x="32" y="10.5" text-anchor="middle" :fill="`url(#needle-${gradientId})`" font-size="10" font-weight="bold" font-family="Times New Roman, serif">N</text>

    <!-- 指北针（大三角形 - 亮红渐变） -->
    <polygon points="32,6 35,30 32,25 29,30" :fill="`url(#needle-${gradientId})`" :filter="`url(#shadow-${gradientId})`"/>
    <!-- 南方倒三角（小 - 银灰色） -->
    <polygon points="32,58 35,34 32,38 29,34" fill="currentColor" opacity="0.7"/>

    <!-- 中心测量点 -->
    <circle cx="32" cy="32" r="3.5" fill="#334155"/>
    <circle cx="32" cy="32" r="2" :fill="`url(#needle-${gradientId})`"/>

    <!-- 产状线（虚线迹线 - 深色带红） -->
    <line x1="16" y1="48" x2="48" y2="16" stroke="#991B1B" stroke-width="1.5" opacity="0.8" stroke-dasharray="4,2"/>
    <!-- 产状线端点 -->
    <circle cx="16" cy="48" r="2" :fill="`url(#needle-${gradientId})`" opacity="0.9"/>
    <circle cx="48" cy="16" r="2" :fill="`url(#needle-${gradientId})`" opacity="0.9"/>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  size?: number | string
  color?: string
}>(), {
  size: 24,
  color: '#EF4444',
})

// 生成随机ID防止多实例冲突
const uniqueSuffix = Math.random().toString(36).substring(2, 9)
const gradientId = computed(() => `geoicon-${uniqueSuffix}`)
</script>
