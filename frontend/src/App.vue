<template>
  <div class="app-container"
    @mousemove="onContainerMouseMove"
    @mousedown="onContainerMouseDown"
    @mouseleave="onContainerMouseLeave"
    :style="resizeCursor ? { cursor: resizeCursor } : {}"
  >
    <!-- 启动界面 -->
    <SplashScreen
      v-if="showSplash"
      :steps="bootSteps"
      :min-duration="2200"
      @complete="onSplashComplete"
    />

    <!-- 主应用界面 -->
    <template v-else>
      <!-- 自定义标题栏 -->
      <header class="title-bar" :style="{ '--sidebar-half': (sidebarCollapsed ? 28 : 76) + 'px' }" @mousedown="onTitleBarMouseDown">
        <div class="title-bar-center" @mousedown.stop>
          <span class="title-bar-page">{{ pageTitle }}</span>
        </div>
        <div class="title-bar-right" @mousedown.stop>
          <button class="win-btn minimize" @click="minimizeWindow" title="最小化">
            <svg viewBox="0 0 12 2" width="12" height="2"><rect width="12" height="2" fill="currentColor" rx="1"/></svg>
          </button>
          <button class="win-btn maximize" @click="toggleMaximize" title="最大化">
            <svg v-if="!isMaximized" viewBox="0 0 12 12" width="12" height="12"><rect x="0.5" y="0.5" width="11" height="11" fill="none" stroke="currentColor" stroke-width="1" rx="1"/></svg>
            <svg v-else viewBox="0 0 12 12" width="12" height="12"><rect x="1.5" y="3.5" width="7" height="7" fill="none" stroke="currentColor" stroke-width="1" rx="1"/><path d="M3.5 1.5h7v7" fill="none" stroke="currentColor" stroke-width="1"/></svg>
          </button>
          <button class="win-btn close" @click="closeWindow" title="关闭">
            <svg viewBox="0 0 12 12" width="12" height="12"><path d="M1 1l10 10M11 1L1 11" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
          </button>
        </div>
      </header>

      <div class="app-body">
        <!-- 侧边栏 -->
        <aside :class="['sidebar', { collapsed: sidebarCollapsed }]">
          <div class="sidebar-header" @click.stop="sidebarCollapsed = !sidebarCollapsed" :title="sidebarCollapsed ? '展开' : '收起'">
            <GeoIcon class="logo-icon" :size="20" color="#0F766E" />
            <div v-if="!sidebarCollapsed" class="logo-text-group">
              <span class="logo-text">TracePipeline</span>
              <span class="logo-version">v{{ appVersion }}</span>
            </div>
          </div>

          <nav class="menu">
            <router-link
              v-for="item in menuItems"
              :key="item.path"
              :to="item.path"
              :class="['menu-item', { active: route.path === item.path }]"
            >
              <div class="menu-item-inner">
                <component :is="item.icon" :size="18" class="menu-icon" />
                <span v-if="!sidebarCollapsed" class="menu-label">{{ item.label }}</span>
              </div>
              <div v-if="route.path === item.path" class="menu-active-indicator"></div>
            </router-link>
          </nav>

          <div class="sidebar-footer">
            <div class="footer-section">
              <div class="footer-btn" @click="openInputDir" :title="sidebarCollapsed ? '打开输入目录' : ''">
                <el-icon :size="14"><FolderOpened /></el-icon>
                <span v-if="!sidebarCollapsed">打开输入目录</span>
              </div>
              <div class="footer-btn" @click="openOutputDir" :title="sidebarCollapsed ? '打开输出目录' : ''">
                <el-icon :size="14"><FolderOpened /></el-icon>
                <span v-if="!sidebarCollapsed">打开输出目录</span>
              </div>
              <div class="footer-btn" @click="openLogsDir" :title="sidebarCollapsed ? '打开日志目录' : ''">
                <el-icon :size="14"><Document /></el-icon>
                <span v-if="!sidebarCollapsed">打开日志目录</span>
              </div>
            </div>
            <div class="dev-toggle" :class="{ collapsed: sidebarCollapsed }">
              <el-switch v-model="appStore.isDevMode" active-text="开发者模式" size="small" />
            </div>
          </div>
        </aside>

        <!-- 主内容区 -->
        <main class="main">
          <router-view v-slot="{ Component }">
            <Transition name="page-slide" mode="out-in" class="page-wrapper">
              <KeepAlive :include="['Intro', 'Processing', 'Statistics', 'Comparison', 'Data', 'Config']">
                <component :is="Component" />
              </KeepAlive>
            </Transition>
          </router-view>

          <footer class="status-bar">
            <div class="status-group">
              <span class="status-item" :class="{ 'status-running': appStore.pipelineStatus === 'running' }">
                <span class="status-indicator">
                  <span v-if="appStore.pipelineStatus === 'running'" class="status-pulse"></span>
                  <el-icon v-else :size="12"><Timer /></el-icon>
                </span>
                <span class="status-text">{{ statusText }}</span>
              </span>
              <span class="status-divider"></span>
              <span class="status-item">
                <el-icon :size="12"><Files /></el-icon>
                <span>已选 {{ appStore.selectedFileCount }} 个文件</span>
              </span>
            </div>
            <div class="status-group status-center">
              <span class="status-item status-path" @click="copyPath(appStore.inputDir)" title="点击复制输入目录路径">
                <el-icon :size="12"><Folder /></el-icon>
                <span class="path-text">输入: {{ appStore.inputDir }}</span>
              </span>
              <span class="status-item status-path" @click="copyPath(appStore.outputDir)" title="点击复制输出目录路径">
                <el-icon :size="12"><FolderOpened /></el-icon>
                <span class="path-text">输出: {{ appStore.outputDir }}</span>
              </span>
            </div>
            <div class="status-group">
              <span v-if="appStore.lastOperationTime" class="status-item time">
                <el-icon :size="12"><Clock /></el-icon>
                <span>{{ appStore.lastOperationTime }}</span>
              </span>
            </div>
          </footer>

          <!-- 右下角 resize grip（拖拽调整大小） -->
          <div class="resize-grip" title="调整大小" @mousedown.stop="onResizeGripMouseDown">
            <svg viewBox="0 0 12 12" width="10" height="10">
              <path d="M8 12L12 12L12 8" stroke="currentColor" stroke-width="1.2" fill="none" opacity="0.5"/>
              <path d="M4 12L12 12L12 4" stroke="currentColor" stroke-width="1.2" fill="none" opacity="0.3"/>
            </svg>
          </div>
        </main>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { msg } from '@/utils/message'
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

