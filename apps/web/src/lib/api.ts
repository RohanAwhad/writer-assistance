import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { QuoteAnchor } from './selection-anchor';

export type { QuoteAnchor } from './selection-anchor';

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

const projectsQueryKey = ['projects'] as const;
const resourcesQueryKey = (projectId: string | undefined) =>
  ['projects', projectId, 'resources'] as const;
const resourceContentQueryKey = (resourceId: string | null) =>
  ['resources', resourceId, 'content'] as const;
const annotationsQueryKey = (resourceId: string | null) =>
  ['resources', resourceId, 'annotations'] as const;

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
