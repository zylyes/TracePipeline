<template>
  <Transition name="splash-fade">
    <div v-if="visible" class="splash-screen">
      <div class="splash-content">
        <!-- Logo 区域 -->
        <div class="splash-logo">
          <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" width="80" height="80">
            <circle cx="32" cy="32" r="30" fill="#1E2935" stroke="#B85C38" stroke-width="3"/>
            <circle cx="32" cy="32" r="24" fill="none" stroke="#B85C38" stroke-width="1" opacity="0.3"/>
            <g stroke="#B85C38" stroke-linecap="round">
              <line x1="32" y1="4"  x2="32" y2="10" stroke-width="2.5"/>
              <line x1="32" y1="54" x2="32" y2="60" stroke-width="2.5"/>
              <line x1="4"  y1="32" x2="10" y2="32" stroke-width="2.5"/>
              <line x1="54" y1="32" x2="60" y2="32" stroke-width="2.5"/>
              <line x1="11.7" y1="11.7" x2="16" y2="16" stroke-width="2"/>
              <line x1="48" y1="48" x2="52.3" y2="52.3" stroke-width="2"/>
              <line x1="11.7" y1="52.3" x2="16" y2="48" stroke-width="2"/>
              <line x1="48" y1="16" x2="52.3" y2="11.7" stroke-width="2"/>
              <line x1="22.3" y1="6.5" x2="23.8" y2="10.5" stroke-width="1.2"/>
              <line x1="40.2" y1="6.5" x2="38.7" y2="10.5" stroke-width="1.2"/>
              <line x1="6.5" y1="22.3" x2="10.5" y2="23.8" stroke-width="1.2"/>
              <line x1="6.5" y1="40.2" x2="10.5" y2="38.7" stroke-width="1.2"/>
              <line x1="22.3" y1="57.5" x2="23.8" y2="53.5" stroke-width="1.2"/>
              <line x1="40.2" y1="57.5" x2="38.7" y2="53.5" stroke-width="1.2"/>
              <line x1="57.5" y1="22.3" x2="53.5" y2="23.8" stroke-width="1.2"/>
              <line x1="57.5" y1="40.2" x2="53.5" y2="38.7" stroke-width="1.2"/>
            </g>
            <text x="32" y="16" text-anchor="middle" fill="#B85C38" font-size="10" font-weight="bold" font-family="Times New Roman, serif">N</text>
            <polygon points="32,6 35,30 32,25 29,30" fill="#B85C38"/>
            <polygon points="32,58 35,34 32,38 29,34" fill="#7f8c8d" opacity="0.8"/>
            <circle cx="32" cy="32" r="3" fill="#B85C38"/>
            <circle cx="32" cy="32" r="1.5" fill="#1E2935"/>
            <line x1="16" y1="48" x2="48" y2="16" stroke="#B85C38" stroke-width="1.5" opacity="0.8" stroke-dasharray="4,2"/>
            <circle cx="16" cy="48" r="1.5" fill="#B85C38" opacity="0.8"/>
            <circle cx="48" cy="16" r="1.5" fill="#B85C38" opacity="0.8"/>
          </svg>
        </div>

        <!-- 应用名称 -->
        <h1 class="splash-title">TracePipeline</h1>
        <p class="splash-subtitle">地质轨迹数据处理与分析平台</p>

        <!-- 进度条区域 -->
        <div class="progress-container">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progress + '%' }"></div>
          </div>
          <div class="progress-info">
            <span class="progress-text">{{ currentStep }}</span>
            <span class="progress-percent">{{ Math.round(progress) }}%</span>
          </div>
        </div>
      </div>

      <!-- 底部版本信息 -->
      <div class="splash-footer">
        <span>v{{ appVersion }}</span>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const appVersion = __APP_VERSION__

const emit = defineEmits<{
  (e: 'complete'): void
}>()

const visible = ref(true)
const progress = ref(0)
const currentStep = ref('正在初始化...')

const steps = [
  { text: '正在初始化...', duration: 300, progress: 15 },
  { text: '加载配置...', duration: 400, progress: 35 },
  { text: '连接后端服务...', duration: 500, progress: 60 },
  { text: '准备就绪...', duration: 300, progress: 100 },
]

async function animateProgress() {
  for (const step of steps) {
    currentStep.value = step.text
    
    // 平滑过渡到目标进度
    const startProgress = progress.value
    const targetProgress = step.progress
    const steps_count = 20
    const step_delay = step.duration / steps_count
    const progress_step = (targetProgress - startProgress) / steps_count
    
    for (let i = 0; i < steps_count; i++) {
      await new Promise(resolve => setTimeout(resolve, step_delay))
      progress.value = Math.min(startProgress + progress_step * (i + 1), targetProgress)
    }
    
    progress.value = targetProgress
  }
  
  // 完成后短暂停留，然后隐藏
  await new Promise(resolve => setTimeout(resolve, 400))
  visible.value = false
  emit('complete')
}

onMounted(() => {
  animateProgress()
})
</script>

<style scoped lang="scss">
.splash-screen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: linear-gradient(145deg, #1A2332 0%, #0f1620 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.splash-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
}

.splash-logo {
  margin-bottom: 24px;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.9;
  }
}

.splash-title {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 8px 0;
  font-family: var(--tp-font-stack);
  letter-spacing: 2px;
}

.splash-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 48px 0;
  letter-spacing: 1px;
}

.progress-container {
  width: 320px;
}

.progress-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #B85C38 0%, #d4785a 100%);
  border-radius: 2px;
  transition: width 0.15s ease-out;
  position: relative;
  
  &::after {
    content: '';
    position: absolute;
    right: 0;
    top: 0;
    width: 30px;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3));
  }
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.progress-percent {
  font-size: 13px;
  color: #B85C38;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.splash-footer {
  position: absolute;
  bottom: 32px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

/* 淡出动画 */
.splash-fade-leave-active {
  transition: opacity 0.5s ease-out;
}

.splash-fade-leave-to {
  opacity: 0;
}
</style>
