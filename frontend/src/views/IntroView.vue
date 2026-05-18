<template>
  <div class="intro-view">
    <!-- Hero 区域 -->
    <div class="hero-section">
      <div class="hero-texture"></div>
      <div class="hero-content">
        <div class="hero-logo-wrap">
          <GeoIcon class="hero-logo" :size="48" color="#C96B4F" />
        </div>
        <h1 class="hero-title">TracePipeline</h1>
        <p class="hero-subtitle">节理迹线数据处理与可视化系统</p>
        <p class="hero-desc">
          面向地质工程的专业数据处理平台，支持迹线自动识别、走向玫瑰图生成、
          节点拓扑分析及多露头对比统计。
        </p>
        <div class="hero-badges">
          <span class="badge">Python</span>
          <span class="badge">Vue 3</span>
          <span class="badge">PyWebView</span>
        </div>
      </div>
    </div>

    <!-- 功能模块 -->
    <div class="modules-section">
      <div class="modules-row">
        <div v-for="mod in modules" :key="mod.path" class="module-card" @click="$router.push(mod.path)">
          <div class="module-accent" :style="{ background: mod.color }" />
          <div class="module-body">
            <component :is="mod.icon" :size="32" :color="mod.color" class="module-icon" />
            <h3 class="module-name">{{ mod.name }}</h3>
            <p class="module-desc">{{ mod.desc }}</p>
          </div>
          <div class="module-arrow">
            <ArrowRight :size="14" />
          </div>
        </div>
      </div>
    </div>

    <!-- 快速开始 -->
    <div class="quickstart-section tp-card">
      <h2 class="section-title">快速开始</h2>
      <div class="steps">
        <div v-for="(step, i) in steps" :key="i" class="step-group">
          <div class="step-item">
            <div class="step-number">{{ i + 1 }}</div>
            <div class="step-content">
              <h4>{{ step.title }}</h4>
              <p>{{ step.desc }}</p>
            </div>
          </div>
          <div v-if="i < steps.length - 1" class="step-connector">
            <div class="step-line"></div>
            <ArrowRight :size="14" class="step-arrow-icon" />
          </div>
        </div>
      </div>
    </div>

    <!-- 底部 -->
    <footer class="intro-footer">
      <p>TracePipeline v{{ appVersion }} · 地质工程数据处理平台</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ArrowRight } from '@element-plus/icons-vue'

const appVersion = __APP_VERSION__
defineOptions({ name: 'Intro' })

import GeoIcon from '@/components/GeoIcon.vue'
import HomeIcon from '@/components/icons/HomeIcon.vue'
import ProcessIcon from '@/components/icons/ProcessIcon.vue'
import StatsIcon from '@/components/icons/StatsIcon.vue'
import CompareIcon from '@/components/icons/CompareIcon.vue'
import DataIcon from '@/components/icons/DataIcon.vue'
import ConfigIcon from '@/components/icons/ConfigIcon.vue'

const modules = [
  {
    name: '处理',
    desc: '批量处理露头数据，自动计算迹线参数与节点识别',
    path: '/processing',
    icon: ProcessIcon,
    color: '#C96B4F',
  },
  {
    name: '统计',
    desc: '密度指标、迹长直方图、裂隙类型饼图与结果浏览',
    path: '/statistics',
    icon: StatsIcon,
    color: '#2E7D5A',
  },
  {
    name: '对比',
    desc: '多露头参数对比表格与柱状图，直观比较差异',
    path: '/comparison',
    icon: CompareIcon,
    color: '#4A5568',
  },
  {
    name: '数据',
    desc: '裂隙情况、端点坐标、走向与迹长等多维度浏览',
    path: '/data',
    icon: DataIcon,
    color: '#7B1FA2',
  },
  {
    name: '配置',
    desc: '全局参数、绘图样式与开发者模式灵活调整',
    path: '/config',
    icon: ConfigIcon,
    color: '#B89A6A',
  },
]

const steps = [
  { title: '选择露头文件', desc: '扫描并选择需处理的露头 Excel 文件，配置处理参数。' },
  { title: '运行处理流程', desc: '启动流水线，自动完成迹线计算、绘图与节点识别。' },
  { title: '查看分析结果', desc: '在统计、对比或数据页面查看结果，支持图表交互。' },
  { title: '导出报告', desc: '生成 Word/PDF 格式分析报告，便于存档与汇报。' },
]

</script>

<style scoped lang="scss">
.intro-view {
  padding: var(--tp-space-5) var(--tp-space-6);
  height: 100%;
  overflow-y: auto;
  background: var(--tp-bg-base);
}

/* ── Hero ───────────────────────────────────────────── */
.hero-section {
  position: relative;
  background: linear-gradient(145deg, var(--tp-brand-primary) 0%, #2c3e50 60%, var(--tp-brand-primary) 100%);
  border-radius: var(--tp-radius-xl);
  padding: 36px 40px;
  text-align: center;
  color: #fff;
  margin-bottom: var(--tp-space-5);
  overflow: visible;
}

.hero-texture {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 20% 30%, var(--tp-brand-accent-bg) 0%, transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(74, 158, 122, 0.06) 0%, transparent 50%);
  pointer-events: none;
  animation: heroTextureShift 8s ease-in-out infinite alternate;
}

