<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="image-modal"
      @click.self="close"
      @keydown.esc="close"
      tabindex="-1"
    >
      <div class="modal-content">
        <div class="modal-header">
          <span class="modal-title">{{ outcrop }} 处理结果</span>
          <el-button circle :icon="Close" size="small" @click="close" />
        </div>
        <div class="modal-body" v-loading="loading" element-loading-text="正在载入结果图">
          <div class="img-grid">
            <div class="img-item" v-for="img in imageList" :key="img.key">
              <div class="img-wrapper">
                <img
                  v-if="img.dataUrl"
                  :src="img.dataUrl"
                  class="img-preview"
                  @click="previewImage(img)"
                />
                <el-empty v-else description="图片未生成" />
              </div>
              <div class="img-title">{{ img.title }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
  <Teleport to="body">
    <div v-if="fullscreenSrc" class="fullscreen-viewer" @click="fullscreenSrc = ''">
      <img :src="fullscreenSrc" class="fullscreen-img" />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Close } from '@element-plus/icons-vue'
import { loadImageBase64, loadImageThumbnail } from '@/utils/image'
import { msg } from '@/utils/message'

interface ImageInfo {
  key: string
  title: string
  src: string
}

const props = defineProps<{
  visible: boolean
  outcrop: string
  images: ImageInfo[]
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
}>()

const GRID_THUMBNAIL_MAX_PX = 640

const imageList = ref<Array<{ key: string; title: string; dataUrl: string; path: string }>>([])
const loading = ref(false)
const fullscreenSrc = ref('')

async function loadImages() {
  loading.value = true
  try {
    const list = []
    for (const img of props.images) {
      const path = img.src || ''
      // 网格预览使用缩略图，减少内存占用
      const dataUrl = path ? await loadImageThumbnail(path, GRID_THUMBNAIL_MAX_PX) : ''
      list.push({ key: img.key, title: img.title, dataUrl, path })
    }
    imageList.value = list
  } catch (e) {
    console.error('加载图片缩略图失败', e)
    msg.warning('部分图片加载失败')
  } finally {
    loading.value = false
  }
}

watch([() => props.visible, () => props.images], ([visible, images]) => {
  if (visible && images.length > 0) {
    loadImages()
  }
})

function close() {
  emit('update:visible', false)
}

async function previewImage(img: { key: string; title: string; dataUrl: string; path: string }) {
  // 全屏查看时再加载原图
  if (!img.path) return
  try {
    fullscreenSrc.value = await loadImageBase64(img.path)
  } catch (e) {
    console.error('加载原图失败', e)
    msg.warning('原图加载失败')
  }
}
</script>

<style scoped lang="scss">
.image-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    radial-gradient(circle at 50% 45%, rgba(56, 189, 248, 0.12), transparent 32%),
    var(--tp-bg-overlay);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--tp-space-6);
  animation: modalOverlayIn 0.25s var(--tp-easing);
  backdrop-filter: blur(8px) saturate(1.08);
}

@keyframes modalOverlayIn {
  from { backdrop-filter: blur(0px); background: rgba(26, 35, 50, 0); }
  to { backdrop-filter: blur(4px); background: var(--tp-bg-overlay); }
}

.modal-content {
  background: var(--tp-surface-cyber);
  border-radius: var(--tp-radius-xl);
  width: 100%;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--tp-shadow-xl), var(--tp-glow-cyan-sm);
  border: 1px solid rgba(125, 211, 252, 0.22);
  animation: modalContentIn 0.35s var(--tp-easing-expo);
}

@keyframes modalContentIn {
  from { opacity: 0; transform: scale(0.9) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--tp-space-4) var(--tp-space-5);
  border-bottom: 1px solid var(--tp-border-light);
}

.modal-title {
  font-family: var(--tp-font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--tp-text-primary);
}

.modal-body {
  padding: var(--tp-space-5);
  overflow-y: auto;
  flex: 1;
}

.img-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: var(--tp-space-4);
}

.img-item {
  background: linear-gradient(180deg, rgba(255,255,255,0.78), var(--tp-bg-sunken));
  border-radius: var(--tp-radius-md);
  overflow: hidden;
  border: 1px solid rgba(125, 211, 252, 0.12);
}

.img-item:last-child:nth-child(odd) {
  grid-column: 1 / -1;
  max-width: 50%;
  margin: 0 auto;
}

.img-title {
  padding: var(--tp-space-2) var(--tp-space-3);
  font-family: var(--tp-font-heading);
  font-size: 13px;
  font-weight: 600;
  color: var(--tp-text-primary);
  background: var(--tp-bg-hover);
  text-align: center;
}

.img-wrapper {
  padding: var(--tp-space-3);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  background:
    linear-gradient(rgba(2, 132, 199, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(2, 132, 199, 0.03) 1px, transparent 1px);
  background-size: 22px 22px;
}

.img-preview {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
  cursor: zoom-in;
  transition: transform var(--tp-duration-normal) var(--tp-easing);
}

.img-preview:hover {
  transform: scale(1.02);
  filter: drop-shadow(0 10px 24px rgba(26, 54, 93, 0.16));
}

.fullscreen-viewer {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  cursor: zoom-out;
  backdrop-filter: blur(4px);
}

.fullscreen-img {
  max-width: 95%;
  max-height: 95%;
  object-fit: contain;
}
</style>
