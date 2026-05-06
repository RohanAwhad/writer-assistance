import { QueryClientProvider } from '@tanstack/react-query';

import { queryClient } from '../app/query-client';
import { CreateProjectForm } from '../components/create-project-form';
import { ProjectList } from '../components/project-list';
import { useProjectsQuery } from '../lib/api';

function RootRouteContent() {
  const { data } = useProjectsQuery();
  const projects = data?.projects ?? [];

  return (
    <main>
      <h1>Writer Assistance</h1>
      <CreateProjectForm />
      <ProjectList projects={projects} />
      {projects.length ? null : <p>Create your first project</p>}
    </main>
  );
}

export function RootRoute() {
  return (
    <QueryClientProvider client={queryClient}>
      <RootRouteContent />
    </QueryClientProvider>
  );
}