@keyframes heroTextureShift {
  0% { background-position: 0% 0%, 0% 0%; opacity: 1; }
  100% { background-position: 5% 3%, -3% -5%; opacity: 0.7; }
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 580px;
  margin: 0 auto;
}

.hero-logo-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: var(--tp-radius-xl);
  background: var(--tp-brand-accent-bg);
  border: 1px solid var(--tp-brand-accent-border);
  margin-bottom: 16px;
  animation: logoWrapEntry 0.6s var(--tp-easing-expo) both, logoWrapFloat 4s 0.6s ease-in-out infinite;
}

@keyframes logoWrapEntry {
  from { opacity: 0; transform: scale(0.7) rotate(-10deg); }
  to { opacity: 1; transform: scale(1) rotate(0deg); }
}

@keyframes logoWrapFloat {
  0%, 100% { transform: translateY(0); box-shadow: 0 4px 16px var(--tp-brand-accent-glow); }
  50% { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(201, 107, 79, 0.2); }
}

.hero-logo {
  display: block;
}

.hero-title {
  font-family: var(--tp-font-heading);
  font-size: var(--tp-font-size-hero);
  font-weight: 700;
  margin: 0 0 8px;
  color: #fff;
  animation: heroTitleIn 0.7s 0.15s var(--tp-easing-expo) both;
}

@keyframes heroTitleIn {
  from { opacity: 0; transform: translateY(16px); letter-spacing: 4px; }
  to { opacity: 1; transform: translateY(0); letter-spacing: normal; }
}

.hero-subtitle {
  font-family: var(--tp-font-body);
  font-size: 15px;
  font-weight: 400;
  opacity: 0.88;
  margin: 0 0 12px;
  color: rgba(255, 255, 255, 0.85);
  animation: heroSubIn 0.5s 0.35s var(--tp-easing-expo) both;
}

@keyframes heroSubIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 0.88; transform: translateY(0); }
}

.hero-desc {
  font-family: var(--tp-font-body);
  font-size: 14px;
  line-height: var(--tp-leading-relaxed);
  opacity: 0.65;
  margin: 0 auto;
  max-width: 480px;
  color: rgba(255, 255, 255, 0.7);
  animation: heroDescIn 0.5s 0.5s var(--tp-easing-expo) both;
}

@keyframes heroDescIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 0.65; transform: translateY(0); }
}

.hero-badges {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 18px;
}

.badge {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.75);
  padding: 4px 14px;
  border-radius: var(--tp-radius-full);
  font-size: 11px;
  font-weight: 500;
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-family: var(--tp-font-data);
}

/* ── 功能模块 ──────────────────────────── */
.modules-section {
  margin-bottom: var(--tp-space-5);
}

.modules-row {
  display: flex;
  gap: 14px;
}

.module-card {
  flex: 1;
  min-width: 0;
  background: var(--tp-bg-elevated);
  border: 1px solid var(--tp-border-light);
  border-radius: var(--tp-radius-lg);
  cursor: pointer;
  transition: all var(--tp-duration-slow) var(--tp-easing-expo);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: var(--tp-shadow-sm);
}

.module-card:hover {
  transform: translateY(-4px) scale(1.015);
  box-shadow: var(--tp-shadow-lg), 0 0 0 1px var(--tp-brand-accent-border);
  border-color: var(--tp-brand-accent-border);
}

.module-accent {
  height: 3px;
  width: 100%;
  flex-shrink: 0;
  opacity: 0.85;
  transition: height var(--tp-duration-normal) var(--tp-easing-expo);
}

.module-card:hover .module-accent {
  height: 4px;
  opacity: 1;
}

.module-body {
  padding: 18px 14px 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  flex: 1;
}

.module-icon {
  margin-bottom: 10px;
  flex-shrink: 0;
  opacity: 0.9;
  transition: all var(--tp-duration-normal) var(--tp-easing-expo);
}

.module-card:hover .module-icon {
  transform: scale(1.1) translateY(-2px);
  opacity: 1;
}

.module-name {
  font-family: var(--tp-font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0 0 6px;
}

.module-desc {
  font-family: var(--tp-font-body);
  font-size: 13px;
  color: var(--tp-text-secondary);
  line-height: 1.55;
  margin: 0;
}

.module-arrow {
  position: absolute;
  bottom: 10px;
  right: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--tp-bg-base);
  color: var(--tp-text-muted);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: all var(--tp-duration-normal) var(--tp-easing-expo);
}

.module-card:hover .module-arrow {
  visibility: visible;
  opacity: 1;
  color: var(--tp-brand-accent);
  transform: translateX(3px);
}

/* ── 快速开始 ──────────────────────────────────────── */
.quickstart-section {
  padding: var(--tp-space-5) var(--tp-space-6);
  margin-bottom: var(--tp-space-5);
}