const appVersion = __APP_VERSION__
const showSplash = ref(true)
const sidebarCollapsed = ref(false)

watch(sidebarCollapsed, (collapsed) => {
  document.documentElement.style.setProperty('--sidebar-half', collapsed ? '28px' : '76px')
}, { immediate: true })

function onSplashComplete(payload: { errors: Array<{ step: string; error: string }> }) {
  const { input_dir, output_dir } = configStore.config
  if (input_dir) appStore.inputDir = input_dir
  if (output_dir) appStore.outputDir = output_dir
  showSplash.value = false
  if (payload.errors.length > 0) {
    const failedSteps = payload.errors.map(e => e.step.replace(/正在|\.{3}/g, '')).join('、')
    msg.warning(`初始化未完成: ${failedSteps}，进入页面后将自动重试`)
  }
  nextTick(async () => {
    if (appStore.inputDir === 'input' && appStore.outputDir === 'output') {
      try {
        await api.ready()
        const cfg = await api.get_config()
        if (cfg.input_dir) appStore.inputDir = cfg.input_dir
        if (cfg.output_dir) appStore.outputDir = cfg.output_dir
        configStore.hydrateConfig(cfg)
      } catch { /* ignore */ }
    }
  })
}

const route = useRoute()
const appStore = useAppStore()
const configStore = useConfigStore()

