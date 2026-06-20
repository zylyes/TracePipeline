/** UI 类型定义 */

export interface TraceFile {
  stem: string
  outcrop: string
  path: string
  status: 'completed' | 'pending' | 'error'
}

export interface PipelineResult {
  outcrop: string
  status: string
  trace_count: number
  mean_length: number
  scanline_azimuth: number
  excel_path: string
  raw_plot: string
  rotated_plot: string
  rose_plot: string
  window_strategy: string
  area_source: string
  error?: string
  error_type?: string
  node_count?: number
  node_x_count?: number
  node_y_count?: number
  node_i_count?: number
}

export interface PipelineProgress {
  current: number
  total: number
  filename: string
  message: string
}

export interface ReportProgress {
  type: 'progress' | 'complete' | 'error'
  step?: string
  message?: string
  current?: number
  total?: number
  outcrop?: string
}

export interface StatsData {
  outcrop: string
  scanline_azimuth: number
  trace_count: number
  mean_trace_length: number | null
  p10: number | null
  p20: number | null
  p21: number | null
  type_i: number
  type_ii: number
  type_iii: number
  scanline_length?: number | null
  outcrop_area?: number | null
  area_source?: string
  window_strategy?: string
  histogram?: {
    bins: number[]
    edges: number[]
  }
  strikes?: number[]
  circles?: Array<{
    center_x: number
    center_y: number
    radius: number
  }>
  warning?: string
  nodes_summary?: {
    node_count: number
    node_i_count: number
    node_y_count: number
    node_x_count: number
    intersection_count: number
    degenerate_skipped: number
  }
  nodes?: Array<{
    node_id: number
    x: number
    y: number
    type: string
    degree: number
    trace_indices: number[]
    event_count: number
  }>
  intersections?: Array<{
    trace_a: number
    trace_b: number
    x: number
    y: number
    t: number
    u: number
    kind: string
  }>
}

export interface ImageItem {
  key: string
  title: string
  src: string
  dataUrl?: string
}

export interface ConfigData {
  input_dir?: string
  output_dir?: string
  process_all?: boolean
  export_rose_plot?: boolean
  rose_bin_width?: number
  rose_dpi?: number
  trace_dpi?: number
  rotated_trace_dpi?: number
  window_strategy?: string
  auto_density_threshold?: number
  tangent_window_count?: number
  style?: Record<string, unknown>
  [key: string]: unknown
}

export interface DataPageResult {
  data: Record<string, unknown>[]
  total: number
  columns: string[]
  error?: string
}

export interface PlotOverlay {
  data_x_min: number
  data_x_max: number
  data_y_min: number
  data_y_max: number
  has_hull: boolean
  hull_vertices: Array<[number, number]>
  has_circles: boolean
  circles: Array<{ center_x: number; center_y: number; radius: number }>
  has_nodes: boolean
  nodes: Array<{ x: number; y: number; node_type: string; node_id: number; degree: number }>
}

export interface ComparisonRow {
  outcrop: string
  trace_count: string
  p10: string
  p20: string
  p21: string
  mean_trace_length: string
  scanline_azimuth: string
  type_ratio: string
  node_count: string
  node_ratio: string
  node_density: string
}
