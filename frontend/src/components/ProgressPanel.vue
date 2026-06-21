<template>
  <div class="progress-panel tp-card tp-neon-edge" :class="{ 'is-running': running, 'is-complete': isComplete }">
    <div class="progress-header">
      <div class="progress-header-left">
        <div class="progress-header-icon">
          <el-icon :size="14"><VideoPlay /></el-icon>
        </div>
        <h3>进度控制</h3>
      </div>
    </div>
    
    <div class="control-bar">
      <el-button
        :icon="VideoPlay"
        :loading="running"
        :disabled="running"
        @click="emit('run')"
        size="default"
        class="run-btn"
      >
        {{ running ? '运行中...' : '一键运行' }}
      </el-button>
      <div class="parallel-control">
        <span class="parallel-label">并行进程</span>
        <div class="slider-input-combo">
          <el-slider v-model="parallel" :min="1" :max="maxParallel" />
          <el-input-number v-model="parallel" :min="1" :max="maxParallel" :controls="false" size="small" style="width: 60px; flex-shrink: 0;" />
        </div>
        <span class="parallel-limit tp-data">上限 {{ maxParallel }}</span>
      </div>
    </div>

    <!-- 步骤指示器 -->
    <div class="steps-indicator">
      <div 
        v-for="(step, idx) in steps" 
        :key="idx"
        class="step-item"
        :class="{
          'is-active': currentStepIndex === idx && running,
          'is-complete': currentStepIndex > idx || (isComplete && idx === steps.length - 1),
          'is-pending': currentStepIndex < idx || (!running && !isComplete && currentStepIndex === 0)
        }"
      >
        <div class="step-card">
          <div class="step-icon">
            <el-icon v-if="currentStepIndex > idx || (isComplete && idx === steps.length - 1)"><Check /></el-icon>
            <span v-else>{{ idx + 1 }}</span>
          </div>
          <div class="step-content">
            <div class="step-title">{{ step.title }}</div>
            <div class="step-desc">{{ getStepDesc(idx) }}</div>
          </div>
          <div class="scan-line" v-if="currentStepIndex === idx && running"></div>
        </div>
        <div class="step-connector" v-if="idx < steps.length - 1"></div>
      </div>
    </div>

    <div class="progress-area">
      <div class="progress-meta">
        <span class="progress-chip">任务 {{ progress.current || 0 }} / {{ progress.total || 0 }}</span>
        <span class="progress-chip" :class="{ active: running }">{{ running ? '流水线运行中' : '等待任务' }}</span>
      </div>
      <el-progress
        :percentage="percentage"
        :stroke-width="8"
        :status="progressStatus"
        :color="progressColor"
        class="modern-progress"
      />
      <div class="current-file">
        <span v-if="isComplete" class="complete-text">
          <el-icon :size="14"><CircleCheck /></el-icon>
          全部处理完成
        </span>
        <span v-else-if="!running && progress.current === 0 && progress.total === 0" class="idle-text">未处理</span>
        <span v-else-if="progress.filename" class="running-text">
          <el-icon class="tp-rotate" :size="12"><Loading /></el-icon>
          当前: {{ progress.filename }} — {{ progress.message }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { VideoPlay, CircleCheck, Loading, Check } from '@element-plus/icons-vue'

const props = defineProps<{
  running: boolean
  progress: {
    current: number
    total: number
    filename: string
    message: string
  }
}>()

const emit = defineEmits<{
  (e: 'run'): void
}>()

const maxParallel = Math.max(4, Math.min((navigator.hardwareConcurrency || 4) * 2, 32))
const parallel = defineModel<number>('parallel', { default: 0 })

// 步骤定义
const steps = [
  { title: '读取', id: 'read' },
  { title: '分析', id: 'analyze' },
  { title: '计算', id: 'compute' },
  { title: '导出', id: 'export' }
]

const isComplete = computed(() => !props.running && props.progress.total > 0 && props.progress.current >= props.progress.total)

// 简单的步骤推断逻辑，根据消息内容或进度百分比
const currentStepIndex = computed(() => {
  if (isComplete.value) return steps.length - 1
  if (!props.running && props.progress.current === 0) return 0
  
  const msg = props.progress.message.toLowerCase()
  if (msg.includes('export') || msg.includes('导出')) return 3
  if (msg.includes('calc') || msg.includes('计算') || msg.includes('compute')) return 2
  if (msg.includes('analy') || msg.includes('分析')) return 1
  
  // 如果消息推断不出来，按进度百分比估算
  const pct = targetPercentage.value
  if (pct > 90) return 3
  if (pct > 50) return 2
  if (pct > 10) return 1
  return 0
})

function getStepDesc(idx: number) {
  if (currentStepIndex.value > idx || (isComplete.value && idx === steps.length - 1)) return '已完成'
  if (currentStepIndex.value === idx && props.running) return '处理中...'
  return '等待中'
}

// ── 平滑进度插值 ──────────────────────────────────────────────
const REAL_TO_DISPLAY_SPEED = 0.12
const CREEP_SPEED = 0.015
const CREEP_GAP = 0.8

const targetPercentage = computed(() => {
  if (!props.progress.total) return 0
  return (props.progress.current / props.progress.total) * 100
})

const displayPercentage = ref(0)
let rafId: number | null = null

function stopAnimation() {
  if (rafId !== null) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
}

function tickAnimation() {
  const target = targetPercentage.value
  const current = displayPercentage.value

  if (current < target) {
    displayPercentage.value = current + (target - current) * REAL_TO_DISPLAY_SPEED
    if (Math.abs(displayPercentage.value - target) < 0.05) {
      displayPercentage.value = target
    }
  } else if (props.running && target < 100) {
    const nextStep = target + (100 / props.progress.total)
    const creepCeiling = nextStep - CREEP_GAP
    if (current < creepCeiling) {
      displayPercentage.value = Math.min(current + CREEP_SPEED, creepCeiling)
    }
  }

  if (props.running || displayPercentage.value < targetPercentage.value) {
    rafId = requestAnimationFrame(tickAnimation)
  } else {
    rafId = null
  }
}

watch(
  () => props.running,
  (running) => {
    if (running) {
      displayPercentage.value = 0
      if (rafId === null) {
        rafId = requestAnimationFrame(tickAnimation)
      }
    } else {
      displayPercentage.value = targetPercentage.value >= 100 ? 100 : targetPercentage.value
      stopAnimation()
    }
  },
  { immediate: true }
)

watch(targetPercentage, (val) => {
  if (val >= 100 && !props.running) {
    displayPercentage.value = 100
    stopAnimation()
  }
})

onUnmounted(() => {
  stopAnimation()
})

const percentage = computed(() => Math.round(displayPercentage.value))

const progressStatus = computed(() => {
  return undefined
})

const progressColor = computed(() => {
  if (props.running) return 'var(--tp-brand-accent)'
  if (isComplete.value) return 'var(--tp-success)'
  return 'var(--tp-brand-primary)'
})
</script>

<style scoped lang="scss">
.progress-panel {
  padding: var(--tp-space-4) var(--tp-space-5);
  margin-top: var(--tp-space-4);
}

.progress-panel.is-running {
  box-shadow: var(--tp-shadow-md), var(--tp-glow-cyan-md);
}

.progress-header {
  display: flex;
  align-items: center;
  margin-bottom: var(--tp-space-3);
  padding-bottom: var(--tp-space-3);
  border-bottom: 1px solid var(--tp-border-light);
}

.progress-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--tp-icon-md);
  height: var(--tp-icon-md);
  border-radius: var(--tp-radius-sm);
  background: var(--tp-info-bg);
  color: var(--tp-info);
}

