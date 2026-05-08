export interface Project {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

export interface Resource {
  id: number;
  project_id: number;
  filename: string;
  path: string;
  content?: string;
  created_at: string;
}

export interface LensNote {
  content: string;
  highlight: string;
  status: "pending" | "accepted" | "discarded";
}

export interface Lens {
  id: number;
  resource_id: number;
  name: string;
  perspective: string;
  notes: LensNote[];
  created_at: string;
}

export interface Note {
  id: number;
  project_id: number;
  resource_id: number | null;
  lens_id: number | null;
  content: string;
  note_type: string;
  highlight: string;
  created_at: string;
}

export interface ReportBlock {
  id: number;
  report_id: number;
  position: number;
  content: string;
  block_type: string;
  created_at: string;
}

export interface Report {
  id: number;
  project_id: number;
  title: string;
  blocks: ReportBlock[];
  created_at: string;
}

export interface ToneVariation {
  tone_name: string;
  content: string;
}

export interface Critique {
  critique: string;
  suggestions: string[];
  questions: string[];
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export const listProjects = () => request<Project[]>("/api/projects");

export const createProject = (data: { name: string; description: string }) =>
  request<Project>("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

export const deleteProject = (id: number) =>
  request<{ ok: boolean }>(`/api/projects/${id}`, { method: "DELETE" });

export const getProject = (id: number) =>
  request<Project>(`/api/projects/${id}`);

export const listResources = (projectId: number) =>
  request<Resource[]>(`/api/projects/${projectId}/resources`);

export const getResource = (id: number) =>
  request<Resource>(`/api/resources/${id}`);

export const uploadResources = (projectId: number, files: File[]) => {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  return request<Resource[]>(`/api/projects/${projectId}/resources`, {
    method: "POST",
    body: form,
  });
};

export const deleteResource = (id: number) =>
  request<{ ok: boolean }>(`/api/resources/${id}`, { method: "DELETE" });

export const generateLenses = (resourceId: number) =>
  request<Lens[]>(`/api/resources/${resourceId}/lenses/generate`, {
    method: "POST",
  });

export const listLenses = (resourceId: number) =>
  request<Lens[]>(`/api/resources/${resourceId}/lenses`);

export const listNotes = (projectId: number) =>
  request<Note[]>(`/api/projects/${projectId}/notes`);

export const createNote = (
  projectId: number,
  data: { content: string; note_type?: string; highlight?: string }
) =>
  request<Note>(`/api/projects/${projectId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

export const acceptLensNotes = (
  projectId: number,
  lensId: number,
  noteIndices: number[]
) =>
  request<Note[]>(`/api/projects/${projectId}/notes/from-lens`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lens_id: lensId, note_ids: noteIndices }),
  });

export const discardLensNotes = (
  projectId: number,
  lensId: number,
  noteIndices: number[]
) =>
  request<{ ok: boolean }>(`/api/projects/${projectId}/notes/discard-lens`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lens_id: lensId, note_ids: noteIndices }),
  });

export const deleteNote = (id: number) =>
  request<{ ok: boolean }>(`/api/notes/${id}`, { method: "DELETE" });

export interface ReportSummary {
  id: number;
  project_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export const listReports = (projectId: number) =>
  request<ReportSummary[]>(`/api/projects/${projectId}/reports`);

export const generateReport = (projectId: number) =>
  request<Report>(`/api/projects/${projectId}/reports/generate`, {
    method: "POST",
  });

export const getReport = (id: number) =>
  request<Report>(`/api/reports/${id}`);

export const deleteReport = (id: number) =>
  request<{ ok: boolean }>(`/api/reports/${id}`, { method: "DELETE" });

export const exportReport = async (reportId: number) => {
  const res = await fetch(`/api/reports/${reportId}/export`);
  const text = await res.text();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="(.+)"/);
  const filename = match ? match[1] : "report.md";
  const blob = new Blob([text], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

export const updateBlock = (
  reportId: number,
  blockId: number,
  content: string
) =>
  request<ReportBlock>(`/api/reports/${reportId}/blocks/${blockId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });

export const getToneVariations = (reportId: number, blockId: number) =>
  request<ToneVariation[]>(
    `/api/reports/${reportId}/blocks/${blockId}/tone-variations`,
    { method: "POST" }
  );

export const getCritique = (reportId: number, blockId: number) =>
  request<Critique>(`/api/reports/${reportId}/blocks/${blockId}/critique`, {
    method: "POST",
  });
