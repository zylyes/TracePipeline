<template>
  <div class="style-preview">
    <h3>预览</h3>
    <div class="preview-grid">
      <div class="preview-box">
        <div class="preview-label">原始迹线图</div>
        <div class="preview-img-wrapper" v-loading="loading">
          <img v-if="rawUrl" :src="rawUrl" class="preview-img" />
          <el-empty v-else description="修改样式后自动生成预览" />
        </div>
      </div>
      <div class="preview-box">
        <div class="preview-label">走向玫瑰图</div>
        <div class="preview-img-wrapper" v-loading="loading">
          <img v-if="roseUrl" :src="roseUrl" class="preview-img" />
          <el-empty v-else description="修改样式后自动生成预览" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { api } from '@/api/pywebview'
import { loadImageBase64 } from '@/utils/image'

const props = defineProps<{
  styleConfig: any
}>()

const rawUrl = ref('')
const roseUrl = ref('')
const loading = ref(false)

let debounceTimer: number | null = null

async function doGenerate() {
  loading.value = true
  try {
    const res = await api.generate_preview(props.styleConfig)
    if (res.status === 'ready') {
      rawUrl.value = await loadImageBase64(res.paths.raw)
      roseUrl.value = await loadImageBase64(res.paths.rose)
    } else {
      rawUrl.value = ''
      roseUrl.value = ''
    }
  } catch (e) {
    rawUrl.value = ''
    roseUrl.value = ''
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
</script>

<style scoped lang="scss">
.style-preview {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  margin-top: 16px;
}
.preview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 12px;
}
.preview-box {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
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
  aspect-ratio: 4/3;
  background: #fff;
}
.preview-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
