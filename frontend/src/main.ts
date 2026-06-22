import { createApp } from 'vue'
import { createPinia } from 'pinia'
import {
  ElAlert,
  ElButton,
  ElCheckbox,
  ElCol,
  ElCollapse,
  ElCollapseItem,
  ElColorPicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDivider,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElLoading,
  ElOption,
  ElPagination,
  ElProgress,
  ElRadio,
  ElRadioButton,
  ElRadioGroup,
  ElRow,
  ElSelect,
  ElSlider,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

// 样式加载顺序：设计 Tokens → 字体系统 → Element Plus 全局覆盖
import './styles/tokens.css'
import './styles/fonts.css'
import './styles/element-global.css'

const app = createApp(App)

const elementPlusPlugins = [
  ElAlert,
  ElButton,
  ElCheckbox,
  ElCol,
  ElCollapse,
  ElCollapseItem,
  ElColorPicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDivider,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElLoading,
  ElOption,
  ElPagination,
  ElProgress,
  ElRadio,
  ElRadioButton,
  ElRadioGroup,
  ElRow,
  ElSelect,
  ElSlider,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
]

app.use(createPinia())
app.use(router)
elementPlusPlugins.forEach(plugin => app.use(plugin))

app.mount('#app')
