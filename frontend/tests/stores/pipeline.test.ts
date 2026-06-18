/**
 * pipeline store 单元测试 — 验证流水线状态管理。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePipelineStore } from '@/stores/pipeline'

describe('usePipelineStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('初始状态：running=false, progress 为零值, results 为空', () => {
    const store = usePipelineStore()
    expect(store.running).toBe(false)
    expect(store.isRunning).toBe(false)
    expect(store.progress).toEqual({ current: 0, total: 0, filename: '', message: '' })
    expect(store.results).toEqual([])
  })

  it('reset() 清除全部运行状态', () => {
    const store = usePipelineStore()
    store.running = true
    store.progress = { current: 5, total: 10, filename: 'test', message: 'running' }
    store.results = [{ outcrop: 'O76', status: 'success' } as any]

    store.reset()

    expect(store.running).toBe(false)
    expect(store.progress).toEqual({ current: 0, total: 0, filename: '', message: '' })
    expect(store.results).toEqual([])
  })

  it('setLastRunConfig() 持久化到 localStorage 并更新 ref', () => {
    const store = usePipelineStore()

    store.setLastRunConfig(true, true)

    expect(store.lastEnableNodeRecognition).toBe(true)
    expect(store.lastExportRosePlot).toBe(true)
    expect(localStorage.getItem('tp_last_enable_node_recognition')).toBe('true')
    expect(localStorage.getItem('tp_last_export_rose_plot')).toBe('true')

    store.setLastRunConfig(false, false)

    expect(store.lastEnableNodeRecognition).toBe(false)
    expect(store.lastExportRosePlot).toBe(false)
    expect(localStorage.getItem('tp_last_enable_node_recognition')).toBe('false')
    expect(localStorage.getItem('tp_last_export_rose_plot')).toBe('false')
  })

  it('从 localStorage 恢复上次运行配置', () => {
    localStorage.setItem('tp_last_enable_node_recognition', 'true')
    localStorage.setItem('tp_last_export_rose_plot', 'false')

    const store = usePipelineStore()

    expect(store.lastEnableNodeRecognition).toBe(true)
    expect(store.lastExportRosePlot).toBe(false)
  })

  it('isRunning 是 running 的计算属性', () => {
    const store = usePipelineStore()
    expect(store.isRunning).toBe(false)
    store.running = true
    expect(store.isRunning).toBe(true)
  })
})
