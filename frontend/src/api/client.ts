import type {
  AiProvider,
  AnnotationOut,
  CritiqueOut,
  DumpEntryIn,
  DumpOut,
  ExpertNoteOut,
  ExpertNoteState,
  ExpertRunOut,
  ExpertRunsOut,
  ImportResult,
  LensProposalOut,
  LensProposalStatus,
  ProjectDetail,
  ProjectOut,
  ReportBlockOut,
  ReportOut,
  ResourceOut,
  RoundDetailOut,
  RoundOut,
  RoundSummary,
  ToneSamplesOut,
  TreeOut,
} from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

type JsonBody = Record<string, unknown>;

interface RequestOptions {
  method: string;
  body?: JsonBody;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function request<T>(path: string, options: RequestOptions): Promise<T> {
  const init: RequestInit = {
    method: options.method,
    headers: { Accept: "application/json" },
  };
  if (options.body !== undefined) {
    init.headers = { ...init.headers, "Content-Type": "application/json" };
    init.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, init);
  if (response.status === 204) {
    return undefined as T;
  }
  const payload: unknown = await response
    .json()
    .catch(() => null);
  if (!response.ok) {
    const detail =
      isRecord(payload) && typeof payload.detail === "string"
        ? payload.detail
        : `request failed with status ${response.status}`;
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export const api = {
  async listProjects(): Promise<ProjectOut[]> {
    return request<ProjectOut[]>(`${BASE}/projects`, { method: "GET" });
  },

  async createProject(name: string): Promise<ProjectOut> {
    return request<ProjectOut>(`${BASE}/projects`, { method: "POST", body: { name } });
  },

  async getProject(projectId: number): Promise<ProjectDetail> {
    return request<ProjectDetail>(`${BASE}/projects/${projectId}`, { method: "GET" });
  },

  async deleteProject(projectId: number): Promise<void> {
    return request<void>(`${BASE}/projects/${projectId}`, { method: "DELETE" });
  },

  async updateProjectProvider(projectId: number, provider: AiProvider): Promise<ProjectOut> {
    return request<ProjectOut>(`${BASE}/projects/${projectId}/provider`, {
      method: "PUT",
      body: { provider },
    });
  },

  async importTree(projectId: number, path: string): Promise<ImportResult> {
    return request<ImportResult>(`${BASE}/projects/${projectId}/import`, {
      method: "POST",
      body: { path },
    });
  },

  async getTree(projectId: number): Promise<TreeOut> {
    return request<TreeOut>(`${BASE}/projects/${projectId}/tree`, { method: "GET" });
  },

  async getResource(resourceId: number): Promise<ResourceOut> {
    return request<ResourceOut>(`${BASE}/resources/${resourceId}`, { method: "GET" });
  },

  async getResourceAnnotations(resourceId: number): Promise<AnnotationOut[]> {
    return request<AnnotationOut[]>(`${BASE}/resources/${resourceId}/annotations`, {
      method: "GET",
    });
  },

  async createHighlight(
    resourceId: number,
    body: { start_offset: number; end_offset: number; content?: string },
  ): Promise<AnnotationOut> {
    return request<AnnotationOut>(`${BASE}/resources/${resourceId}/highlights`, {
      method: "POST",
      body,
    });
  },

  async createNote(
    resourceId: number,
    body: {
      content: string;
      start_offset?: number | null;
      end_offset?: number | null;
    },
  ): Promise<AnnotationOut> {
    return request<AnnotationOut>(`${BASE}/resources/${resourceId}/notes`, {
      method: "POST",
      body,
    });
  },

  async deleteAnnotation(annotationId: number): Promise<void> {
    return request<void>(`${BASE}/annotations/${annotationId}`, { method: "DELETE" });
  },

  async proposeLenses(resourceId: number): Promise<LensProposalOut[]> {
    return request<LensProposalOut[]>(`${BASE}/resources/${resourceId}/lens-proposals`, {
      method: "POST",
    });
  },

  async listLensProposals(resourceId: number): Promise<LensProposalOut[]> {
    return request<LensProposalOut[]>(`${BASE}/resources/${resourceId}/lens-proposals`, {
      method: "GET",
    });
  },

  async setLensProposalStatus(
    proposalId: number,
    status: LensProposalStatus,
  ): Promise<LensProposalOut> {
    return request<LensProposalOut>(`${BASE}/lens-proposals/${proposalId}`, {
      method: "PATCH",
      body: { status },
    });
  },

  async createRound(body: {
    project_id: number;
    doc_ids: number[];
    name?: string | null;
  }): Promise<RoundOut> {
    return request<RoundOut>(`${BASE}/rounds`, { method: "POST", body });
  },

  async listRounds(projectId: number): Promise<RoundSummary[]> {
    return request<RoundSummary[]>(`${BASE}/rounds?project_id=${projectId}`, {
      method: "GET",
    });
  },

  async getRound(roundId: number): Promise<RoundDetailOut> {
    return request<RoundDetailOut>(`${BASE}/rounds/${roundId}`, { method: "GET" });
  },

  async runExperts(roundId: number, lensProposalIds: number[]): Promise<ExpertRunsOut> {
    return request<ExpertRunsOut>(`${BASE}/rounds/${roundId}/experts`, {
      method: "POST",
      body: { lens_proposal_ids: lensProposalIds },
    });
  },

  async getRoundExpertRuns(roundId: number): Promise<ExpertRunsOut> {
    return request<ExpertRunsOut>(`${BASE}/rounds/${roundId}/expert-runs`, { method: "GET" });
  },

  async getExpertRunNotes(runId: number): Promise<ExpertRunOut> {
    return request<ExpertRunOut>(`${BASE}/expert-runs/${runId}/notes`, { method: "GET" });
  },

  async updateExpertNote(
    noteId: number,
    reviewState: ExpertNoteState,
    content?: string,
  ): Promise<ExpertNoteOut> {
    return request<ExpertNoteOut>(`${BASE}/expert-notes/${noteId}`, {
      method: "PATCH",
      body: { review_state: reviewState, content },
    });
  },

  async mergeExpertNote(noteId: number, content?: string): Promise<DumpOut["entries"][number]> {
    return request<DumpOut["entries"][number]>(`${BASE}/expert-notes/${noteId}/merge`, {
      method: "POST",
      body: content !== undefined ? { content } : {},
    });
  },

  async getDump(roundId: number): Promise<DumpOut> {
    return request<DumpOut>(`${BASE}/rounds/${roundId}/dump`, { method: "GET" });
  },

  async saveDump(roundId: number, entries: DumpEntryIn[]): Promise<DumpOut> {
    return request<DumpOut>(`${BASE}/rounds/${roundId}/dump`, {
      method: "POST",
      body: { entries },
    });
  },

  async generateReport(roundId: number): Promise<ReportOut> {
    return request<ReportOut>(`${BASE}/rounds/${roundId}/generate-report`, {
      method: "POST",
    });
  },

  async getReport(reportId: number): Promise<ReportOut> {
    return request<ReportOut>(`${BASE}/reports/${reportId}`, { method: "GET" });
  },

  async exportMarkdown(reportId: number): Promise<string> {
    const response = await fetch(`${BASE}/reports/${reportId}/export.md`, {
      method: "GET",
      headers: { Accept: "text/markdown" },
    });
    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null);
      const detail =
        isRecord(payload) && typeof payload.detail === "string"
          ? payload.detail
          : `request failed with status ${response.status}`;
      throw new ApiError(response.status, detail);
    }
    return response.text();
  },

  async deleteReport(reportId: number, confirm: boolean): Promise<void> {
    return request<void>(`${BASE}/reports/${reportId}`, {
      method: "DELETE",
      body: { confirm },
    });
  },

  async updateBlock(blockId: number, content: string): Promise<ReportBlockOut> {
    return request<ReportBlockOut>(`${BASE}/blocks/${blockId}`, {
      method: "PUT",
      body: { content },
    });
  },

  async toneSamples(blockId: number): Promise<ToneSamplesOut> {
    return request<ToneSamplesOut>(`${BASE}/blocks/${blockId}/tone-samples`, {
      method: "POST",
    });
  },

  async critiqueBlock(blockId: number): Promise<CritiqueOut> {
    return request<CritiqueOut>(`${BASE}/blocks/${blockId}/critique`, { method: "POST" });
  },
};
