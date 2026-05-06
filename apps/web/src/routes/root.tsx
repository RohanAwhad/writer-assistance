import { CreateProjectForm } from '../components/create-project-form';
import { ProjectList } from '../components/project-list';
import { useProjectsQuery } from '../lib/api';

function RootRouteContent() {
  const { data, isError, isPending } = useProjectsQuery();
  const projects = data?.projects ?? [];
  let projectsContent = <ProjectList projects={projects} />;

  if (isPending) {
    projectsContent = <p>Loading projects...</p>;
  } else if (isError) {
    projectsContent = <p role="alert">Unable to load projects.</p>;
  } else if (!projects.length) {
    projectsContent = <p>Create your first project</p>;
  }

  return (
    <main>
      <h1>Writer Assistance</h1>
      <CreateProjectForm />
      {projectsContent}
    </main>
  );
}

export function RootRoute() {
  return <RootRouteContent />;
}
