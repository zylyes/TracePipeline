<template>
  <div class="intro-view">
    <!-- Hero 区域 -->
    <div class="hero-section">
      <div class="hero-content">
        <GeoIcon class="hero-logo" :size="44" color="#B85C38" />
        <h1 class="hero-title">TracePipeline</h1>
        <p class="hero-subtitle">节理迹线数据处理与可视化系统</p>
        <p class="hero-desc">
          面向地质工程的专业数据处理平台，支持迹线自动识别、走向玫瑰图生成、
          节点拓扑分析及多露头对比统计。
        </p>
      </div>
    </div>

    <!-- 功能模块 — 单行横向 -->
    <div class="modules-section">
      <div class="modules-row">
        <div v-for="mod in modules" :key="mod.path" class="module-card" @click="$router.push(mod.path)">
          <div class="module-accent" :style="{ background: mod.color }" />
          <div class="module-body">
            <component :is="mod.icon" :size="36" :color="mod.color" class="module-icon" />
            <h3 class="module-name">{{ mod.name }}</h3>
            <p class="module-desc">{{ mod.desc }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 快速开始 -->
    <div class="quickstart-section">
      <h2 class="section-title">快速开始</h2>
      <div class="steps">
        <div v-for="(step, i) in steps" :key="i" class="step-group">
          <div class="step-item">
            <span class="step-number">{{ i + 1 }}</span>
            <div class="step-content">
              <h4>{{ step.title }}</h4>
              <p>{{ step.desc }}</p>
            </div>
          </div>
          <span v-if="i < steps.length - 1" class="step-arrow"><ArrowRight :size="18" /></span>
        </div>
      </div>
    </div>

    <!-- 底部 -->
    <footer class="intro-footer">
      <p>TracePipeline v1.0.1 · 地质工程数据处理平台</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ArrowRight } from '@element-plus/icons-vue'
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
    color: '#B85C38',
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
    color: '#606266',
  },
]

const steps = [
  { title: '选择露头文件', desc: '扫描并选择需处理的露头 Excel 文件，配置处理参数。' },
  { title: '运行处理流程', desc: '启动流水线，自动完成迹线计算、绘图与节点识别。' },
  { title: '查看分析结果', desc: '在统计、对比或数据页面查看结果，支持图表交互。' },
]

</script>

<style scoped lang="scss">
.intro-view {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
  background: #f8f9fa;
}

/* ── Hero ───────────────────────────────────────────── */
.hero-section {
  background: linear-gradient(135deg, #1a2332 0%, #2c3e50 100%);
  border-radius: 10px;
  padding: 36px 32px;
  text-align: center;
  color: #fff;
  margin-bottom: 28px;
}

.hero-content {
  max-width: 560px;
  margin: 0 auto;
}

.hero-logo {
  margin-bottom: 12px;
  display: block;
  margin-left: auto;
  margin-right: auto;
}

.hero-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 6px;
  font-family: var(--tp-font-stack);
  letter-spacing: 1px;
}

.hero-subtitle {
  font-size: 16px;
  font-weight: 400;
  opacity: 0.88;
  margin: 0 0 12px;
  color: #e0e0e0;
}

.hero-desc {
  font-size: 13px;
  line-height: 1.7;
  opacity: 0.7;
  margin: 0;
  color: #c0c4cc;
}

/* ── 功能模块（单行横向） ──────────────────────────── */
.modules-section {
  margin-bottom: 28px;
}

.modules-row {
  display: flex;
  gap: 14px;
}

.module-card {
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid #dde1e6;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.25s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.module-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border-color: #c8cdd3;
}

.module-accent {
  height: 3px;
  width: 100%;
  flex-shrink: 0;
}

.module-body {
  padding: 16px 14px 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  flex: 1;
}

.module-icon {
  margin-bottom: 10px;
  flex-shrink: 0;
}

.module-name {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 6px;
  font-family: 'SimHei', 'Microsoft YaHei', var(--tp-font-stack);
}

.module-desc {
  font-size: 12px;
  color: #7f8c8d;
  line-height: 1.55;
  margin: 0;
}

/* ── 快速开始 ──────────────────────────────────────── */
.quickstart-section {
  background: #fff;
  border: 1px solid #dde1e6;
  border-radius: 10px;
  padding: 24px 32px;
  margin-bottom: 20px;
}

.section-title {
  font-size: 17px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 18px;
  text-align: center;
  font-family: 'SimHei', 'Microsoft YaHei', var(--tp-font-stack);
}

.steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.step-group {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
  min-width: 220px;
  max-width: 320px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
}

.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #B85C38;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-family: 'Times New Roman', serif;
}

.step-content {
  flex: 1 1 auto;
  min-width: 0;
}

.step-content h4 {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 4px;
  font-family: 'SimHei', 'Microsoft YaHei', var(--tp-font-stack);
}

.step-content p {
  font-size: 12px;
  color: #7f8c8d;
  line-height: 1.5;
  margin: 0;
}

.step-arrow {
  color: #c0c4cc;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  margin-top: 5px;
}

/* ── 底部 ──────────────────────────────────────────── */
.intro-footer {
  text-align: center;
  padding: 12px 0;
  color: #909399;
  font-size: 12px;
}
</style>
