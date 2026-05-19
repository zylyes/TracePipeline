<template>
  <Transition name="splash-fade" @after-leave="onAfterLeave">
    <div v-if="visible" class="splash-screen">
      <div class="splash-content">
        <!-- Logo 区域 -->
        <div class="splash-logo">
          <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" width="80" height="80">
            <defs>
              <linearGradient id="logo-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="var(--tp-brand-accent-light)" />
                <stop offset="100%" stop-color="var(--tp-brand-accent)" />
              </linearGradient>
            </defs>
            <circle class="draw-circle" cx="32" cy="32" r="30" fill="#1E293B" stroke="url(#logo-gradient)" stroke-width="3"/>
            <circle cx="32" cy="32" r="24" fill="none" stroke="url(#logo-gradient)" stroke-width="1" opacity="0.3"/>
            <g class="draw-lines" stroke="url(#logo-gradient)" stroke-linecap="round">
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
            <text class="draw-text" x="32" y="16" text-anchor="middle" fill="url(#logo-gradient)" font-size="10" font-weight="bold" font-family="Times New Roman, serif">N</text>
            <polygon class="draw-poly-1" points="32,6 35,30 32,25 29,30" fill="url(#logo-gradient)"/>
            <polygon class="draw-poly-2" points="32,58 35,34 32,38 29,34" fill="#94A3B8" opacity="0.8"/>
            <circle cx="32" cy="32" r="3" fill="url(#logo-gradient)"/>
            <circle cx="32" cy="32" r="1.5" fill="#1E293B"/>
            <line class="draw-path" x1="16" y1="48" x2="48" y2="16" stroke="url(#logo-gradient)" stroke-width="1.5" opacity="0.8" stroke-dasharray="4,2"/>
            <circle class="draw-point-1" cx="16" cy="48" r="1.5" fill="url(#logo-gradient)" opacity="0.8"/>
            <circle class="draw-point-2" cx="48" cy="16" r="1.5" fill="url(#logo-gradient)" opacity="0.8"/>
          </svg>
        </div>

        <!-- 应用名称 -->
        <h1 class="splash-title">TracePipeline</h1>
        <p class="splash-subtitle">地质轨迹数据处理与分析平台</p>

        <!-- 进度条区域 -->
        <div class="progress-container">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :class="{ 'progress-error': hasErrors }"
              :style="{ width: progress + '%' }"
            ></div>
            <div class="progress-sweep" :style="{ left: progress > 5 ? (progress - 5) + '%' : '-10%' }"></div>
          </div>
          <div class="progress-info">
            <span class="progress-text">{{ currentStep }}</span>
            <span class="progress-percent tp-data">{{ Math.round(progress) }}%</span>
          </div>
        </div>

        <!-- 错误提示 -->
        <Transition name="error-slide">
          <div v-if="hasErrors" class="error-hint">
            <el-icon><Warning /></el-icon>
            <span>部分初始化失败，将在页面中自动重试</span>
          </div>
        </Transition>
      </div>

      <!-- 底部版本信息 -->
      <div class="splash-footer">
        <span class="tp-data">v{{ appVersion }}</span>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Warning } from '@element-plus/icons-vue'

const appVersion = __APP_VERSION__

export interface BootStep {
  label: string
  task: () => Promise<any>
  targetProgress: number
}

const props = defineProps<{
  steps: BootStep[]
  minDuration?: number
}>()

const emit = defineEmits<{
  (e: 'complete', payload: { errors: Array<{ step: string; error: string }> }): void
}>()

const visible = ref(true)
const progress = ref(0)
const currentStep = ref('正在初始化...')
const errors = ref<Array<{ step: string; error: string }>>([])

const hasErrors = computed(() => errors.value.length > 0)

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function runBootSequence() {
  const startTime = Date.now()
  errors.value = []

  for (const step of props.steps) {
    currentStep.value = step.label

    try {
      await step.task()
    } catch (err: any) {
      const message = err?.message || String(err) || '未知错误'
      errors.value.push({ step: step.label, error: message })
      console.warn(`[SplashScreen] 步骤失败: ${step.label} — ${message}`)
    }

    // 平滑推进到目标进度
    const startProgress = progress.value
    const targetProgress = step.targetProgress
    const diff = targetProgress - startProgress
    if (diff > 0) {
      const frames = 12
      const frameDelay = 80
      for (let i = 1; i <= frames; i++) {
        await delay(frameDelay)
        progress.value = Math.min(startProgress + (diff * i) / frames, targetProgress)
      }
    }
    progress.value = targetProgress
  }

  // 最终步骤
  currentStep.value = '准备就绪'
  progress.value = 100

  // 最小展示时间控制
  const elapsed = Date.now() - startTime
  const minDur = props.minDuration ?? 1500
  if (elapsed < minDur) {
    await delay(minDur - elapsed)
  }

  // 淡出
  visible.value = false
}

function onAfterLeave() {
  emit('complete', { errors: errors.value })
}

onMounted(() => {
  runBootSequence()
})
</script>

