import { createRouter, createWebHashHistory } from 'vue-router'
import ProcessingView from '@/views/ProcessingView.vue'
import StatisticsView from '@/views/StatisticsView.vue'
import ComparisonView from '@/views/ComparisonView.vue'
import DataView from '@/views/DataView.vue'
import ConfigView from '@/views/ConfigView.vue'

const routes = [
  { path: '/', redirect: '/processing' },
  { path: '/processing', name: 'Processing', component: ProcessingView },
  { path: '/statistics', name: 'Statistics', component: StatisticsView },
  { path: '/comparison', name: 'Comparison', component: ComparisonView },
  { path: '/data', name: 'Data', component: DataView },
  { path: '/config', name: 'Config', component: ConfigView },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
