import { createRouter, createWebHashHistory } from 'vue-router'

const IntroView = () => import('@/views/IntroView.vue')
const ProcessingView = () => import('@/views/ProcessingView.vue')
const StatisticsView = () => import('@/views/StatisticsView.vue')
const ComparisonView = () => import('@/views/ComparisonView.vue')
const DataView = () => import('@/views/DataView.vue')
const ConfigView = () => import('@/views/ConfigView.vue')

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