.progress-panel h3 {
  font-family: var(--tp-font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0;
}

.control-bar {
  display: flex;
  align-items: center;
  gap: var(--tp-space-4);
  margin-bottom: var(--tp-space-4);
  flex-wrap: wrap;
}

.run-btn {
  font-family: var(--tp-font-heading);
  font-weight: 700;
  font-size: 14px;
  padding: 8px 22px;
  border-radius: var(--tp-radius-sm);
  letter-spacing: 0;
  background: linear-gradient(135deg, var(--tp-brand-accent), var(--tp-brand-accent-dark));
  border-color: var(--tp-brand-accent);
  color: var(--tp-text-inverse);
  box-shadow: var(--tp-brand-accent-shadow-sm);
  transition: all var(--tp-duration-normal) var(--tp-easing);
  position: relative;
  overflow: hidden;
}

.run-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.15) 50%, transparent 100%);
  transform: translateX(-100%);
  transition: transform 0.5s var(--tp-easing-expo);
}

.run-btn:hover::after {
  transform: translateX(100%);
}

.run-btn:hover,
.run-btn:focus {
  background: var(--tp-brand-accent-dark);
  border-color: var(--tp-brand-accent-dark);
  box-shadow: var(--tp-brand-accent-shadow-md);
  transform: translateY(-1px);
}

.run-btn:active {
  transform: translateY(0) scale(0.97);
  box-shadow: var(--tp-brand-accent-glow);
}

.parallel-control {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: var(--tp-text-secondary);
  background: rgba(238, 240, 244, 0.74);
  padding: 6px 12px;
  border-radius: var(--tp-radius-sm);
  border: 1px solid var(--tp-border-light);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.65);
}

