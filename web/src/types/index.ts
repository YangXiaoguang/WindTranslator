/* API response types matching the server schemas */

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface Project {
  id: string;
  filename: string;
  format: string;
  title: string;
  total_chapters: number;
  total_blocks: number;
  file_size: number;
  status: ProjectStatus;
  created_at: string;
}

export type ProjectStatus =
  | "pending"
  | "parsed"
  | "translating"
  | "completed"
  | "failed"
  | "cancelled"
  | "error";

export interface ChapterPreview {
  id: string;
  index: number;
  title: string;
  block_count: number;
  preview_text: string;
  status: string;
}

export interface ProjectDetail extends Project {
  chapters: ChapterPreview[];
}

export interface ProgressData {
  project_id: string;
  status: string;
  total_blocks: number;
  completed_blocks: number;
  percent: number;
  current_chapter?: string;
  error_message?: string;
}

export interface TranslateRequest {
  provider: string;
  model: string;
  api_key: string;
  base_url?: string;
  chapter_range?: string;
}

export interface ProviderInfo {
  name: string;
  models: string[];
  requires_base_url: boolean;
}

export type ProvidersMap = Record<string, ProviderInfo>;

export interface TestKeyResult {
  success: boolean;
  message: string;
}

export interface WsEvent {
  event: "started" | "progress" | "completed" | "error";
  data: Record<string, unknown>;
}
