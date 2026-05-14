<template>
  <div class="image-grid">
    <div
      v-for="(img, idx) in imageList"
      :key="img.key"
      class="grid-item"
      @mouseenter="hovered = img.key"
      @mouseleave="hovered = ''"
      @click="emit('click', idx)"
    >
      <img v-if="img.dataUrl" :src="img.dataUrl" class="grid-img" :class="{ hover: hovered === img.key }" />
      <el-empty v-else description="加载中" />
      <div class="grid-label">{{ img.label }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { loadImageBase64 } from '@/utils/image'

const props = defineProps<{
  images: { key: string; src: string; label: string }[]
}>()

const emit = defineEmits<{
  (e: 'click', index: number): void
}>()

const hovered = ref('')
const imageList = ref<{ key: string; dataUrl: string; label: string }[]>([])

async function loadImages() {
  const list = []
  for (const img of props.images) {
    const dataUrl = await loadImageBase64(img.src)
    list.push({ key: img.key, dataUrl, label: img.label })
  }
  imageList.value = list
}

watch(() => props.images, loadImages, { deep: true, immediate: true })
</script>

<style scoped lang="scss">
.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  margin-top: 16px;
}
.grid-item {
  background: #fff;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  transition: transform 0.2s;
}
.grid-img {
  width: 100%;
  height: 120px;
  object-fit: cover;
  display: block;
  transition: transform 0.2s;
}
.grid-img.hover {
  transform: scale(1.05);
}
.grid-label {
  padding: 6px 8px;
  font-size: 12px;
  color: #606266;
  text-align: center;
}
</style>
