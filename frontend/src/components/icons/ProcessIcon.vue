<template>
  <Workflow :size="size" :color="color" :stroke-width="1.5" />
</template>
<script setup lang="ts">
import { Workflow } from '@lucide/vue'
withDefaults(defineProps<{ size?: number; color?: string }>(), { size: 24, color: '#0369A1' })
</script>
