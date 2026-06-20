/**
 * Python 后端 API 封装层。
 *
 * ## 架构
 *
 * 前端通过 `pywebview.api` 调用后端 `GuiApi` 类暴露的方法。
 * 本模块负责：
 * - **就绪等待** (`waitForApi`): 轮询 `pywebviewready` 事件，确保 API 可用后再放行调用
 * - **开发回退** (`mockApi`): 在浏览器环境（`pywebview` 未定义）自动使用 mock 数据
 * - **类型安全出口** (`api` 对象): 为每个后端方法提供带默认参数的 TypeScript 包装
 *
 * ## 调用约定
 *
 * - 所有方法均为 async，返回 Promise
 * - 后端异常会以 rejected Promise 形式抛出，由调用方 catch 处理
 * - 参数类型应与 `GuiApi` 方法签名保持一致
 *
 * @module pywebview
 */

/** pywebview 注入的全局对象，仅在桌面端 WebView2 环境中存在 */
declare const pywebview: any

/** 文件扫描结果条目（与 stores/cache.ts 中的定义一致） */
interface ScanEntry {
  stem: string
  outcrop: string
  path: string
  status: 'completed' | 'pending'
}

/** GuiApi 暴露给前端的 JS Bridge 方法签名 */
interface GuiApiInterface {
  get_config(): Promise<unknown>
  set_config(cfg: Record<string, unknown>): Promise<unknown>
  reset_config(): Promise<unknown>
  reset_processing_config(): Promise<unknown>
  reset_style_config(): Promise<unknown>
  scan_files(force?: boolean): Promise<unknown>
  run_pipeline(targets: string[], config: Record<string, unknown>): Promise<unknown>
  poll_progress(): Promise<unknown>
  get_results(): Promise<unknown>
  get_stats(outcrop: string): Promise<unknown>
  get_comparison(outcrops: string[]): Promise<unknown>
  get_data(outcrop: string, section: string, page: number, page_size: number, source?: string): Promise<unknown>
  generate_preview(config: Record<string, unknown>): Promise<unknown>
  get_logs(tail?: number, level?: string): Promise<string[]>
  generate_report(outcrop: string, report_type: string, fmt: string, save_path?: string): Promise<unknown>
  generate_reports_zip(targets: string[], report_type: string, fmt: string, save_path?: string): Promise<unknown>
  poll_report_progress(): Promise<unknown>
  get_provenance(outcrop: string): Promise<unknown>
  get_audit_log(limit?: number): Promise<unknown>
  open_external(url: string): Promise<boolean>
  open_directory(path: string): Promise<boolean>
  browse_folder(): Promise<string>
  ask_save_path(defaultName?: string, fileFilter?: string): Promise<string>
  export_config_json(folder: string, content: string): Promise<boolean>
  get_image_meta(path: string): Promise<unknown>
  get_image_data(path: string): Promise<{ data?: string; mtime_ns?: number; size?: number }>
  get_image(path: string): Promise<string>
  get_image_thumbnail(path: string, maxPx?: number): Promise<string>
  preload_fonts(): Promise<unknown>
  check_webview2(): Promise<{ installed: boolean }>
  window_minimize(): Promise<boolean>
  window_maximize(): Promise<boolean>
  window_resize(w: number, h: number): Promise<boolean>
  window_close(): Promise<boolean>
  window_move_by(dx: number, dy: number): Promise<boolean>
  window_position(): Promise<{ x: number; y: number }>
  window_move_to(x: number, y: number): Promise<boolean>
  window_is_maximized(): Promise<boolean>
}

/**
 * 获取实际 API 对象。
 *
 * - 桌面环境：返回 `pywebview.api`（GuiApi 实例暴露的 JS 桥接方法）
 * - 浏览器/开发环境：返回 mockApi() 提供的假数据
 */
function getApi(): GuiApiInterface {
  if (typeof pywebview === 'undefined' || !pywebview.api) {
    return mockApi()
  }
  return pywebview.api
}

let _apiReady: Promise<void> | null = null

