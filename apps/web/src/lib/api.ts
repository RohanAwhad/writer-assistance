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
