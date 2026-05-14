<template>
  <div class="app-container">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <GeoIcon class="logo-icon" :size="22" color="#B85C38" />
        <span class="logo-text">TracePipeline</span>
        <span class="logo-version">v1.0</span>
      </div>
      <nav class="menu">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          :class="['menu-item', { active: route.path === item.path }]"
        >
          <el-icon :size="20"><component :is="item.icon" /></el-icon>
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
      <router-view />
      <footer class="status-bar">
        <span class="status-item">
          <el-icon :size="12"><Timer /></el-icon>
          状态: {{ statusText }}
        </span>
        <span class="status-item">
          <el-icon :size="12"><Files /></el-icon>
          选中: {{ appStore.selectedFileCount }} 个文件
        </span>
        <span class="status-item">
          <el-icon :size="12"><Folder /></el-icon>
          输入: {{ appStore.inputDir }}
        </span>
        <span class="status-item">
          <el-icon :size="12"><FolderOpened /></el-icon>
          输出: {{ appStore.outputDir }}
        </span>
        <span v-if="appStore.lastOperationTime" class="status-item time">
          <el-icon :size="12"><Clock /></el-icon>
          {{ appStore.lastOperationTime }}
        </span>
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  HomeFilled, DataLine, DocumentCopy, List, Setting,
  FolderOpened, Document, Timer, Files, Folder, Clock,
} from '@element-plus/icons-vue'
import GeoIcon from '@/components/GeoIcon.vue'
import { useAppStore } from '@/stores/app'
import { useConfigStore } from '@/stores/config'
import { api } from '@/api/pywebview'

const route = useRoute()
const appStore = useAppStore()
const configStore = useConfigStore()

const menuItems = [
  { path: '/processing', label: '处理', icon: HomeFilled },
  { path: '/statistics', label: '统计', icon: DataLine },
  { path: '/comparison', label: '对比', icon: DocumentCopy },
  { path: '/data', label: '数据', icon: List },
  { path: '/config', label: '配置', icon: Setting },
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

onMounted(async () => {
  try {
    const cfg = await api.get_config()
    appStore.inputDir = cfg.input_dir || 'input'
    appStore.outputDir = cfg.output_dir || 'output'
    configStore.config = { ...cfg }
  } catch (e) {
    ElMessage.warning('无法加载配置')
  }
})
</script>

<style scoped lang="scss">
.app-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.sidebar {
  width: 200px;
  background: #1E2935;
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
  height: 48px;
  color: rgba(255,255,255,0.75);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  border-left: 4px solid transparent;
}

.menu-item:hover {
  background: #243342;
  color: #fff;
}

.menu-item.active {
  background: #2c3e50;
  color: #fff;
  border-left-color: #B85C38;
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
  background: #f5f7fa;
  overflow: hidden;
}

.status-bar {
  height: 32px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 0 24px;
  font-size: 12px;
  color: #7f8c8d;
  flex-shrink: 0;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-item.time {
  margin-left: auto;
  color: #909399;
}
</style>
