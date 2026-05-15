<template>
  <div class="intro-view">
    <!-- Hero 区域 -->
    <div class="hero-section">
      <div class="hero-content">
        <GeoIcon class="hero-logo" :size="48" color="#B85C38" />
        <h1 class="hero-title">TracePipeline</h1>
        <p class="hero-subtitle">岩体节理测线数据处理与可视化系统</p>
        <p class="hero-desc">
          面向地质工程领域的专业数据处理平台，支持节理迹线自动识别、走向玫瑰图生成、
          节点拓扑分析、多露头对比统计等功能。
        </p>
        <el-button type="primary" size="large" @click="$router.push('/processing')">
          <el-icon><HomeFilled /></el-icon>
          开始使用
        </el-button>
      </div>
    </div>

    <!-- 功能模块 -->
    <div class="modules-section">
      <h2 class="section-title">功能模块</h2>
      <div class="modules-grid">
        <el-card class="module-card" shadow="hover" @click="$router.push('/processing')">
          <div class="module-icon">
            <el-icon :size="32" color="#B85C38"><HomeFilled /></el-icon>
          </div>
          <h3 class="module-name">处理</h3>
          <p class="module-desc">
            批量处理露头数据，自动计算迹线参数，支持节点识别、走向玫瑰图生成与多种圆窗策略。
          </p>
        </el-card>

        <el-card class="module-card" shadow="hover" @click="$router.push('/statistics')">
          <div class="module-icon">
            <el-icon :size="32" color="#2E7D5A"><DataLine /></el-icon>
          </div>
          <h3 class="module-name">统计</h3>
          <p class="module-desc">
            单露头统计指标展示，包含 P10/P20/P21 密度、迹长直方图、裂隙类型饼图与结果图浏览。
          </p>
        </el-card>

        <el-card class="module-card" shadow="hover" @click="$router.push('/comparison')">
          <div class="module-icon">
            <el-icon :size="32" color="#2c3e50"><DocumentCopy /></el-icon>
          </div>
          <h3 class="module-name">对比</h3>
          <p class="module-desc">
            多露头参数对比表格与柱状图分析，直观比较不同露头的迹线密度、裂隙类型与节点指标。
          </p>
        </el-card>

        <el-card class="module-card" shadow="hover" @click="$router.push('/data')">
          <div class="module-icon">
            <el-icon :size="32" color="#7B1FA2"><List /></el-icon>
          </div>
          <h3 class="module-name">数据</h3>
          <p class="module-desc">
            查看输入/输出数据明细，支持裂隙情况、计算数据、端点坐标、走向与迹长等多维度浏览。
          </p>
        </el-card>

        <el-card class="module-card" shadow="hover" @click="$router.push('/config')">
          <div class="module-icon">
            <el-icon :size="32" color="#606266"><Setting /></el-icon>
          </div>
          <h3 class="module-name">配置</h3>
          <p class="module-desc">
            全局参数、绘图样式与开发者模式配置，灵活调整处理流程与可视化效果。
          </p>
        </el-card>
      </div>
    </div>

    <!-- 快速开始 -->
    <div class="quickstart-section">
      <h2 class="section-title">快速开始</h2>
      <div class="steps">
        <div class="step-item">
          <div class="step-number">1</div>
          <div class="step-content">
            <h4>选择露头文件</h4>
            <p>在"处理"页面扫描并选择需要处理的露头 Excel 文件，配置处理参数。</p>
          </div>
        </div>
        <div class="step-arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
        <div class="step-item">
          <div class="step-number">2</div>
          <div class="step-content">
            <h4>运行处理流程</h4>
            <p>点击"开始处理"启动流水线，系统将自动完成迹线计算、玫瑰图绘制与节点识别。</p>
          </div>
        </div>
        <div class="step-arrow">
          <el-icon><ArrowRight /></el-icon>
        </div>
        <div class="step-item">
          <div class="step-number">3</div>
          <div class="step-content">
            <h4>查看分析结果</h4>
            <p>在"统计"、"对比"或"数据"页面查看处理结果，支持图表交互与数据导出。</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部信息 -->
    <footer class="intro-footer">
      <p>TracePipeline v1.0 · 地质工程数据处理平台</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { HomeFilled, DataLine, DocumentCopy, List, Setting, ArrowRight } from '@element-plus/icons-vue'
import GeoIcon from '@/components/GeoIcon.vue'
</script>

<style scoped lang="scss">
.intro-view {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
  background: #f5f7fa;
}

/* Hero 区域 */
.hero-section {
  background: linear-gradient(135deg, #2c3e50 0%, #1E2935 100%);
  border-radius: 12px;
  padding: 48px 32px;
  text-align: center;
  color: #fff;
  margin-bottom: 32px;
}

.hero-content {
  max-width: 640px;
  margin: 0 auto;
}

.hero-logo {
  margin-bottom: 16px;
}

.hero-title {
  font-size: 36px;
  font-weight: 700;
  margin: 0 0 8px;
  font-family: var(--tp-font-stack);
  letter-spacing: 1px;
}

.hero-subtitle {
  font-size: 18px;
  font-weight: 400;
  opacity: 0.9;
  margin: 0 0 16px;
  color: #e0e0e0;
}

.hero-desc {
  font-size: 14px;
  line-height: 1.8;
  opacity: 0.75;
  margin: 0 0 24px;
  color: #c0c4cc;
}

/* 功能模块 */
.modules-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 20px;
  text-align: center;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.module-card {
  cursor: pointer;
  transition: all 0.3s;
  border-radius: 8px;
}

.module-card:hover {
  transform: translateY(-4px);
}

.module-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 12px;
  background: #f5f7fa;
  margin-bottom: 16px;
}

.module-name {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 8px;
}

.module-desc {
  font-size: 13px;
  color: #7f8c8d;
  line-height: 1.6;
  margin: 0;
}

/* 快速开始 */
.quickstart-section {
  background: #fff;
  border-radius: 12px;
  padding: 32px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
}

.steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  max-width: 260px;
}

.step-number {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #B85C38;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-content h4 {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 6px;
}

.step-content p {
  font-size: 13px;
  color: #7f8c8d;
  line-height: 1.6;
  margin: 0;
}

.step-arrow {
  color: #c0c4cc;
  font-size: 20px;
  flex-shrink: 0;
}

/* 底部 */
.intro-footer {
  text-align: center;
  padding: 16px 0;
  color: #909399;
  font-size: 12px;
}
</style>
