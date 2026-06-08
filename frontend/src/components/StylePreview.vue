<template>
  <div class="style-preview">
    <div class="preview-header">
      <h3>预览</h3>
      <div class="overlay-controls">
        <el-button size="small" type="primary" plain @click="generatePreview">生成预览</el-button>
        <el-checkbox v-model="showHull" size="small" @change="generatePreview">显示凸包</el-checkbox>
        <el-checkbox v-model="showCircles" size="small" @change="generatePreview">显示圆窗</el-checkbox>
        <el-checkbox v-model="showNodes" size="small" @change="generatePreview">显示节点</el-checkbox>
      </div>
    </div>

    <div class="preview-grid">
      <div class="preview-box" v-for="(img, idx) in previewImages" :key="img.key" @click="openViewer(idx)">
        <div class="preview-img-wrapper" v-loading="loading">
          <img v-if="img.url" :src="img.url" class="preview-img" />
          <el-empty v-else description="点击生成预览后显示" />
        </div>
        <div class="preview-label">{{ img.label }}</div>
      </div>
    </div>

    <el-alert v-if="errorMsg" :title="errorMsg" type="error" :closable="false" show-icon style="margin-top: 12px" />

    <ImageViewer
      v-model:visible="viewerVisible"
      :images="viewerImages"
      :initial-index="viewerInitialIndex"
      @index-change="handleViewerIndexChange"
    />
  </div>
</template>

<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { api } from '@/api/pywebview'
import { loadImageBase64, loadImageThumbnail } from '@/utils/image'
import ImageViewer from '@/components/ImageViewer.vue'

const emit = defineEmits<{
  (e: 'save-style'): void
  (e: 'reset-style'): void
}>()

interface PreviewImage {
  key: string
  label: string
  path: string
  url: string
  fullUrl?: string
  fullLoadPromise?: Promise<void>
}

const props = defineProps<{
  styleConfig: Record<string, any>
  previewTrigger: number
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

const PREVIEW_THUMBNAIL_MAX_PX = 640

function viewerSourceImages() {
  return previewImages.value.filter((img) => img.url || img.fullUrl)
}

function syncViewerImages() {
  viewerImages.value = viewerSourceImages()
    .map((img) => ({ title: img.label, src: img.fullUrl || img.url }))
}

async function ensureFullPreviewImage(img: PreviewImage) {
  if (img.fullUrl || !img.path) return
  if (img.fullLoadPromise) return img.fullLoadPromise
  img.fullLoadPromise = (async () => {
    try {
      img.fullUrl = await loadImageBase64(img.path)
      if (viewerVisible.value) syncViewerImages()
    } finally {
      img.fullLoadPromise = undefined
    }
  })()
  return img.fullLoadPromise
}

async function openViewer(index: number) {
  const target = previewImages.value[index]
  if (!target || (!target.url && !target.path)) return
  await ensureFullPreviewImage(target)
  const sources = viewerSourceImages()
  viewerInitialIndex.value = Math.max(0, sources.findIndex((img) => img.key === target.key))
  syncViewerImages()
  viewerVisible.value = true
}

async function handleViewerIndexChange(index: number) {
  const target = viewerSourceImages()[index]
  if (target) await ensureFullPreviewImage(target)
}

let debounceTimer: number | null = null

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})

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
          img.url = await loadImageThumbnail(match.path, PREVIEW_THUMBNAIL_MAX_PX)
          img.fullUrl = ''
        } else {
          img.path = ''
          img.url = ''
          img.fullUrl = ''
        }
      }
    } else if (res.status === 'error') {
      errorMsg.value = res.message || '预览生成失败'
      for (const img of previewImages.value) {
        img.path = ''
        img.url = ''
        img.fullUrl = ''
      }
    }
  } catch (e: any) {
    errorMsg.value = e?.message || '预览生成失败'
    for (const img of previewImages.value) {
      img.path = ''
      img.url = ''
      img.fullUrl = ''
    }
  } finally {
    loading.value = false
  }
}

function generatePreview() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = window.setTimeout(doGenerate, 500)
}

watch(() => props.previewTrigger, () => {
  generatePreview()
})
</script>

<style scoped lang="scss">
.style-preview {
  background: var(--tp-bg-card);
  border-radius: var(--tp-radius-lg);
  padding: var(--tp-space-3) var(--tp-space-4);
  box-shadow: var(--tp-shadow-md);
  border: 1px solid var(--tp-border-light);
  margin-top: var(--tp-space-4);
}
.preview-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--tp-space-3) var(--tp-space-4);
  margin-bottom: var(--tp-space-3);
}
.preview-header h3 {
  margin: 0;
  font-family: var(--tp-font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--tp-text-primary);
  white-space: nowrap;
}
.overlay-controls {
  display: flex;
  gap: 18px;
  padding: var(--tp-space-2) var(--tp-space-4);
  background: var(--tp-bg-sunken);
  border-radius: var(--tp-radius-sm);
  flex-shrink: 0;
  margin-left: auto;
}
.preview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: var(--tp-space-3);
}
.preview-box {
  border: 1px solid var(--tp-border-light);
  border-radius: var(--tp-radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow var(--tp-duration-normal) var(--tp-easing);
}
.preview-box:hover {
  box-shadow: var(--tp-shadow-lg);
}
.preview-label {
  padding: var(--tp-space-2);
  background: var(--tp-bg-sunken);
  font-family: var(--tp-font-heading);
  font-size: 13px;
  font-weight: 600;
  text-align: center;
}
.preview-img-wrapper {
  position: relative;
  min-height: 240px;
  background: var(--tp-bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-img {
  max-width: 100%;
  max-height: 340px;
  object-fit: contain;
  image-rendering: -webkit-optimize-contrast;
}
@media (max-width: 900px) {
  .preview-grid {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 768px) {
  .preview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