const menuItems = [
  { path: '/', label: '首页', icon: HomeIcon },
  { path: '/processing', label: '处理', icon: ProcessIcon },
  { path: '/statistics', label: '统计', icon: StatsIcon },
  { path: '/comparison', label: '对比', icon: CompareIcon },
  { path: '/data', label: '数据', icon: DataIcon },
  { path: '/config', label: '配置', icon: ConfigIcon },
]

const pageTitle = computed(() => {
  const item = menuItems.find(m => m.path === route.path)
  return item ? item.label : 'TracePipeline'
})

const statusText = computed(() => {
  switch (appStore.pipelineStatus) {
    case 'running': return '处理中'
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
    msg.success(`已复制路径`, 1500)
  } catch {
    msg.info(path)
  }
}

// ── 窗口控制 ──
const isMaximized = ref(false)

async function minimizeWindow() {
  await api.window_minimize()
}

async function toggleMaximize() {
  await api.window_maximize()
  setTimeout(async () => {
    isMaximized.value = await api.window_is_maximized()
  }, 120)
}

async function closeWindow() {
  await api.window_close()
}

// ── 标题栏拖动移动窗口 ──
const isDragging = ref(false)

function onTitleBarMouseDown(e: MouseEvent) {
  if (e.button !== 0) return
  if (isMaximized.value) return
  isDragging.value = true
  const startX = e.screenX
  const startY = e.screenY
  let lastMoveTime = 0

  api.window_position().then((pos: any) => {
    const startWinX = pos.x
    const startWinY = pos.y

    function onMouseMove(ev: MouseEvent) {
      const now = Date.now()
      if (now - lastMoveTime < 16) return
      lastMoveTime = now
      const dx = ev.screenX - startX
      const dy = ev.screenY - startY
      api.window_move_to(startWinX + dx, startWinY + dy)
    }

    function onMouseUp() {
      isDragging.value = false
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  })
}

// ── 边缘拖拽调整窗口大小 ──
type ResizeEdge = 'left' | 'right' | 'top' | 'bottom' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | null

const RESIZE_BORDER = 6
const isResizing = ref(false)
const resizeEdge = ref<ResizeEdge>(null)
const resizeCursor = ref<string>('')

function detectResizeEdge(e: MouseEvent): ResizeEdge {
  if (isMaximized.value) return null
  const w = window.innerWidth
  const h = window.innerHeight
  const x = e.clientX
  const y = e.clientY

  const onLeft = x < RESIZE_BORDER
  const onRight = x >= w - RESIZE_BORDER
  const onTop = y < RESIZE_BORDER
  const onBottom = y >= h - RESIZE_BORDER

  if (onTop && onLeft) return 'top-left'
  if (onTop && onRight) return 'top-right'
  if (onBottom && onLeft) return 'bottom-left'
  if (onBottom && onRight) return 'bottom-right'
  if (onLeft) return 'left'
  if (onRight) return 'right'
  if (onTop) return 'top'
  if (onBottom) return 'bottom'
  return null
}

const edgeToCursor: Record<string, string> = {
  left: 'ew-resize',
  right: 'ew-resize',
  top: 'ns-resize',
  bottom: 'ns-resize',
  'top-left': 'nwse-resize',
  'top-right': 'nesw-resize',
  'bottom-left': 'nesw-resize',
  'bottom-right': 'nwse-resize',
}

function onContainerMouseMove(e: MouseEvent) {
  if (isResizing.value) return
  const edge = detectResizeEdge(e)
  resizeEdge.value = edge
  resizeCursor.value = edge ? (edgeToCursor[edge] || '') : ''
}

function onContainerMouseDown(e: MouseEvent) {
  const edge = detectResizeEdge(e)
  if (!edge) return
  if (e.button !== 0) return
  e.preventDefault()
  isResizing.value = true

  const startX = e.screenX
  const startY = e.screenY

  Promise.all([api.window_position()]).then(([pos]) => {
    const startWinX = pos.x
    const startWinY = pos.y
    const startWinW = window.innerWidth
    const startWinH = window.innerHeight
    let lastMoveTime = 0

    function onMouseMove(ev: MouseEvent) {
      const now = Date.now()
      if (now - lastMoveTime < 16) return
      lastMoveTime = now
      const dx = ev.screenX - startX
      const dy = ev.screenY - startY

      let newX = startWinX, newY = startWinY
      let newW = startWinW, newH = startWinH

      if (edge && edge.includes('right')) {
        newW = startWinW + dx
      }
      if (edge && edge.includes('left')) {
        newW = startWinW - dx
        newX = startWinX + dx
      }
      if (edge && edge.includes('bottom')) {
        newH = startWinH + dy
      }
      if (edge && edge.includes('top')) {
        newH = startWinH - dy
        newY = startWinY + dy
      }

      newW = Math.max(480, newW)
      newH = Math.max(360, newH)
      if (newW === 480 && edge && edge.includes('left')) {
        newX = startWinX + startWinW - 480
      }
      if (newH === 360 && edge && edge.includes('top')) {
        newY = startWinY + startWinH - 360
      }

      api.window_move_to(newX, newY)
      api.window_resize(newW, newH)
    }

    function onMouseUp() {
      isResizing.value = false
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  })
}

function onContainerMouseLeave() {
  if (!isResizing.value) {
    resizeEdge.value = null
    resizeCursor.value = ''
  }
}

function onResizeGripMouseDown(e: MouseEvent) {
  if (e.button !== 0) return
  if (isMaximized.value) return
  e.preventDefault()
  isResizing.value = true

  const startX = e.screenX
  const startY = e.screenY

  api.window_position().then((pos: any) => {
    const startWinX = pos.x
    const startWinY = pos.y
    const startWinW = window.innerWidth
    const startWinH = window.innerHeight
    let lastMoveTime = 0

    function onMouseMove(ev: MouseEvent) {
      const now = Date.now()
      if (now - lastMoveTime < 16) return
      lastMoveTime = now
      const dx = ev.screenX - startX
      const dy = ev.screenY - startY
      const newW = Math.max(480, startWinW + dx)
      const newH = Math.max(360, startWinH + dy)
      api.window_resize(newW, newH)
    }

    function onMouseUp() {
      isResizing.value = false
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  })
}

// 启动步骤：真实 API 驱动进度
const cacheStore = useCacheStore()

const bootSteps: BootStep[] = [
  {
    label: '正在连接后端服务...',
    targetProgress: 30,
    task: async () => {
      await api.ready()
      const cfg = await api.get_config()
      appStore.setDirs(cfg.input_dir || 'input', cfg.output_dir || 'output')
      configStore.hydrateConfig(cfg)

      const pipelineStore = usePipelineStore()
      const hasStoredRose = localStorage.getItem('tp_last_export_rose_plot') !== null
      const hasStoredNode = localStorage.getItem('tp_last_enable_node_recognition') !== null
      if (!hasStoredRose || !hasStoredNode) {
        pipelineStore.setLastRunConfig(
          cfg.enable_node_recognition ?? false,
          cfg.export_rose_plot ?? false
        )
      }
    }
  },
  {
    label: '正在扫描输入目录...',
    targetProgress: 55,
    task: async () => {
      const files = await api.scan_files(true)
      cacheStore.setScan(files)
    }
  },
  {
    label: '正在初始化字体缓存...',
    targetProgress: 80,
    task: async () => {
      await api.preload_fonts()
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

// config → appStore（状态栏路径显示，immediate 确保启动时同步）
watch(() => configStore.config.input_dir as string | undefined, (val) => { if (val) appStore.inputDir = val }, { immediate: true })
watch(() => configStore.config.output_dir as string | undefined, (val) => { if (val) appStore.outputDir = val }, { immediate: true })
</script>

<style scoped lang="scss">
.app-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow: hidden;
  background:
    linear-gradient(rgba(2, 132, 199, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(2, 132, 199, 0.035) 1px, transparent 1px),
    radial-gradient(circle at 18% 12%, rgba(56, 189, 248, 0.16), transparent 30%),
    radial-gradient(circle at 85% 10%, rgba(15, 118, 110, 0.10), transparent 28%),
    var(--tp-bg-base);
  background-size: 28px 28px, 28px 28px, auto, auto, auto;
}

/* Vue Transition 默认渲染为 span（inline），必须显式 block 才能正确参与 flex 布局 */
.page-wrapper {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

/* ── 标题栏：标题相对内容区居中（排除侧边栏宽度）── */
.title-bar {
  height: 36px;
  background:
    linear-gradient(90deg, #10243f 0%, var(--tp-brand-primary) 45%, #0f3b57 100%);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0;
  flex-shrink: 0;
  user-select: none;
  position: relative;
  z-index: 100;
  box-shadow: 0 1px 0 rgba(125, 211, 252, 0.18), 0 10px 28px rgba(15, 35, 60, 0.12);
  overflow: hidden;
}

.title-bar::after {
  content: '';
  position: absolute;
  left: 152px;
  right: 132px;
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.78), rgba(15, 118, 110, 0.46), transparent);
  opacity: 0.8;
  pointer-events: none;
}

.title-bar-center {
  position: absolute;
  left: calc(50% + var(--sidebar-half, 90px));
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  transition: left 0.25s var(--tp-easing);
}

.title-bar-page {
  font-family: var(--tp-font-heading);
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.84);
  letter-spacing: 0;
  text-shadow: 0 0 14px rgba(56, 189, 248, 0.28);
}

.title-bar-right {
  display: flex;
  align-items: center;
  height: 100%;
  -webkit-app-region: no-drag;
}

.win-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 100%;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: color var(--tp-duration-fast), background var(--tp-duration-fast), transform var(--tp-duration-fast);
  outline: none;
}

.win-btn:hover {
  background: rgba(125, 211, 252, 0.14);
  color: var(--tp-text-inverse);
}

.win-btn:active {
  transform: scale(0.94);
}

.win-btn.close:hover {
  background: var(--tp-danger);
  color: var(--tp-text-inverse);
}

.win-btn svg {
  pointer-events: none;
}

/* ── 主体布局 ── */
.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* ── 侧边栏 ── */
.sidebar {
  width: 152px;
  background:
    linear-gradient(rgba(56, 189, 248, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(56, 189, 248, 0.035) 1px, transparent 1px),
    linear-gradient(180deg, #10243f 0%, var(--tp-brand-primary) 48%, #112b46 100%);
  background-size: 22px 22px, 22px 22px, auto;
  color: var(--tp-text-inverse);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: relative;
  transition: width 0.25s var(--tp-easing);
  overflow: hidden;
  box-shadow: inset -1px 0 0 rgba(125, 211, 252, 0.12), 10px 0 34px rgba(26, 54, 93, 0.14);
}

.sidebar::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(180deg, rgba(56, 189, 248, 0.28), rgba(56, 189, 248, 0.58) 40%, rgba(56, 189, 248, 0.58) 60%, rgba(56, 189, 248, 0.28));
  pointer-events: none;
}

.sidebar.collapsed {
  width: 56px;
}

.sidebar-header {
  height: 48px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  cursor: pointer;
  transition: justify-content padding 0.25s var(--tp-easing);
  position: relative;
}

.sidebar-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 8px;
  right: 8px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(125, 211, 252, 0.22), transparent);
  pointer-events: none;
}

.sidebar-header:hover {
  background: rgba(56, 189, 248, 0.06);
}

.sidebar.collapsed .sidebar-header {
  justify-content: center;
  padding: 0;
}

.logo-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.logo-text-group {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
  white-space: nowrap;
}

.logo-text {
  font-family: var(--tp-font-heading);
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  line-height: 1.2;
}

.logo-version {
  font-family: var(--tp-font-data);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.menu {
  flex: 1;
  padding: 10px 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  position: relative;
  height: 44px;
  margin: 0 8px;
  padding: 0 10px;
  color: rgba(255, 255, 255, 0.6);
  text-decoration: none;
  font-size: 14px;
  border-radius: var(--tp-radius-md);
  transition: color var(--tp-duration-normal) var(--tp-easing), background var(--tp-duration-normal) var(--tp-easing), transform var(--tp-duration-normal) var(--tp-easing);
  overflow: hidden;
}

.menu-item::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--tp-radius-md);
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.14), rgba(255, 255, 255, 0.055));
  opacity: 0;
  transform: scaleX(0.3);
  transition: all var(--tp-duration-normal) var(--tp-easing-expo);
  transform-origin: left center;
}

.sidebar.collapsed .menu-item {
  justify-content: center;
  padding: 0;
  margin: 2px 8px;
}

.menu-item-inner {
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
  z-index: 2;
  overflow: hidden;
  white-space: nowrap;
}

.menu-icon {
  flex-shrink: 0;
  opacity: 0.7;
  transition: all var(--tp-duration-normal);
}

.menu-label {
  font-family: var(--tp-font-heading);
  font-weight: 500;
}

.menu-item:hover {
  color: rgba(255, 255, 255, 0.9);
  transform: translateX(2px);
}

.menu-item:hover::before {
  opacity: 1;
  transform: scaleX(1);
}

.menu-item:hover .menu-icon {
  opacity: 1;
  transform: scale(1.1);
}

.menu-item.active {
  color: var(--tp-text-inverse);
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.20), rgba(255, 255, 255, 0.06));
  box-shadow: inset 0 0 0 1px rgba(125, 211, 252, 0.16), var(--tp-shadow-sidebar-item);
}

