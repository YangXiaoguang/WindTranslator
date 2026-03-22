import axios from "axios";
import type {
  ApiResponse,
  Project,
  ProjectDetail,
  ProgressData,
  TranslateRequest,
  ProvidersMap,
  TestKeyResult,
} from "@/types";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

/* ── Projects ─────────────────────────────────────────────── */

export async function uploadBook(file: File): Promise<Project> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<ApiResponse<Project>>("/projects/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
  });
  return data.data;
}

export async function listProjects(): Promise<Project[]> {
  const { data } = await api.get<ApiResponse<Project[]>>("/projects");
  return data.data;
}

export async function getProject(id: string): Promise<ProjectDetail> {
  const { data } = await api.get<ApiResponse<ProjectDetail>>(`/projects/${id}`);
  return data.data;
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/projects/${id}`);
}

/* ── Translation ──────────────────────────────────────────── */

export async function startTranslation(
  projectId: string,
  body: TranslateRequest
): Promise<{ project_id: string; task_id: string }> {
  const { data } = await api.post<
    ApiResponse<{ project_id: string; task_id: string }>
  >(`/projects/${projectId}/translate`, body);
  return data.data;
}

export async function cancelTranslation(projectId: string): Promise<void> {
  await api.post(`/projects/${projectId}/cancel`);
}

export async function getProgress(projectId: string): Promise<ProgressData> {
  const { data } = await api.get<ApiResponse<ProgressData>>(
    `/projects/${projectId}/progress`
  );
  return data.data;
}

export function getDownloadUrl(projectId: string): string {
  return `/api/projects/${projectId}/download/pdf`;
}

/* ── Config ───────────────────────────────────────────────── */

export async function getProviders(): Promise<ProvidersMap> {
  const { data } = await api.get<ApiResponse<ProvidersMap>>("/config/providers");
  return data.data;
}

export async function testApiKey(body: {
  provider: string;
  model: string;
  api_key: string;
  base_url?: string;
}): Promise<TestKeyResult> {
  const { data } = await api.post<ApiResponse<TestKeyResult>>(
    "/config/test-key",
    body
  );
  return data.data;
}
