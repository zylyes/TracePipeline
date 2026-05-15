import { createRouter, createWebHashHistory } from 'vue-router'
import IntroView from '@/views/IntroView.vue'
import ProcessingView from '@/views/ProcessingView.vue'
import StatisticsView from '@/views/StatisticsView.vue'
import ComparisonView from '@/views/ComparisonView.vue'
import DataView from '@/views/DataView.vue'
import ConfigView from '@/views/ConfigView.vue'

const routes = [
  { path: '/', name: 'Intro', component: IntroView },
  { path: '/processing', name: 'Processing', component: ProcessingView },
  { path: '/statistics', name: 'Statistics', component: StatisticsView },
  { path: '/comparison', name: 'Comparison', component: ComparisonView },
  { path: '/data', name: 'Data', component: DataView },
  { path: '/config', name: 'Config', component: ConfigView },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
