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
              <div class="img-title">{{ img.title }}</div>
              <div class="img-wrapper">
                <img
                  v-if="img.dataUrl"
                  :src="img.dataUrl"
                  class="img-preview"
                  @click="previewImage(img.dataUrl)"
                />
                <el-empty v-else description="图片未生成" />
              </div>
            </div>
          </div>
        </div>
      </div>
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

watch(() => [props.visible, props.images], () => {
  if (props.visible && props.images.length > 0) {
    loadImages()
  }
}, { deep: true })

function close() {
  emit('update:visible', false)
}

function previewImage(src: string) {
  const viewer = document.createElement('div')
  viewer.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:flex;align-items:center;justify-content:center;z-index:10000;cursor:zoom-out;'
  const imgEl = document.createElement('img')
  imgEl.src = src
  imgEl.style.cssText = 'max-width:95%;max-height:95%;object-fit:contain;'
  viewer.appendChild(imgEl)
  viewer.onclick = () => document.body.removeChild(viewer)
  document.body.appendChild(viewer)
}
</script>

<style scoped lang="scss">
.image-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal-content {
  background: #fff;
  border-radius: 8px;
  width: 100%;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.img-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 16px;
}

.img-item {
  background: #f5f7fa;
  border-radius: 6px;
  overflow: hidden;
}

.img-item:last-child:nth-child(odd) {
  grid-column: 1 / -1;
  max-width: 50%;
  margin: 0 auto;
}

.img-title {
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #2c3e50;
  background: #e4e7ed;
  text-align: center;
}

.img-wrapper {
  padding: 12px;
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
  transition: transform 0.2s;
}

.img-preview:hover {
  transform: scale(1.02);
}
</style>
