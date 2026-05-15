<template>
  <div class="style-preview">
    <div class="preview-header">
      <h3>预览</h3>
      <div class="overlay-controls">
        <el-checkbox v-model="showHull" size="small" @change="generatePreview">显示凸包</el-checkbox>
        <el-checkbox v-model="showCircles" size="small" @change="generatePreview">显示圆窗</el-checkbox>
        <el-checkbox v-model="showNodes" size="small" @change="generatePreview">显示节点</el-checkbox>
      </div>
    </div>

    <div class="preview-grid">
      <div class="preview-box" v-for="(img, idx) in previewImages" :key="img.key" @click="openViewer(idx)">
        <div class="preview-label">{{ img.label }}</div>
        <div class="preview-img-wrapper" v-loading="loading">
          <img v-if="img.url" :src="img.url" class="preview-img" />
          <el-empty v-else description="修改配置后自动生成预览" />
        </div>
      </div>
    </div>

    <el-alert v-if="errorMsg" :title="errorMsg" type="error" :closable="false" show-icon style="margin-top: 12px" />

    <ImageViewer
      v-model:visible="viewerVisible"
      :images="viewerImages"
      :initial-index="viewerInitialIndex"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { api } from '@/api/pywebview'
import { loadImageBase64 } from '@/utils/image'
import ImageViewer from '@/components/ImageViewer.vue'

interface PreviewImage {
  key: string
  label: string
  path: string
  url: string
}

const props = defineProps<{
  styleConfig: Record<string, any>
}>()

const previewImages = ref<PreviewImage[]>([
  { key: 'raw', label: '原始迹线图', path: '', url: '' },
  { key: 'rotated', label: '旋转迹线图', path: '', url: '' },
  { key: 'rose', label: '走向玫瑰图', path: '', url: '' },
])

const loading = ref(false)
const errorMsg = ref('')

const showHull = ref(true)
const showCircles = ref(true)
const showNodes = ref(true)

const viewerVisible = ref(false)
const viewerImages = ref<Array<{ title: string; src: string }>>([])
const viewerInitialIndex = ref(0)

function openViewer(index: number) {
  viewerImages.value = previewImages.value
    .filter((img) => img.url)
    .map((img) => ({ title: img.label, src: img.url }))
  viewerInitialIndex.value = index
  viewerVisible.value = true
}

let debounceTimer: number | null = null

async function doGenerate() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await api.generate_preview({
      style: { ...props.styleConfig },
      show_hull: showHull.value,
      show_circles: showCircles.value,
      show_nodes: showNodes.value,
    })
    if (res.status === 'ready') {
      const images = res.images || []
      for (const img of previewImages.value) {
        const match = images.find((item: any) => item.key === img.key)
        if (match && match.path) {
          img.path = match.path
          img.url = await loadImageBase64(match.path)
        } else {
          img.path = ''
          img.url = ''
        }
      }
    } else if (res.status === 'error') {
      errorMsg.value = res.message || '预览生成失败'
      for (const img of previewImages.value) {
        img.path = ''
        img.url = ''
      }
    }
  } catch (e: any) {
    errorMsg.value = e?.message || '预览生成失败'
    for (const img of previewImages.value) {
      img.path = ''
      img.url = ''
    }
  } finally {
    loading.value = false
  }
}

function generatePreview() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = window.setTimeout(doGenerate, 500)
}

watch(() => props.styleConfig, () => {
  generatePreview()
}, { deep: true })

// 初始加载
watch(() => props.styleConfig, (val) => {
  if (val && Object.keys(val).length > 0) {
    generatePreview()
  }
}, { immediate: true, deep: true })
</script>

<style scoped lang="scss">
.style-preview {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  margin-top: 16px;
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}
.preview-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}
.overlay-controls {
  display: flex;
  gap: 20px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}
.preview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-top: 12px;
}
.preview-box {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.preview-box:hover {
  box-shadow: 0 4px 12px 0 rgba(0,0,0,0.1);
}
.preview-label {
  padding: 8px;
  background: #f5f7fa;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
}
.preview-img-wrapper {
  position: relative;
  min-height: 260px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-img {
  max-width: 100%;
  max-height: 360px;
  object-fit: contain;
  image-rendering: -webkit-optimize-contrast;
}
@media (max-width: 768px) {
  .preview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
