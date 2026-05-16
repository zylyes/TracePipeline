import { createRouter, createWebHashHistory } from 'vue-router'
import IntroView from '@/views/IntroView.vue'
import ProcessingView from '@/views/ProcessingView.vue'
import StatisticsView from '@/views/StatisticsView.vue'
import ComparisonView from '@/views/ComparisonView.vue'
import DataView from '@/views/DataView.vue'
import ConfigView from '@/views/ConfigView.vue'

const routes = [
  { path: '/', name: 'Intro', component: IntroView, meta: { keepAlive: true } },
  { path: '/processing', name: 'Processing', component: ProcessingView, meta: { keepAlive: true } },
  { path: '/statistics', name: 'Statistics', component: StatisticsView, meta: { keepAlive: true } },
  { path: '/comparison', name: 'Comparison', component: ComparisonView, meta: { keepAlive: true } },
  { path: '/data', name: 'Data', component: DataView, meta: { keepAlive: true } },
  { path: '/config', name: 'Config', component: ConfigView, meta: { keepAlive: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
