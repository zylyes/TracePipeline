<template>
  <Compass :size="size" :color="color" :stroke-width="1.5" />
</template>
<script setup lang="ts">
import { Compass } from '@lucide/vue'
withDefaults(defineProps<{ size?: number; color?: string }>(), { size: 24, color: '#0284C7' })
</script>