/**
 * 等待后端 API 就绪。
 *
 * 监听 `pywebviewready` 事件（pywebview 在 WebView2 加载完成后触发），
 * 若 5 秒内未收到事件则超时放行（允许 mock 模式继续运行）。
 *
 * @returns 在后端就绪或超时后 resolve 的 Promise
 */
function waitForApi(): Promise<void> {
  if (_apiReady) return _apiReady
  _apiReady = new Promise((resolve) => {
    if (typeof pywebview !== 'undefined' && pywebview.api) {
      resolve()
      return
    }
    const onReady = () => {
      window.removeEventListener('pywebviewready', onReady)
      resolve()
    }
    window.addEventListener('pywebviewready', onReady)
    setTimeout(() => {
      window.removeEventListener('pywebviewready', onReady)
      resolve()
    }, 5000)
  })
  return _apiReady
}

/**
 * 开发环境 mock API。
 *
 * 提供与 `GuiApi` 相同的方法签名但返回假数据，
 * 允许前端在浏览器中独立开发调试，无需启动 Python 后端。
 */
function mockApi(): GuiApiInterface {
  return {
    get_config: async () => ({
      input_dir: 'input',
      output_dir: 'output',
      process_all: true,
      export_rose_plot: false,
      rose_bin_width: 10,
      rose_dpi: 600,
      trace_dpi: 600,
      rotated_trace_dpi: 600,
      window_strategy: 'auto',
      auto_density_threshold: 5.0,
      tangent_window_count: 3,
      enable_node_recognition: false,
      node_merge_tolerance: 0.01,
      show_node_overlay: true,
      node_label_mode: 'type',
    }),
    set_config: async (cfg: Record<string, unknown>) => cfg,
    reset_config: async () => ({}),
    reset_processing_config: async () => ({
      process_all: true,
      export_rose_plot: false,
      rose_bin_width: 10,
      rose_dpi: 600,
      trace_dpi: 600,
      rotated_trace_dpi: 600,
      window_strategy: 'auto',
      auto_density_threshold: 5.0,
      tangent_window_count: 3,
      enable_node_recognition: false,
      node_merge_tolerance: 0.01,
      show_node_overlay: true,
      node_label_mode: 'type',
    }),
    reset_style_config: async () => ({ style: {} }),
    scan_files: async (_force?: boolean) => [
      { stem: 'O76_process', outcrop: 'O76', path: 'input/O76_process', status: 'completed' },
      { stem: 'O77_process', outcrop: 'O77', path: 'input/O77_process', status: 'pending' },
    ],
    run_pipeline: async () => ({ status: 'started', total: 1 }),
    poll_progress: async () => null,
    get_results: async () => [],
    get_stats: async (outcrop: string) => ({
      outcrop,
      scanline_azimuth: 298.0,
      trace_count: 19,
      mean_trace_length: 2.34,
      p10: 1.23,
      p20: 0.42,
      p21: 0.85,
      type_i: 5,
      type_ii: 8,
      type_iii: 6,
      histogram: { bins: [2,5,3,4,2,1,1,0,1,0], edges: [0,0.5,1,1.5,2,2.5,3,3.5,4,4.5,5] },
      warning: '',
    }),
    get_comparison: async () => [],
    get_data: async () => ({ data: [], total: 0, columns: [] }),
    generate_preview: async () => ({ status: 'ready', paths: { raw: '', rotated: '', rose: '' }, images: [] }),
    get_logs: async () => [],
    generate_report: async (_outcrop: string, _report_type: string, _fmt: string, _save_path?: string) => ({}),
    generate_reports_zip: async () => ({ zip_path: 'output/reports/reports_20240101_120000.zip', count: 2, errors: [] }),
    get_provenance: async () => ({}),
    poll_report_progress: async () => null as unknown as Record<string, unknown>,
    get_audit_log: async () => [],
    open_external: async (_url: string) => true,
    open_directory: async () => true,
    ask_save_path: async (_defaultName?: string, _fileFilter?: string) => 'C:\\mock\\save_path.zip',
    browse_folder: async () => 'C:\\mock\\folder',
    export_config_json: async (folder: string, content: string) => true,
    preload_fonts: async () => ({ status: 'ok' }),
    check_webview2: async () => ({ installed: true }),
    get_image_meta: async (_path: string) => ({ path: _path, size: 0, mtime_ns: 0, ext: '' }),
    get_image_data: async (_path: string) => ({ data: '', mtime_ns: 0, size: 0 }),
    get_image: async (_path: string) => '',
    get_image_thumbnail: async (_path: string, _maxPx?: number) => '',
    window_minimize: async () => true,
    window_maximize: async () => true,
    window_resize: async (_w: number, _h: number) => true,
    window_close: async () => true,
    window_move_by: async (_dx: number, _dy: number) => true,
    window_position: async () => ({ x: 0, y: 0 }) as { x: number; y: number },
    window_move_to: async (_x: number, _y: number) => true,
    window_is_maximized: async () => false,
  }
}