.menu-item.active .menu-icon {
  opacity: 1;
  color: var(--tp-brand-accent-light);
  transform: scale(1.05);
}

.menu-active-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  background: linear-gradient(180deg, var(--tp-brand-accent-light), var(--tp-geo-emerald));
  border-radius: 0 3px 3px 0;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.72), 0 0 22px rgba(15, 118, 110, 0.32);
  transition: all var(--tp-duration-normal) var(--tp-easing-expo);
}

/* ── 侧边栏底部 ── */
.sidebar-footer {
  padding: 10px 8px;
  border-top: 1px solid rgba(125, 211, 252, 0.12);
  overflow: hidden;
}

.sidebar.collapsed .sidebar-footer {
  padding: 10px 0;
}

.footer-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 8px;
}

.sidebar.collapsed .footer-section {
  align-items: center;
}

.footer-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: 30px;
  padding: 0 10px;
  border-radius: var(--tp-radius-sm);
  cursor: pointer;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.55);
  transition: all var(--tp-duration-normal);
  white-space: nowrap;
  overflow: hidden;
}

.sidebar.collapsed .footer-btn {
  justify-content: center;
  padding: 0;
  width: 40px;
  height: 32px;
}

.footer-btn:hover {
  color: rgba(255, 255, 255, 0.9);
  background: rgba(56, 189, 248, 0.10);
  box-shadow: inset 0 0 0 1px rgba(125, 211, 252, 0.10);
}

