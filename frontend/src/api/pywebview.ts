// Python API 封装（通过 pywebview 暴露的 JS API）
declare const pywebview: any

function getApi(): any {
  if (typeof pywebview === 'undefined' || !pywebview.api) {
    // 开发环境回退：返回 mock
    return mockApi()
  }
  return pywebview.api
}

function mockApi(): any {
  return {
    get_config: async () => ({
      input_dir: 'input',
      output_dir: 'output',
      process_all: true,
      export_rose_plot: true,
      rose_bin_width: 10,
      rose_dpi: 400,
      trace_dpi: 300,
      rotated_trace_dpi: 600,
      window_strategy: 'auto',
      auto_density_threshold: 5.0,
      tangent_window_count: 3,
    }),
    set_config: async (cfg: any) => cfg,
    reset_config: async () => ({}),
    reset_processing_config: async () => ({
      process_all: true,
      export_rose_plot: true,
      rose_bin_width: 10,
      rose_dpi: 400,
      trace_dpi: 300,
      rotated_trace_dpi: 600,
      window_strategy: 'auto',
      auto_density_threshold: 5.0,
      tangent_window_count: 3,
      enable_node_recognition: true,
      node_merge_tolerance: 1e-6,
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
    generate_report: async () => ({}),
    generate_reports_zip: async () => ({ zip_path: 'output/reports/reports_20240101_120000.zip', count: 2, errors: [] }),
    get_provenance: async () => ({}),
    get_audit_log: async () => [],
    open_directory: async () => true,
    ask_save_path: async (_defaultName?: string, _fileFilter?: string) => 'C:\\mock\\save_path.zip',
    browse_folder: async () => 'C:\\mock\\folder',
    export_config_json: async (folder: string, content: string) => true,
    check_webview2: async () => ({ installed: true }),
    get_image: async (_path: string) => '',
  }
}

export const api = {
  get_config: () => getApi().get_config(),
  set_config: (cfg: any) => getApi().set_config(cfg),
  reset_config: () => getApi().reset_config(),
  reset_processing_config: () => getApi().reset_processing_config(),
  reset_style_config: () => getApi().reset_style_config(),
  scan_files: (force?: boolean) => getApi().scan_files(force),
  run_pipeline: (targets: string[], config: any) => getApi().run_pipeline(targets, config),
  poll_progress: () => getApi().poll_progress(),
  get_results: () => getApi().get_results(),
  get_stats: (outcrop: string) => getApi().get_stats(outcrop),
  get_comparison: (outcrops: string[]) => getApi().get_comparison(outcrops),
  get_data: (outcrop: string, section: string, page: number, page_size: number, source?: string) =>
    getApi().get_data(outcrop, section, page, page_size, source),
  generate_preview: (config: any) => getApi().generate_preview(config),
  get_logs: (tail?: number, level?: string) => getApi().get_logs(tail, level),
  generate_report: (outcrop: string, report_type: string, fmt: string) =>
    getApi().generate_report(outcrop, report_type, fmt),
  generate_reports_zip: (targets: string[], report_type: string, fmt: string, save_path?: string) =>
    getApi().generate_reports_zip(targets, report_type, fmt, save_path),
  get_provenance: (outcrop: string) => getApi().get_provenance(outcrop),
  get_audit_log: (limit?: number) => getApi().get_audit_log(limit),
  open_directory: (path: string) => getApi().open_directory(path),
  browse_folder: () => getApi().browse_folder(),
  ask_save_path: (defaultName?: string, fileFilter?: string) => getApi().ask_save_path(defaultName, fileFilter),
  export_config_json: (folder: string, content: string) => getApi().export_config_json(folder, content),
  get_image: (path: string) => getApi().get_image(path),
  check_webview2: () => getApi().check_webview2(),
}