/**
 * 后端 API 调用入口。
 *
 * 每个方法对应 `GuiApi` 的同名 public 方法。
 * 所有调用在首次调用 `ready()` 之后才会真正发起（确保后端已就绪）。
 *
 * @example
 * ```ts
 * import { api } from '@/api/pywebview'
 * await api.ready()
 * const cfg = await api.get_config()
 * ```
 */
export const api = {
  ready: () => waitForApi(),
  get_config: () => getApi().get_config(),
  set_config: (cfg: Record<string, unknown>) => getApi().set_config(cfg),
  reset_config: () => getApi().reset_config(),
  reset_processing_config: () => getApi().reset_processing_config(),
  reset_style_config: () => getApi().reset_style_config(),
  scan_files: (force?: boolean) => getApi().scan_files(force),
  run_pipeline: (targets: string[], config: Record<string, unknown>) => getApi().run_pipeline(targets, config),
  poll_progress: () => getApi().poll_progress(),
  get_results: () => getApi().get_results(),
  get_stats: (outcrop: string) => getApi().get_stats(outcrop),
  get_comparison: (outcrops: string[]) => getApi().get_comparison(outcrops),
  get_data: (outcrop: string, section: string, page: number, page_size: number, source?: string) =>
    getApi().get_data(outcrop, section, page, page_size, source),
  generate_preview: (config: Record<string, unknown>) => getApi().generate_preview(config),
  get_logs: (tail?: number, level?: string) => getApi().get_logs(tail, level),
  generate_report: (outcrop: string, report_type: string, fmt: string, save_path?: string) =>
    getApi().generate_report(outcrop, report_type, fmt, save_path),
  generate_reports_zip: (targets: string[], report_type: string, fmt: string, save_path?: string) =>
    getApi().generate_reports_zip(targets, report_type, fmt, save_path),
  poll_report_progress: () => getApi().poll_report_progress(),
  get_provenance: (outcrop: string) => getApi().get_provenance(outcrop),
  get_audit_log: (limit?: number) => getApi().get_audit_log(limit),
  open_external: (url: string) => getApi().open_external(url),
  open_directory: (path: string) => getApi().open_directory(path),
  browse_folder: () => getApi().browse_folder(),
  ask_save_path: (defaultName?: string, fileFilter?: string) => getApi().ask_save_path(defaultName, fileFilter),
  export_config_json: (folder: string, content: string) => getApi().export_config_json(folder, content),
  get_image_meta: (path: string) => getApi().get_image_meta(path),
  get_image_data: (path: string) => getApi().get_image_data(path),
  get_image: (path: string) => getApi().get_image(path),
  get_image_thumbnail: (path: string, maxPx?: number) => getApi().get_image_thumbnail(path, maxPx),
  preload_fonts: () => getApi().preload_fonts(),
  check_webview2: () => getApi().check_webview2(),
  window_minimize: () => getApi().window_minimize(),
  window_maximize: () => getApi().window_maximize(),
  window_resize: (w: number, h: number) => getApi().window_resize(w, h),
  window_close: () => getApi().window_close(),
  window_move_by: (dx: number, dy: number) => getApi().window_move_by(dx, dy),
  window_position: () => getApi().window_position(),
  window_move_to: (x: number, y: number) => getApi().window_move_to(x, y),
  window_is_maximized: () => getApi().window_is_maximized(),
}