.footer-btn :deep(.el-icon) {
  flex-shrink: 0;
  opacity: 0.7;
}

.dev-toggle {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding: 8px 0 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.dev-toggle.collapsed {
  justify-content: center;
}

.dev-toggle.collapsed :deep(.el-switch__label) {
  display: none;
}

.dev-toggle :deep(.el-switch__label) {
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
}

/* ── 主内容区 ── */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: transparent;
  overflow: hidden;
  position: relative;
}

.main::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 72% 6%, rgba(56, 189, 248, 0.12), transparent 28%),
    linear-gradient(120deg, rgba(255, 255, 255, 0.45), rgba(255, 255, 255, 0));
  pointer-events: none;
  z-index: 0;
}

.main > * {
  position: relative;
  z-index: 1;
}

/* ── 状态栏 ── */
.status-bar {
  height: 36px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(14px) saturate(1.15);
  -webkit-backdrop-filter: blur(14px) saturate(1.15);
  border-top: 1px solid rgba(125, 211, 252, 0.18);
  box-shadow: 0 -8px 24px rgba(15, 35, 60, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.72);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 20px;
  font-family: var(--tp-font-body);
  font-size: 13px;
  color: var(--tp-text-tertiary);
  flex-shrink: 0;
  transition: background var(--tp-duration-normal) var(--tp-easing-smooth);
}

