import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { QuoteAnchor } from './selection-anchor';

export type { QuoteAnchor } from './selection-anchor';
export const LENS_CATALOG = [
  'financial',
  'real_estate',
  'political',
  'software_engineering',
] as const;
export type LensName = (typeof LENS_CATALOG)[number];

export type CreateProjectInput = {
  title: string;
};

export type Project = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ProjectsResponse = {
  projects: Project[];
};

export type Resource = {
  id: string;
  project_id: string;
  logical_path: string;
  original_filename: string;
  content_hash: string;
  upload_status: string;
  created_at: string;
};

export type UploadResourcesResponse = {
  resources: Resource[];
};

export type ResourcesResponse = {
  resources: Resource[];
};

export type ResourceContentResponse = {
  resource_id: string;
  markdown: string;
};

export type Annotation = {
  id: string;
  project_id: string;
  resource_id: string;
  body: string;
  origin_type: string;
  provenance_source_id: string | null;
  created_at: string;
  updated_at: string;
  anchor: QuoteAnchor;
};

export type AnnotationsResponse = {
  annotations: Annotation[];
};

export type CreateAnnotationInput = {
  resource_id: string;
  body: string;
  anchor: QuoteAnchor;
};

export type AnalysisRunGenerationState =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'completed_with_failures'
  | 'failed'
  | 'cancelled';

export type AnalysisLensGenerationState =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled';

export type SuggestionReviewState = 'unreviewed' | 'accepted' | 'discarded';

export type AnalysisSuggestion = {
  id: string;
  analysis_run_id: string;
  lens: LensName;
  body: string;
  review_state: SuggestionReviewState;
  created_at: string;
  updated_at: string;
  anchor: QuoteAnchor;
};

export type AnalysisLensResult = {
  id: string;
  lens: LensName;
  generation_state: AnalysisLensGenerationState;
  error_message: string | null;
  suggestions: AnalysisSuggestion[];
};

export type AnalysisRun = {
  id: string;
  project_id: string;
  resource_id: string;
  generation_state: AnalysisRunGenerationState;
  lens_results: AnalysisLensResult[];
  created_at: string;
  updated_at: string;
};

export type CreateAnalysisRunInput = {
  resource_id: string;
  lenses: LensName[];
};

export type AcceptAnalysisSuggestionResponse = {
  suggestion: AnalysisSuggestion;
  annotation: Annotation;
};

export type SuggestionEnvelope = {
  suggestion: AnalysisSuggestion;
};

const projectsQueryKey = ['projects'] as const;
const resourcesQueryKey = (projectId: string | undefined) =>
  ['projects', projectId, 'resources'] as const;
const resourceContentQueryKey = (resourceId: string | null) =>
  ['resources', resourceId, 'content'] as const;
const annotationsQueryKey = (resourceId: string | null) =>
  ['resources', resourceId, 'annotations'] as const;
const latestAnalysisRunQueryKey = (resourceId: string | null) =>
  ['resources', resourceId, 'analysis-runs', 'latest'] as const;
const ANALYSIS_RUN_POLL_INTERVAL_MS = 1500;

export async function listProjects(): Promise<ProjectsResponse> {
  const response = await fetch('/api/projects');

  if (!response.ok) {
    throw new Error('Failed to load projects');
  }

  return (await response.json()) as ProjectsResponse;
}

export async function createProject(input: CreateProjectInput): Promise<Project> {
  const response = await fetch('/api/projects', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error('Failed to create project');
  }

  return (await response.json()) as Project;
}

type DirectoryFile = File & {
  webkitRelativePath?: string;
};

export async function uploadResources(
  projectId: string,
  files: File[],
): Promise<UploadResourcesResponse> {
  const formData = new FormData();

  files.forEach((file) => {
    const directoryFile = file as DirectoryFile;
    formData.append('files', file, file.name);
    formData.append('paths', directoryFile.webkitRelativePath || file.name);
  });

  const response = await fetch(`/api/projects/${projectId}/resources/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to upload resources');
  }

  return (await response.json()) as UploadResourcesResponse;
}

export async function listResources(projectId: string): Promise<ResourcesResponse> {
  const response = await fetch(`/api/projects/${projectId}/resources`);

  if (!response.ok) {
    throw new Error('Failed to load resources');
  }

  return (await response.json()) as ResourcesResponse;
}

export async function getResourceContent(resourceId: string): Promise<ResourceContentResponse> {
  const response = await fetch(`/api/resources/${resourceId}/content`);

  if (!response.ok) {
    throw new Error('Failed to load resource content');
  }

  return (await response.json()) as ResourceContentResponse;
}

export async function listAnnotations(resourceId: string): Promise<AnnotationsResponse> {
  const response = await fetch(`/api/resources/${resourceId}/annotations`);

  if (!response.ok) {
    throw new Error('Failed to load annotations');
  }

  return (await response.json()) as AnnotationsResponse;
}

export async function createAnnotation(
  projectId: string,
  input: CreateAnnotationInput,
): Promise<Annotation> {
  const response = await fetch(`/api/projects/${projectId}/annotations`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error('Failed to create annotation');
  }

  return (await response.json()) as Annotation;
}

export async function createAnalysisRun(
  projectId: string,
  input: CreateAnalysisRunInput,
): Promise<AnalysisRun> {
  const response = await fetch(`/api/projects/${projectId}/analysis-runs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error('Failed to run analysis');
  }

  return (await response.json()) as AnalysisRun;
}

export async function getLatestAnalysisRun(resourceId: string): Promise<AnalysisRun | null> {
  const response = await fetch(`/api/resources/${resourceId}/analysis-runs/latest`);

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error('Failed to load latest analysis run');
  }

  return (await response.json()) as AnalysisRun;
}

