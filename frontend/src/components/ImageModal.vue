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
        <div class="modal-body" v-loading="loading">
          <div class="img-grid">
            <div class="img-item" v-for="img in imageList" :key="img.key">
              <div class="img-wrapper">
                <img
                  v-if="img.dataUrl"
                  :src="img.dataUrl"
                  class="img-preview"
                  @click="previewImage(img.dataUrl)"
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
import { loadImageBase64 } from '@/utils/image'

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

const imageList = ref<Array<{ key: string; title: string; dataUrl: string }>>([])
const loading = ref(false)
const fullscreenSrc = ref('')

async function loadImages() {
  loading.value = true
  try {
    const list = []
    for (const img of props.images) {
      const dataUrl = img.src ? await loadImageBase64(img.src) : ''
      list.push({ key: img.key, title: img.title, dataUrl })
    }
    imageList.value = list
  } catch (e) {
    console.error('加载图片失败', e)
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

function previewImage(src: string) {
  fullscreenSrc.value = src
}
</script>

<style scoped lang="scss">
.image-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--tp-bg-overlay);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--tp-space-6);
  animation: modalOverlayIn 0.25s var(--tp-easing);
  backdrop-filter: blur(4px);
}

@keyframes modalOverlayIn {
  from { backdrop-filter: blur(0px); background: rgba(26, 35, 50, 0); }
  to { backdrop-filter: blur(4px); background: var(--tp-bg-overlay); }
}

.modal-content {
  background: var(--tp-bg-card);
  border-radius: var(--tp-radius-xl);
  width: 100%;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--tp-shadow-xl);
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
  background: var(--tp-bg-sunken);
  border-radius: var(--tp-radius-md);
  overflow: hidden;
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
