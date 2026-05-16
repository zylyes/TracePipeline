<template>
  <div class="app-container">
    <!-- 启动界面 -->
    <SplashScreen
      v-if="showSplash"
      :steps="bootSteps"
      :min-duration="1500"
      @complete="onSplashComplete"
    />

    <!-- 主应用界面 -->
    <template v-else>
      <!-- 侧边栏 -->
      <aside class="sidebar">
      <div class="logo">
        <GeoIcon class="logo-icon" :size="22" color="#B85C38" />
        <span class="logo-text">TracePipeline</span>
        <span class="logo-version">v{{ appVersion }}</span>
      </div>
      <nav class="menu">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          :class="['menu-item', { active: route.path === item.path }]"
        >
          <component :is="item.icon" :size="20" class="menu-icon" />
          <span class="menu-label">{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="footer-btn" @click="openInputDir">
          <el-icon :size="16"><FolderOpened /></el-icon>
          <span>打开输入目录</span>
        </div>
        <div class="footer-btn" @click="openOutputDir">
          <el-icon :size="16"><FolderOpened /></el-icon>
          <span>打开输出目录</span>
        </div>
        <div class="footer-btn" @click="openLogsDir">
          <el-icon :size="16"><Document /></el-icon>
          <span>打开日志目录</span>
        </div>
        <div class="dev-toggle">
          <el-switch v-model="appStore.isDevMode" active-text="开发者模式" size="small" />
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main">
      <router-view v-slot="{ Component }">
        <Transition name="page-slide" mode="out-in">
          <KeepAlive :include="['Intro', 'Processing', 'Statistics', 'Comparison', 'Data', 'Config']">
            <component :is="Component" />
          </KeepAlive>
        </Transition>
      </router-view>
      <footer class="status-bar">
        <div class="status-group">
          <span class="status-item" :class="{ 'status-running': appStore.pipelineStatus === 'running' }">
            <el-icon :size="12"><Timer /></el-icon>
            <span class="status-dot" v-if="appStore.pipelineStatus === 'running'"></span>
            状态: {{ statusText }}
          </span>
          <span class="status-item">
            <el-icon :size="12"><Files /></el-icon>
            选中: {{ appStore.selectedFileCount }} 个文件
          </span>
        </div>
        <div class="status-group">
          <span class="status-item status-path" @click="copyPath(appStore.inputDir)" title="点击复制输入目录路径">
            <el-icon :size="12"><Folder /></el-icon>
            <span class="path-text">输入: {{ appStore.inputDir }}</span>
          </span>
          <span class="status-item status-path" @click="copyPath(appStore.outputDir)" title="点击复制输出目录路径">
            <el-icon :size="12"><FolderOpened /></el-icon>
            <span class="path-text">输出: {{ appStore.outputDir }}</span>
          </span>
        </div>
        <span v-if="appStore.lastOperationTime" class="status-item time">
          <el-icon :size="12"><Clock /></el-icon>
          {{ appStore.lastOperationTime }}
        </span>
      </footer>
    </main>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const appVersion = __APP_VERSION__
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { FolderOpened, Document, Timer, Files, Folder, Clock } from '@element-plus/icons-vue'
import GeoIcon from '@/components/GeoIcon.vue'
import SplashScreen from '@/components/SplashScreen.vue'
import type { BootStep } from '@/components/SplashScreen.vue'
import HomeIcon from '@/components/icons/HomeIcon.vue'
import ProcessIcon from '@/components/icons/ProcessIcon.vue'
import StatsIcon from '@/components/icons/StatsIcon.vue'
import CompareIcon from '@/components/icons/CompareIcon.vue'
import DataIcon from '@/components/icons/DataIcon.vue'
import ConfigIcon from '@/components/icons/ConfigIcon.vue'
import { useAppStore } from '@/stores/app'
import { useConfigStore } from '@/stores/config'
import { usePipelineStore } from '@/stores/pipeline'
import { useCacheStore } from '@/stores/cache'
import { api } from '@/api/pywebview'

const showSplash = ref(true)

function onSplashComplete(payload: { errors: Array<{ step: string; error: string }> }) {
  showSplash.value = false
  if (payload.errors.length > 0) {
    const failedSteps = payload.errors.map(e => e.step.replace(/正在|\.\.\./g, '')).join('、')
    ElMessage.warning(`初始化未完成: ${failedSteps}，进入页面后将自动重试`)
  }
}

const route = useRoute()
const appStore = useAppStore()
const configStore = useConfigStore()
const cacheStore = useCacheStore()

const menuItems = [
  { path: '/', label: '首页', icon: HomeIcon },
  { path: '/processing', label: '处理', icon: ProcessIcon },
  { path: '/statistics', label: '统计', icon: StatsIcon },
  { path: '/comparison', label: '对比', icon: CompareIcon },
  { path: '/data', label: '数据', icon: DataIcon },
  { path: '/config', label: '配置', icon: ConfigIcon },
]

const statusText = computed(() => {
  switch (appStore.pipelineStatus) {
    case 'running': return '处理中...'
    case 'completed': return '处理完成'
    case 'error': return '处理出错'
    default: return '就绪'
  }
})

async function openInputDir() {
  await api.open_directory(appStore.inputDir)
}

async function openOutputDir() {
  await api.open_directory(appStore.outputDir)
}

async function openLogsDir() {
  await api.open_directory('logs')
}

async function copyPath(path: string) {
  try {
    await navigator.clipboard.writeText(path)
    ElMessage.success(`已复制: ${path}`)
  } catch {
    ElMessage.info(path)
  }
}

// 启动步骤：真实 API 驱动进度
const bootSteps: BootStep[] = [
  {
    label: '正在连接后端服务...',
    targetProgress: 30,
    task: async () => {
      const cfg = await api.get_config()
      appStore.inputDir = cfg.input_dir || 'input'
      appStore.outputDir = cfg.output_dir || 'output'
      configStore.config = { ...cfg }

      const pipelineStore = usePipelineStore()
      const hasStoredRose = localStorage.getItem('tp_last_export_rose_plot') !== null
      const hasStoredNode = localStorage.getItem('tp_last_enable_node_recognition') !== null
      if (!hasStoredRose || !hasStoredNode) {
        pipelineStore.setLastRunConfig(
          cfg.enable_node_recognition ?? true,
          cfg.export_rose_plot ?? true
        )
      }
    }
  },
  {
    label: '正在扫描工作目录...',
    targetProgress: 60,
    task: async () => {
      const files = await api.scan_files()
      cacheStore.setScan(files)
    }
  },
  {
    label: '正在加载统计数据...',
    targetProgress: 90,
    task: async () => {
      const files = cacheStore.getScan()
      if (files && files.length > 0) {
        const firstOutcrop = files[0].outcrop
        const stats = await api.get_stats(firstOutcrop)
        if (!stats.error) {
          cacheStore.setStats(firstOutcrop, stats)
        }
      }
    }
  },
  {
    label: '正在准备界面...',
    targetProgress: 100,
    task: async () => {
      // 空步骤，确保进度到 100%
    }
  }
]
</script>

<style scoped lang="scss">
.app-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.sidebar {
  width: 210px;
  background: #1A2332;
  color: #fff;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.logo {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-icon { display: flex; align-items: center; }
.logo-text { font-size: 15px; font-weight: 600; font-family: var(--tp-font-stack); }
.logo-version { font-size: 11px; opacity: 0.6; margin-left: auto; }

.menu {
  flex: 1;
  padding: 12px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  height: 46px;
  color: rgba(255,255,255,0.7);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.menu-icon {
  flex-shrink: 0;
  opacity: 0.8;
}

.menu-item:hover {
  background: #222d3a;
  color: #fff;
}

.menu-item:hover .menu-icon {
  opacity: 1;
}

.menu-item.active {
  background: #253544;
  color: #fff;
  border-left-color: #B85C38;
}

.menu-item.active .menu-icon {
  opacity: 1;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
}

.footer-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  height: 32px;
  padding: 0 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255,255,255,0.7);
  transition: all 0.2s;
}

.footer-btn:hover {
  color: #fff;
  background: rgba(255,255,255,0.08);
}

.dev-toggle {
  margin-top: 8px;
  :deep(.el-switch__label) { color: rgba(255,255,255,0.6); font-size: 12px; }
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f8f9fa;
  overflow: hidden;
}

.status-bar {
  height: 32px;
  background: var(--tp-bg-card);
  border-top: 1px solid var(--tp-border);
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 0 24px;
  font-size: 12px;
  color: var(--tp-text-secondary);
  flex-shrink: 0;
}

.status-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
  transition: color var(--tp-duration-fast);
}

.status-item.time {
  margin-left: auto;
  color: var(--tp-text-muted);
}

/* 运行状态呼吸灯 */
.status-running .status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--tp-success);
  animation: tp-pulse 2s ease-in-out infinite;
}

/* 可点击路径 */
.status-path {
  cursor: pointer;
  padding: 2px 6px;
  border-radius: var(--tp-radius-sm);
  transition: all var(--tp-duration-fast);
}

.status-path:hover {
  background: var(--tp-bg-hover);
  color: var(--tp-text-primary);
}

.path-text {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 页面切换动画 */
.page-slide-enter-active,
.page-slide-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.page-slide-enter-from {
  opacity: 0;
  transform: translateX(12px);
}
.page-slide-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}
</style>