export function getLatestAnalysisRunPollIntervalMs(
  analysisRun: AnalysisRun | null | undefined,
): number | false {
  if (
    analysisRun?.generation_state === 'queued' ||
    analysisRun?.generation_state === 'running'
  ) {
    return ANALYSIS_RUN_POLL_INTERVAL_MS;
  }

  return false;
}

export async function retryAnalysisRun(analysisRunId: string): Promise<AnalysisRun> {
  const response = await fetch(`/api/analysis-runs/${analysisRunId}/retry`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to retry analysis');
  }

  return (await response.json()) as AnalysisRun;
}

export async function acceptAnalysisSuggestion(
  suggestionId: string,
): Promise<AcceptAnalysisSuggestionResponse> {
  const response = await fetch(`/api/analysis-suggestions/${suggestionId}/accept`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to accept suggestion');
  }

  return (await response.json()) as AcceptAnalysisSuggestionResponse;
}

export async function discardAnalysisSuggestion(suggestionId: string): Promise<SuggestionEnvelope> {
  const response = await fetch(`/api/analysis-suggestions/${suggestionId}/discard`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to discard suggestion');
  }

  return (await response.json()) as SuggestionEnvelope;
}

export function useProjectsQuery() {
  return useQuery({
    queryKey: projectsQueryKey,
    queryFn: listProjects,
  });
}

export function useResourcesQuery(projectId: string | undefined) {
  return useQuery({
    queryKey: resourcesQueryKey(projectId),
    queryFn: async () => {
      if (!projectId) {
        throw new Error('Project ID is required');
      }

      return listResources(projectId);
    },
    enabled: Boolean(projectId),
  });
}

export function useResourceContentQuery(resourceId: string | null) {
  return useQuery({
    queryKey: resourceContentQueryKey(resourceId),
    queryFn: async () => {
      if (!resourceId) {
        throw new Error('Resource ID is required');
      }

      return getResourceContent(resourceId);
    },
    enabled: Boolean(resourceId),
  });
}

export function useAnnotationsQuery(resourceId: string | null) {
  return useQuery({
    queryKey: annotationsQueryKey(resourceId),
    queryFn: async () => {
      if (!resourceId) {
        throw new Error('Resource ID is required');
      }

      return listAnnotations(resourceId);
    },
    enabled: Boolean(resourceId),
  });
}

export function useLatestAnalysisRunQuery(resourceId: string | null) {
  return useQuery({
    queryKey: latestAnalysisRunQueryKey(resourceId),
    queryFn: async () => {
      if (!resourceId) {
        throw new Error('Resource ID is required');
      }

      return getLatestAnalysisRun(resourceId);
    },
    enabled: Boolean(resourceId),
    refetchInterval: (query) => {
      const data = query.state.data as AnalysisRun | null | undefined;
      return getLatestAnalysisRunPollIntervalMs(data);
    },
  });
}

export function useCreateProjectMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createProject,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectsQueryKey });
    },
  });
}

export function useCreateAnnotationMutation(projectId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: CreateAnnotationInput) => {
      if (!projectId) {
        throw new Error('Project ID is required');
      }

      return createAnnotation(projectId, input);
    },
    onSuccess: async (annotation) => {
      queryClient.setQueryData<AnnotationsResponse>(
        annotationsQueryKey(annotation.resource_id),
        (existing) => ({
          annotations: [
            ...(existing?.annotations ?? []).filter((item) => item.id !== annotation.id),
            annotation,
          ],
        }),
      );
      await queryClient.invalidateQueries({
        queryKey: annotationsQueryKey(annotation.resource_id),
      });
    },
  });
}

export function useCreateAnalysisRunMutation(projectId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: CreateAnalysisRunInput) => {
      if (!projectId) {
        throw new Error('Project ID is required');
      }

      return createAnalysisRun(projectId, input);
    },
    onSuccess: async (analysisRun) => {
      queryClient.setQueryData<AnalysisRun | null>(
        latestAnalysisRunQueryKey(analysisRun.resource_id),
        analysisRun,
      );
      await queryClient.invalidateQueries({
        queryKey: latestAnalysisRunQueryKey(analysisRun.resource_id),
      });
    },
  });
}

export function useRetryAnalysisRunMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: retryAnalysisRun,
    onSuccess: async (analysisRun) => {
      queryClient.setQueryData<AnalysisRun | null>(
        latestAnalysisRunQueryKey(analysisRun.resource_id),
        analysisRun,
      );
      await queryClient.invalidateQueries({
        queryKey: latestAnalysisRunQueryKey(analysisRun.resource_id),
      });
    },
  });
}

export function useAcceptAnalysisSuggestionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: acceptAnalysisSuggestion,
    onSuccess: (payload) => {
      queryClient.setQueryData<AnnotationsResponse>(
        annotationsQueryKey(payload.annotation.resource_id),
        (existing) => ({
          annotations: [
            ...(existing?.annotations ?? []).filter(
              (annotation) => annotation.id !== payload.annotation.id,
            ),
            payload.annotation,
          ],
        }),
      );
      void queryClient.invalidateQueries({
        queryKey: latestAnalysisRunQueryKey(payload.annotation.resource_id),
      });
    },
  });
}

export function useDiscardAnalysisSuggestionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: discardAnalysisSuggestion,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        predicate: (query) =>
          Array.isArray(query.queryKey) &&
          query.queryKey[0] === 'resources' &&
          query.queryKey[2] === 'analysis-runs',
      });
    },
  });
}