.section-title {
  font-family: var(--tp-font-heading);
  font-size: 17px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0 0 var(--tp-space-5);
  text-align: center;
}

.steps {
  display: flex;
  align-items: stretch;
  justify-content: center;
  gap: 0;
  flex-wrap: wrap;
}

.step-group {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 220px;
  max-width: 280px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
  background: var(--tp-bg-sunken);
  border-radius: var(--tp-radius-lg);
  padding: 16px;
  border: 1px solid var(--tp-border-light);
  transition: all var(--tp-duration-normal);
}

.step-item:hover {
  background: var(--tp-bg-hover);
  box-shadow: var(--tp-shadow-sm);
}

.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--tp-brand-accent);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-family: var(--tp-font-data);
  margin-top: 1px;
  box-shadow: var(--tp-brand-accent-shadow-sm);
}

.step-content {
  flex: 1 1 auto;
  min-width: 0;
}

.step-content h4 {
  font-family: var(--tp-font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--tp-text-primary);
  margin: 0 0 5px;
}

.step-content p {
  font-family: var(--tp-font-body);
  font-size: 13px;
  color: var(--tp-text-secondary);
  line-height: 1.55;
  margin: 0;
}

.step-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 40px;
  flex-shrink: 0;
  position: relative;
}

.step-line {
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, var(--tp-border) 0%, var(--tp-brand-accent-light) 50%, var(--tp-border) 100%);
  opacity: 0.5;
}

.step-arrow-icon {
  position: absolute;
  bottom: 50%;
  left: 50%;
  transform: translate(-50%, calc(50% + 0.5px));
  color: var(--tp-brand-accent);
  opacity: 0.5;
}

/* ── 底部 ──────────────────────────────────────────── */
.intro-footer {
  text-align: center;
  padding: var(--tp-space-3) 0;
  color: var(--tp-text-muted);
  font-size: 12px;
  font-family: var(--tp-font-body);
}

/* ── 响应式适配 ──────────────────────────────────────── */

@media (max-width: 1024px) {
  .modules-row {
    flex-wrap: wrap;
  }

  .module-card {
    flex: 1 1 calc(33.333% - 14px);
    min-width: 160px;
  }

  .step-group {
    min-width: 180px;
  }
}

@media (max-width: 768px) {
  .intro-view {
    padding: var(--tp-space-4) var(--tp-space-4);
  }

  .hero-section {
    padding: 24px 20px;
  }

  .hero-title {
    font-size: 26px;
  }

  .hero-subtitle {
    font-size: 14px;
  }

  .hero-desc {
    font-size: 13px;
  }

  .hero-logo-wrap {
    width: 56px;
    height: 56px;
    margin-bottom: 12px;
  }

  .modules-row {
    gap: 10px;
  }

  .module-card {
    flex: 1 1 calc(50% - 10px);
    min-width: 140px;
  }

  .module-body {
    padding: 14px 10px 10px;
  }

  .module-name {
    font-size: 14px;
  }

  .module-desc {
    font-size: 12px;
  }

  .quickstart-section {
    padding: var(--tp-space-4) var(--tp-space-4);
  }

  .steps {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .step-group {
    flex: none;
    min-width: 0;
    max-width: none;
    flex-direction: column;
  }

  .step-connector {
    width: auto;
    height: 28px;
    flex-direction: row;
    flex-shrink: 0;
  }

  .step-line {
    width: 1px;
    height: 100%;
  }

  .step-arrow-icon {
    position: absolute;
    right: 50%;
    top: 50%;
    transform: translate(calc(50% + 0.5px), -50%) rotate(90deg);
  }
}

@media (max-width: 480px) {
  .intro-view {
    padding: var(--tp-space-3) var(--tp-space-3);
  }

  .hero-section {
    padding: 18px 14px;
    border-radius: var(--tp-radius-lg);
  }

  .hero-title {
    font-size: 22px;
  }

  .hero-subtitle {
    font-size: 13px;
  }

  .hero-desc {
    font-size: 12px;
  }

  .hero-badges {
    gap: 6px;
    margin-top: 12px;
  }

  .badge {
    padding: 3px 10px;
    font-size: 10px;
  }

  .modules-row {
    flex-direction: column;
    gap: 8px;
  }

  .module-card {
    flex: none;
    min-width: 0;
  }

  .module-body {
    flex-direction: row;
    align-items: center;
    text-align: left;
    gap: 12px;
    padding: 12px 14px;
  }

  .module-icon {
    margin-bottom: 0;
    flex-shrink: 0;
  }

  .module-name {
    font-size: 14px;
    margin-bottom: 2px;
  }

  .module-desc {
    font-size: 12px;
  }

  .module-arrow {
    bottom: 50%;
    right: 10px;
    transform: translateY(50%);
  }

  .step-item {
    padding: 12px;
    gap: 10px;
  }

  .step-content h4 {
    font-size: 14px;
  }

  .step-content p {
    font-size: 12px;
  }

  .section-title {
    font-size: 15px;
  }
}
</style>