.parallel-label {
  font-family: var(--tp-font-heading);
  font-weight: 500;
  font-size: 14px;
}

.parallel-limit {
  font-size: 13px;
  color: var(--tp-text-secondary);
}

/* 步骤指示器样式 */
.steps-indicator {
  display: flex;
  align-items: stretch;
  margin-bottom: var(--tp-space-5);
  padding: 4px;
}

.step-item {
  display: flex;
  align-items: center;
  flex: 1;
}

.step-item:last-child {
  flex: 0;
}

.step-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: var(--tp-radius-md);
  background: var(--tp-surface-1);
  border: 1px solid var(--tp-border-light);
  position: relative;
  overflow: hidden;
  transition: all var(--tp-duration-normal);
  min-width: 120px;
}

.step-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  transition: all var(--tp-duration-normal);
}

.step-content {
  display: flex;
  flex-direction: column;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--tp-text-primary);
}

.step-desc {
  font-size: 12px;
  color: var(--tp-text-tertiary);
}

.step-connector {
  flex: 1;
  height: 2px;
  background: var(--tp-border-light);
  margin: 0 12px;
  transition: background var(--tp-duration-normal);
}

/* 步骤状态样式 */
.step-item.is-pending .step-card {
  background: var(--tp-bg-sunken);
  opacity: 0.7;
}

.step-item.is-pending .step-icon {
  background: var(--tp-border-medium);
  color: var(--tp-text-inverse);
}

.step-item.is-active .step-card {
  background: rgba(2, 132, 199, 0.05);
  border-color: var(--tp-brand-accent);
  box-shadow: 0 0 12px var(--tp-glow-primary);
}

.step-item.is-active .step-icon {
  background: var(--tp-brand-accent);
  color: var(--tp-text-inverse);
  box-shadow: 0 0 8px var(--tp-glow-primary);
}

.step-item.is-active .step-title {
  color: var(--tp-brand-accent);
}

.step-item.is-complete .step-card {
  background: rgba(16, 185, 129, 0.05);
  border-left: 3px solid var(--tp-success);
  border-color: var(--tp-success-border);
}

.step-item.is-complete .step-icon {
  background: var(--tp-success);
  color: var(--tp-text-inverse);
}

.step-item.is-complete .step-connector {
  background: var(--tp-success);
}

/* 扫描线动画 */
.scan-line {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    transparent,
    var(--tp-glow-primary),
    transparent
  );
  height: 100%;
  animation: tp-scan-line 2s linear infinite;
  pointer-events: none;
  opacity: 0.5;
}

.current-file {
  margin-top: var(--tp-space-2);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 22px;
}

.complete-text {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--tp-success);
  font-weight: 500;
}

.idle-text {
  color: var(--tp-text-muted);
}

.running-text {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--tp-brand-accent);
  padding: 4px 10px;
  border-radius: var(--tp-radius-full);
  background: rgba(2, 132, 199, 0.08);
  box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.14);
}

.progress-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--tp-space-2);
  margin-bottom: var(--tp-space-2);
}

.progress-chip {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 10px;
  border-radius: var(--tp-radius-full);
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(125, 211, 252, 0.16);
  color: var(--tp-text-tertiary);
  font-family: var(--tp-font-data);
  font-size: 12px;
}

.progress-chip.active {
  color: var(--tp-brand-accent);
  background: rgba(2, 132, 199, 0.10);
  box-shadow: var(--tp-glow-cyan-sm);
}

.slider-input-combo {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 200px;
  margin: 0 8px;
}

.slider-input-combo .el-slider {
  flex: 1;
}

:deep(.el-slider__button) {
  width: 14px;
  height: 14px;
  transition: transform var(--tp-duration-normal) var(--tp-easing-expo);
}

:deep(.el-slider__button:hover) {
  transform: scale(1.35);
}

/* Element Plus 进度条样式覆盖 */
:deep(.modern-progress .el-progress-bar__outer) {
  border-radius: var(--tp-radius-full);
  background: rgba(26, 54, 93, 0.10);
  box-shadow: inset 0 1px 4px rgba(26, 54, 93, 0.14);
  overflow: hidden;
}

:deep(.modern-progress .el-progress-bar__inner) {
  position: relative;
  border-radius: var(--tp-radius-full);
  transition: width 0.15s linear;
  background: linear-gradient(90deg, var(--tp-brand-accent-dark), var(--tp-brand-accent-light), var(--tp-geo-emerald)) !important;
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.42);
}

.is-running :deep(.modern-progress .el-progress-bar__inner::after) {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.42), transparent);
  animation: progressEnergySweep 1.3s linear infinite;
}

@keyframes progressEnergySweep {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(120%); }
}
</style>
