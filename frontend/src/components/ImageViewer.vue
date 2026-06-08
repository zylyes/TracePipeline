<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="image-viewer"
      @click.self="close"
      @wheel.prevent="onWheel"
      @keydown.esc="close"
      tabindex="-1"
      ref="viewerRef"
    >
      <!-- 关闭按钮 -->
      <div class="viewer-toolbar top">
        <span class="viewer-title">{{ currentTitle }}</span>
        <div class="viewer-actions">
          <el-button circle :icon="ZoomOut" size="small" @click="zoomOut" />
          <el-button circle :icon="ZoomIn" size="small" @click="zoomIn" />
          <el-button circle :icon="RefreshRight" size="small" @click="resetZoom" />
          <el-button circle :icon="Close" size="small" @click="close" />
        </div>
      </div>

      <!-- 左右切换箭头 -->
      <div
        v-if="props.images.length > 1"
        class="nav-arrow nav-left"
        @click="prevImage"
      >
        <el-icon><ArrowLeft /></el-icon>
      </div>
      <div
        v-if="props.images.length > 1"
        class="nav-arrow nav-right"
        @click="nextImage"
      >
        <el-icon><ArrowRight /></el-icon>
      </div>

      <!-- 图片容器 -->
      <div
        class="viewer-content"
        @mousedown="onMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @mouseleave="onMouseUp"
      >
        <img
          v-if="currentSrc"
          :src="currentSrc"
          class="viewer-img"
          :style="imageStyle"
          draggable="false"
        />
        <el-empty v-else description="图片加载中" />
      </div>

      <!-- 底部信息 -->
      <div class="viewer-toolbar bottom">
        <span class="zoom-info">{{ Math.round(scale * 100) }}%</span>
        <span v-if="props.images.length > 1" class="page-info">
          {{ currentIndex + 1 }} / {{ props.images.length }}
        </span>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { Close, ZoomIn, ZoomOut, RefreshRight, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'

interface ImageItem {
  title: string
  src: string
}

const props = defineProps<{
  visible: boolean
  images: ImageItem[]
  initialIndex?: number
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'index-change', val: number): void
}>()

const viewerRef = ref<HTMLDivElement>()
const currentIndex = ref(props.initialIndex ?? 0)
const scale = ref(1)
let lastWheelTime = 0
const WHEEL_THROTTLE_MS = 80
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragOffsetX = ref(0)
const dragOffsetY = ref(0)

const currentSrc = computed(() => {
  const img = props.images[currentIndex.value]
  return img?.src || ''
})

const currentTitle = computed(() => {
  const img = props.images[currentIndex.value]
  return img?.title || ''
})

const imageStyle = computed(() => {
  return {
    transform: `translate(${translateX.value + dragOffsetX.value}px, ${translateY.value + dragOffsetY.value}px) scale(${scale.value})`,
    transition: isDragging.value ? 'none' : 'transform 0.15s ease-out',
    cursor: scale.value > 1 ? (isDragging.value ? 'grabbing' : 'grab') : 'default',
  }
})

watch(() => props.visible, (val) => {
  if (val) {
    currentIndex.value = props.initialIndex ?? 0
    resetZoom()
    emit('index-change', currentIndex.value)
    nextTick(() => viewerRef.value?.focus())
    window.addEventListener('keydown', onKeydown)
  } else {
    window.removeEventListener('keydown', onKeydown)
  }
})

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    close()
  } else if (e.key === 'ArrowLeft') {
    prevImage()
  } else if (e.key === 'ArrowRight') {
    nextImage()
  }
}

watch(() => props.initialIndex, (val) => {
  if (val !== undefined) {
    currentIndex.value = val
    if (props.visible) emit('index-change', currentIndex.value)
  }
})

function close() {
  emit('update:visible', false)
}

function zoomIn() {
  scale.value = Math.min(scale.value * 1.2, 5)
}

function zoomOut() {
  const newScale = Math.max(scale.value / 1.2, 0.5)
  scale.value = newScale
  if (newScale <= 1) {
    translateX.value = 0
    translateY.value = 0
  }
}

function resetZoom() {
  scale.value = 1
  translateX.value = 0
  translateY.value = 0
  dragOffsetX.value = 0
  dragOffsetY.value = 0
}

function onWheel(e: WheelEvent) {
  const now = Date.now()
  if (now - lastWheelTime < WHEEL_THROTTLE_MS) return
  lastWheelTime = now
  if (e.deltaY > 0) {
    zoomOut()
  } else {
    zoomIn()
  }
}

function prevImage() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    resetZoom()
  } else {
    currentIndex.value = props.images.length - 1
    resetZoom()
  }
  emit('index-change', currentIndex.value)
}

function nextImage() {
  if (currentIndex.value < props.images.length - 1) {
    currentIndex.value++
    resetZoom()
  } else {
    currentIndex.value = 0
    resetZoom()
  }
  emit('index-change', currentIndex.value)
}

function onMouseDown(e: MouseEvent) {
  if (scale.value <= 1) return
  isDragging.value = true
  dragStartX.value = e.clientX
  dragStartY.value = e.clientY
  dragOffsetX.value = 0
  dragOffsetY.value = 0
}

function onMouseMove(e: MouseEvent) {
  if (!isDragging.value) return
  dragOffsetX.value = e.clientX - dragStartX.value
  dragOffsetY.value = e.clientY - dragStartY.value
}

function onMouseUp() {
  if (!isDragging.value) return
  isDragging.value = false
  translateX.value += dragOffsetX.value
  translateY.value += dragOffsetY.value
  dragOffsetX.value = 0
  dragOffsetY.value = 0
}
</script>

<style scoped lang="scss">
.image-viewer {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.92);
  z-index: 10000;
  display: flex;
  flex-direction: column;
  outline: none;
  animation: viewerFadeIn 0.25s var(--tp-easing);
  backdrop-filter: blur(6px);
}

@keyframes viewerFadeIn {
  from { opacity: 0; backdrop-filter: blur(0); }
  to { opacity: 1; backdrop-filter: blur(6px); }
}

.viewer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  color: var(--tp-text-inverse);
  flex-shrink: 0;
}

.viewer-toolbar.top {
  background: linear-gradient(to bottom, rgba(0,0,0,0.6), transparent);
}

.viewer-toolbar.bottom {
  background: linear-gradient(to top, rgba(0,0,0,0.6), transparent);
  justify-content: center;
  gap: 24px;
  font-size: 13px;
  color: rgba(255,255,255,0.8);
}

.viewer-title {
  font-size: 14px;
  font-weight: 500;
}

.viewer-actions {
  display: flex;
  gap: 8px;
}

.nav-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.7);
  font-size: 28px;
  cursor: pointer;
  transition: all var(--tp-duration-normal) var(--tp-easing);
  z-index: 2;
  border-radius: var(--tp-radius-xs);
}

.nav-arrow:hover {
  color: var(--tp-text-inverse);
  background: rgba(255,255,255,0.1);
}

.nav-left {
  left: 12px;
}

.nav-right {
  right: 12px;
}

.viewer-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}

.viewer-img {
  max-width: 95%;
  max-height: 95%;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
}

.zoom-info {
  font-variant-numeric: tabular-nums;
}
</style>