<style scoped lang="scss">
.splash-screen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: linear-gradient(145deg, var(--tp-brand-primary) 0%, var(--el-color-primary-dark-2) 100%);
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
  animation: logoFloat 4s ease-in-out infinite, logoEntry 1.2s var(--tp-easing-smooth) forwards;
}

/* ── Logo 绘制动画 ── */
.draw-circle {
  stroke-dasharray: 190;
  stroke-dashoffset: 190;
  animation: drawStroke 1.5s var(--tp-easing-smooth) forwards;
}

.draw-lines {
  stroke-dasharray: 20;
  stroke-dashoffset: 20;
  animation: drawStroke 1s 0.3s var(--tp-easing-smooth) forwards;
}

.draw-path {
  stroke-dasharray: 50;
  stroke-dashoffset: 50;
  animation: drawStroke 1.2s 0.5s var(--tp-easing-smooth) forwards;
}

.draw-poly-1, .draw-poly-2 {
  opacity: 0;
  animation: fadeIn 0.8s 1s forwards;
}

.draw-text {
  opacity: 0;
  animation: fadeIn 0.8s 0.8s forwards;
}

.draw-point-1, .draw-point-2 {
  opacity: 0;
  transform-origin: center;
  animation: popIn 0.5s 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}

@keyframes drawStroke {
  to { stroke-dashoffset: 0; }
}

@keyframes fadeIn {
  to { opacity: 1; }
}

@keyframes popIn {
  from { opacity: 0; transform: scale(0); }
  to { opacity: 0.8; transform: scale(1); }
}

@keyframes logoEntry {
  from { opacity: 0; transform: scale(0.85) translateY(10px); filter: drop-shadow(0 0 0 transparent); }
  to { opacity: 1; transform: scale(1) translateY(0); filter: drop-shadow(0 4px 12px var(--tp-brand-accent-glow)); }
}

@keyframes logoFloat {
  0%, 100% {
    transform: translateY(0);
    filter: drop-shadow(0 4px 12px var(--tp-brand-accent-glow));
  }
  50% {
    transform: translateY(-8px);
    filter: drop-shadow(0 12px 24px var(--tp-brand-accent-shadow-md));
  }
}

.splash-title {
  font-family: var(--tp-font-heading);
  font-size: var(--tp-font-size-hero);
  font-weight: 700;
  color: var(--tp-text-inverse);
  margin: 0 0 8px 0;
  letter-spacing: 2px;
  animation: titleSlideIn 0.6s 0.2s var(--tp-easing-expo) both;
}

@keyframes titleSlideIn {
  from { opacity: 0; transform: translateY(12px); letter-spacing: 6px; }
  to { opacity: 1; transform: translateY(0); letter-spacing: 2px; }
}

.splash-subtitle {
  font-family: var(--tp-font-body);
  font-size: 14px;
  color: rgba(255, 255, 255, 0.55);
  margin: 0 0 48px 0;
  letter-spacing: 1px;
  animation: subtitleFade 0.5s 0.4s var(--tp-easing-expo) both;
}

@keyframes subtitleFade {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.progress-container {
  width: 340px;
}

.progress-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 14px;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--tp-brand-accent) 0%, var(--tp-brand-accent-light) 50%, var(--tp-brand-accent) 100%);
  background-size: 200% 100%;
  border-radius: 2px;
  transition: width var(--tp-duration-fast) var(--tp-easing);
  position: relative;
  animation: progressShimmer 2s linear infinite;
  box-shadow: 0 0 8px var(--tp-brand-accent-glow), 0 0 20px rgba(201, 107, 79, 0.08);

  &.progress-error {
    background: linear-gradient(90deg, var(--tp-danger) 0%, var(--tp-warning) 100%);
    animation: none;
    box-shadow: 0 0 8px rgba(192, 57, 43, 0.3);
  }
}

@keyframes progressShimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.progress-sweep {
  position: absolute;
  top: 0;
  width: 40px;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.25), transparent);
  border-radius: 2px;
  animation: sweep 1.5s ease-in-out infinite;
  transition: left 0.2s ease-out;
}

@keyframes sweep {
  0% { transform: translateX(-30px); opacity: 0; }
  50% { opacity: 1; }
  100% { transform: translateX(30px); opacity: 0; }
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-text {
  font-family: var(--tp-font-body);
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.progress-percent {
  font-size: 13px;
  color: var(--tp-brand-accent);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.error-hint {
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: var(--tp-space-2);
  padding: 10px 16px;
  background: var(--tp-warning-bg);
  border: 1px solid rgba(230, 162, 60, 0.25);
  border-radius: var(--tp-radius-md);
  font-family: var(--tp-font-body);
  font-size: 12px;
  color: var(--tp-warning);

  .el-icon {
    font-size: 14px;
  }
}

.splash-footer {
  position: absolute;
  bottom: 32px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
}

/* 淡出动画 */
.splash-fade-leave-active {
  transition: opacity 0.5s var(--tp-easing-expo);
}

.splash-fade-leave-to {
  opacity: 0;
}

/* 错误提示滑入 */
.error-slide-enter-active,
.error-slide-leave-active {
  transition: all 0.3s var(--tp-easing-expo);
}

.error-slide-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.error-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
