<template>
  <div class="image-preview">
    <div class="preview-card" v-for="img in imageList" :key="img.key">
      <div class="preview-title">{{ img.title }}</div>
      <div class="image-wrapper">
        <img v-if="img.dataUrl" :src="img.dataUrl" class="preview-img" @click="previewImage(img.dataUrl)" />
        <el-empty v-else description="暂无图片" />
      </div>
      <div class="preview-options" v-if="img.key !== 'rose' && img.key.indexOf('rose-') !== 0">
        <el-checkbox v-model="img.showOverlay">显示覆盖层</el-checkbox>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { loadImageBase64 } from '@/utils/image'

interface ImageItem {
  key: string
  title: string
  src: string
}

const props = defineProps<{
  images: ImageItem[]
}>()

const imageList = ref<Array<{ key: string; title: string; dataUrl: string; showOverlay: boolean }>>([])

async function loadImages() {
  const list = []
  for (const img of props.images) {
    const dataUrl = await loadImageBase64(img.src)
    list.push({ key: img.key, title: img.title, dataUrl, showOverlay: true })
  }
  imageList.value = list
}

watch(() => props.images, loadImages, { deep: true, immediate: true })

function previewImage(src: string) {
  const viewer = document.createElement('div')
  viewer.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);display:flex;align-items:center;justify-content:center;z-index:9999;cursor:zoom-out;'
  const imgEl = document.createElement('img')
  imgEl.src = src
  imgEl.style.cssText = 'max-width:90%;max-height:90%;'
  viewer.appendChild(imgEl)
  viewer.onclick = () => document.body.removeChild(viewer)
  document.body.appendChild(viewer)
}
</script>

<style scoped lang="scss">
.image-preview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-top: 16px;
}
.preview-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
}
.preview-title {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 8px;
  text-align: center;
}
.image-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 4/3;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
}
.preview-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  cursor: zoom-in;
}
.preview-options {
  margin-top: 8px;
  text-align: center;
}
</style>