.status-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-center {
  flex: 1;
  justify-content: center;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 5px;
  transition: color var(--tp-duration-fast);
}

.status-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
}

.status-pulse {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--tp-success);
  animation: tp-pulse 2s ease-in-out infinite;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.45), 0 0 18px rgba(16, 185, 129, 0.20);
}

.status-running .status-text {
  color: var(--tp-success);
  font-weight: 500;
}

.status-divider {
  width: 1px;
  height: 14px;
  background: var(--tp-border);
}

/* 可点击路径 */
.status-path {
  cursor: pointer;
  padding: 3px 8px;
  border-radius: var(--tp-radius-sm);
  transition: all var(--tp-duration-fast);
  font-family: var(--tp-font-data);
  font-size: 12px;
}

.status-path:hover {
  background: rgba(56, 189, 248, 0.10);
  color: var(--tp-text-primary);
  box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.12);
}

.path-text {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-item.time {
  color: var(--tp-text-muted);
  font-family: var(--tp-font-data);
}

/* 页面切换动画 */
.page-slide-enter-active,
.page-slide-leave-active {
  transition: opacity 0.36s var(--tp-easing-expo), transform 0.36s var(--tp-easing-expo), filter 0.36s var(--tp-easing-expo);
}

.page-slide-enter-from {
  opacity: 0;
  transform: translateY(14px) scale(0.985);
  filter: blur(4px);
}

.page-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.99);
  filter: blur(2px);
}

