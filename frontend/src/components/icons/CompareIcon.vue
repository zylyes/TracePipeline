<template>
  <Layers2 :size="size" :color="color" :stroke-width="1.5" />
</template>
<script setup lang="ts">
import { Layers2 } from '@lucide/vue'
withDefaults(defineProps<{ size?: number; color?: string }>(), { size: 24, color: '#0369A1' })
</script>
