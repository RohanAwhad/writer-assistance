import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

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
  storage_location: string;
  content_hash: string;
  upload_status: string;
  created_at: string;
};

export type UploadResourcesResponse = {
  resources: Resource[];
};

const projectsQueryKey = ['projects'] as const;

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

export function useProjectsQuery() {
  return useQuery({
    queryKey: projectsQueryKey,
    queryFn: listProjects,
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
