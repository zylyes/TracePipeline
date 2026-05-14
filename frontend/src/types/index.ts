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
  raw_plot_path: string
  rotated_plot_path: string
  rose_plot_path: string
  window_strategy: string
  area_source: string
  error?: string
}

export interface PipelineProgress {
  current: number
  total: number
  filename: string
  message: string
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
}

export interface ImageItem {
  key: string
  title: string
  src: string
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
  style?: Record<string, any>
  [key: string]: any
}

export interface ComparisonRow {
  outcrop: string
  p10: string
  p20: string
  p21: string
  mean_trace_length: string
  scanline_azimuth: string
  type_ratio: string
}

export interface DataPageResult {
  data: any[]
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
}