/* ── 右下角 resize grip ── */
.resize-grip {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 16px;
  height: 16px;
  cursor: nwse-resize;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  padding: 2px;
  color: var(--tp-text-muted);
  z-index: 50;
  transition: color var(--tp-duration-fast);
}

.resize-grip:hover {
  color: var(--tp-brand-accent);
}

.resize-grip svg {
  pointer-events: none;
}

/* ── 响应式适配 ──────────────────────────────────────── */

@media (max-width: 768px) {
  .sidebar {
    width: 56px;
  }

  .sidebar .logo-text-group,
  .sidebar .menu-label,
  .sidebar .footer-btn span,
  .sidebar .dev-toggle :deep(.el-switch__label) {
    display: none;
  }

  .sidebar .sidebar-header {
    justify-content: center;
    padding: 0;
  }

  .sidebar .menu-item {
    justify-content: center;
  }

  .sidebar .footer-section {
    align-items: center;
  }

  .sidebar .footer-btn {
    justify-content: center;
    padding: 0;
    width: 40px;
    height: 32px;
  }

  .sidebar .dev-toggle {
    justify-content: center;
  }

  .title-bar {
    height: 32px;
  }

  .title-bar-page {
    font-size: 12px;
  }

  .win-btn {
    width: 36px;
  }

  .status-bar {
    height: 30px;
    padding: 0 10px;
    gap: 8px;
    font-size: 12px;
  }

  .status-center {
    display: none;
  }

  .path-text {
    max-width: 100px;
  }
}

@media (max-width: 480px) {
  .sidebar {
    width: 44px;
  }

  .sidebar .menu-item {
    margin: 0 4px;
    height: 38px;
  }

  .title-bar {
    height: 28px;
  }

  .status-bar {
    height: 26px;
    padding: 0 8px;
    font-size: 11px;
  }

  .status-group {
    gap: 6px;
  }
}
</style>
