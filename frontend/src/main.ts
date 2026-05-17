import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

// 样式加载顺序：设计 Tokens → 字体系统 → Element Plus 全局覆盖
import './styles/tokens.css'
import './styles/fonts.css'
import './styles/element-global.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
